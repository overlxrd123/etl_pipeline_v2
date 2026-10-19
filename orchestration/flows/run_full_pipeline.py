"""
Prefect 父 Flow: 完整 ETL 管道编排
天气采集 → 加密采集 → 订单生成 → 数据质量门禁 → dbt 构建与测试
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from prefect import flow, task
from datetime import datetime, date

from orchestration.flows.ingest_weather import ingest_weather
from orchestration.flows.ingest_crypto import ingest_crypto
from orchestration.flows.generate_orders import generate_orders_flow


@task(name="run-dbt")
def task_run_dbt():
    """运行 dbt 模型构建"""
    import subprocess
    dbt_dir = Path(__file__).parent.parent.parent / "dbt_project"

    # --profiles-dir . 不能省略：profile 在 dbt_project/ 里，
    # 默认位置 ~/.dbt/profiles.yml 不存在
    import os
    from sqlalchemy.engine import make_url
    from config.settings import DB_URL
    url = make_url(DB_URL)
    if url.get_backend_name() != 'sqlite':
        raise ValueError('当前 dbt profile 仅支持 SQLite；其他数据库需要单独适配并验证 SQL')
    environment = os.environ.copy()
    environment['ETL_SQLITE_PATH'] = str(Path(url.database).resolve())
    print("[dbt] 运行 dbt build（模型与测试按依赖顺序执行）...")
    result = subprocess.run(
        ["dbt", "build", "--profiles-dir", "."],
        cwd=str(dbt_dir),
        capture_output=True,
        text=True, encoding='utf-8', errors='replace', timeout=600, env=environment,
    )
    if result.returncode != 0:
        raise RuntimeError(f"dbt build 失败:\n{(result.stdout + result.stderr)[-4000:]}")
    print("[dbt] build 完成")

    return True


@task(name="data-quality-check")
def task_quality_check():
    """数据质量快速检查"""
    from config.db_connection import get_session
    from src.utils.quality import check_warehouse
    return check_warehouse(get_session)


@flow(name="full-etl-pipeline")
def run_full_pipeline(skip_api: bool = False, skip_dbt: bool = False):
    """
    完整 ETL 管道

    Args:
        skip_api: 跳过 API 调用（离线模式，使用已有数据）
        skip_dbt: 跳过 dbt 转换（dbt 需单独安装）
    """
    start = datetime.now()
    print("=" * 60)
    print(f"[START] Full ETL Pipeline — {start.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    stages = []
    from config.db_connection import init_db
    from seed_data import seed_dim_date, seed_dim_city
    from config.settings import SIM_START, SIM_END
    init_db()
    seed_dim_date()
    seed_dim_city()

    # Stage 1: 数据采集
    if not skip_api:
        print("\n" + "=" * 40)
        print("STAGE 1/4: 数据采集")
        print("=" * 40)

        print("\n[1a] 天气数据...")
        weather_count = ingest_weather(start_date=SIM_START, end_date=SIM_END)
        stages.append(("天气采集", weather_count))

        print("\n[1b] 加密汇率...")
        crypto_count = ingest_crypto(start_date=SIM_START, end_date=SIM_END)
        stages.append(("加密采集", crypto_count))
    else:
        print("\n[STAGE 1/4] 数据采集 — 跳过（离线模式）")

    # Stage 2: 订单生成 + 加载
    print("\n" + "=" * 40)
    print("STAGE 2/4: 订单生成 + 入库")
    print("=" * 40)
    order_count = generate_orders_flow(force=False)
    stages.append(("订单加载", order_count))
    # Reject bad source data before refreshing any dbt marts.
    print("\nSTAGE 3/4: 入库质量门禁")
    quality = task_quality_check()
    stages.append(("质量检查", quality))

    # Stage 4: dbt 转换与测试
    print("\n" + "=" * 40)
    print("STAGE 4/4: dbt 数据转换与测试")
    print("=" * 40)
    if not skip_dbt:
        dbt_ok = task_run_dbt()
        stages.append(("dbt转换", dbt_ok))
    else:
        print("  dbt 转换 — 跳过（需安装 dbt-sqlite）")

    # 完成
    elapsed = (datetime.now() - start).total_seconds()
    print("\n" + "=" * 60)
    print(f"[DONE] Full ETL Pipeline completed — {elapsed:.1f}s")
    print("=" * 60)

    for name, result in stages:
        print(f"  {name}: {result}")

    return {"elapsed": elapsed, "stages": stages}


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='运行完整 ETL；默认采集历史驱动数据并执行 dbt build')
    parser.add_argument('--offline', action='store_true', help='使用已有驱动数据，不调用外部 API')
    parser.add_argument('--skip-dbt', action='store_true', help='显式跳过 dbt，marts 不会刷新')
    args = parser.parse_args()
    run_full_pipeline(skip_api=args.offline, skip_dbt=args.skip_dbt)

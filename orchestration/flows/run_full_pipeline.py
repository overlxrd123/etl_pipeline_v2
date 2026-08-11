"""
Prefect 父 Flow: 完整 ETL 管道编排
天气采集 → 加密采集 → 订单生成 → dbt 转换 → 数据质量检查
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

    print("[dbt] 运行 dbt run...")
    result = subprocess.run(
        ["dbt", "run"],
        cwd=str(dbt_dir),
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(f"[dbt] run 警告:\n{result.stderr[:500]}")
    else:
        print(f"[dbt] run 完成")

    print("[dbt] 运行 dbt test...")
    result = subprocess.run(
        ["dbt", "test"],
        cwd=str(dbt_dir),
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(f"[dbt] test 警告:\n{result.stderr[:500]}")
    else:
        print(f"[dbt] test 完成")

    return True


@task(name="data-quality-check")
def task_quality_check():
    """数据质量快速检查"""
    from config.db_connection import get_session
    from src.warehouse.models import FactOrders, DimProduct, DimCustomer

    session = get_session()

    checks = {}
    checks["fact_orders_count"] = session.query(FactOrders).count()
    checks["dim_product_count"] = session.query(DimProduct).count()
    checks["dim_customer_count"] = session.query(DimCustomer).count()

    # 检查空值
    null_orders = session.query(FactOrders).filter(FactOrders.net_amount.is_(None)).count()
    checks["null_net_amount"] = null_orders

    session.close()

    print(f"[Quality] 数据质量检查:")
    for k, v in checks.items():
        print(f"  {k}: {v}")

    # 如果存在明显问题则告警
    if null_orders > 0:
        print(f"[Quality] WARNING: {null_orders} 条订单金额为空!")

    return checks


@flow(name="full-etl-pipeline")
def run_full_pipeline(skip_api: bool = False, skip_dbt: bool = True):
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

    # Stage 1: 数据采集
    if not skip_api:
        print("\n" + "=" * 40)
        print("STAGE 1/4: 数据采集")
        print("=" * 40)

        print("\n[1a] 天气数据...")
        weather_count = ingest_weather()
        stages.append(("天气采集", weather_count))

        print("\n[1b] 加密汇率...")
        crypto_count = ingest_crypto()
        stages.append(("加密采集", crypto_count))
    else:
        print("\n[STAGE 1/4] 数据采集 — 跳过（离线模式）")

    # Stage 2: 订单生成 + 加载
    print("\n" + "=" * 40)
    print("STAGE 2/4: 订单生成 + 入库")
    print("=" * 40)
    order_count = generate_orders_flow(force=False)
    stages.append(("订单加载", order_count))

    # Stage 3: dbt 转换
    print("\n" + "=" * 40)
    print("STAGE 3/4: dbt 数据转换")
    print("=" * 40)
    if not skip_dbt:
        dbt_ok = task_run_dbt()
        stages.append(("dbt转换", dbt_ok))
    else:
        print("  dbt 转换 — 跳过（需安装 dbt-sqlite）")

    # Stage 4: 质量检查
    print("\n" + "=" * 40)
    print("STAGE 4/4: 数据质量检查")
    print("=" * 40)
    quality = task_quality_check()
    stages.append(("质量检查", quality))

    # 完成
    elapsed = (datetime.now() - start).total_seconds()
    print("\n" + "=" * 60)
    print(f"[DONE] Full ETL Pipeline completed — {elapsed:.1f}s")
    print("=" * 60)

    for name, result in stages:
        print(f"  {name}: {result}")

    return {"elapsed": elapsed, "stages": stages}


if __name__ == "__main__":
    run_full_pipeline(skip_api=True, skip_dbt=True)

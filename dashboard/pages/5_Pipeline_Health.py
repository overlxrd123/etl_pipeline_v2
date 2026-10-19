"""
管道健康 — ETL 运行监控页
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import streamlit as st
import pandas as pd
from datetime import datetime
from dashboard.utils.db_queries import get_pipeline_stats, get_driver_coverage

st.title("🔧 管道健康监控")
st.caption("ETL管道运行状态 & 数据质量检查")

# 当前时间
st.metric("最近检查时间", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

st.divider()

# 表统计
st.subheader("数仓各表行数")
stats = get_pipeline_stats()

cols = st.columns(len(stats))
for i, row in stats.iterrows():
    with cols[i]:
        st.metric(row["表名"], f"{row['行数']:,}")

st.divider()

# 数据质量检查
st.subheader("订单加载批次")
from dashboard.utils.db_queries import get_recent_load_runs
load_runs = get_recent_load_runs()
if load_runs.empty:
    st.info("暂无加载记录。下次运行订单加载后，这里会显示批次状态、增量行数及失败类型。")
else:
    st.dataframe(load_runs, width='stretch', hide_index=True)
    if load_runs.iloc[0]['状态'] == 'failed':
        st.warning("最近一次订单加载失败。已提交批次保留，使用同一来源文件重跑可补齐未完成部分。")
st.divider()

st.subheader("数据质量检查")

from config.db_connection import get_session
from src.warehouse.models import FactOrders
from sqlalchemy import text

session = get_session()

checks = []

# 检查1: 空金额
null_amounts = session.query(FactOrders).filter(FactOrders.net_amount.is_(None)).count()
checks.append({
    "检查项": "订单金额为空",
    "结果": "通过" if null_amounts == 0 else "失败",
    "详情": f"发现 {null_amounts} 条空值" if null_amounts > 0 else "全部正常",
})

# 检查2: 负数金额
neg_amounts = session.query(FactOrders).filter(FactOrders.net_amount <= 0).count()
checks.append({
    "检查项": "订单金额为正",
    "结果": "通过" if neg_amounts == 0 else "失败",
    "详情": f"发现 {neg_amounts} 条非正数" if neg_amounts > 0 else "全部正常",
})

# 检查3: 有效日期
null_dates = session.query(FactOrders).filter(FactOrders.date_id.is_(None)).count()
checks.append({
    "检查项": "日期字段完整",
    "结果": "通过" if null_dates == 0 else "失败",
    "详情": f"发现 {null_dates} 条空日期" if null_dates > 0 else "全部正常",
})

# 检查4: 有效客户FK
bad_customers = session.execute(text("""
    SELECT COUNT(*) FROM fact_orders f
    LEFT JOIN dim_customer c ON f.customer_id = c.customer_id
    WHERE c.customer_id IS NULL
""")).scalar()
checks.append({
    "检查项": "客户外键完整",
    "结果": "通过" if bad_customers == 0 else "警告",
    "详情": f"发现 {bad_customers} 条孤儿订单" if bad_customers > 0 else "全部正常",
})

# 检查5: 有效产品FK
bad_products = session.execute(text("""
    SELECT COUNT(*) FROM fact_orders f
    LEFT JOIN dim_product p ON f.product_id = p.product_id
    WHERE p.product_id IS NULL
""")).scalar()
checks.append({
    "检查项": "产品外键完整",
    "结果": "通过" if bad_products == 0 else "警告",
    "详情": f"发现 {bad_products} 条孤儿订单" if bad_products > 0 else "全部正常",
})

session.close()

# 显示检查结果
checks_df = pd.DataFrame(checks)
for _, row in checks_df.iterrows():
    if row["结果"] == "通过":
        st.success(f"**{row['检查项']}** — {row['详情']}")
    elif row["结果"] == "警告":
        st.warning(f"**{row['检查项']}** — {row['详情']}")
    else:
        st.error(f"**{row['检查项']}** — {row['详情']}")

st.divider()

# 数据新鲜度
st.subheader("数据新鲜度")
from config.db_connection import engine

with engine.connect() as conn:
    latest_order = conn.execute(text(
        "SELECT MAX(order_timestamp) FROM fact_orders"
    )).scalar()
    if latest_order:
        st.metric("最新订单时间", str(latest_order)[:19])

    latest_weather = conn.execute(text(
        "SELECT MAX(fetched_at) FROM dim_weather"
    )).scalar()
    if latest_weather:
        st.metric("最新天气采集", str(latest_weather)[:19])

    latest_crypto = conn.execute(text(
        "SELECT MAX(fetched_at) FROM dim_crypto"
    )).scalar()
    if latest_crypto:
        st.metric("最新加密价格采集", str(latest_crypto)[:19])

st.divider()

# 驱动数据覆盖
st.subheader("驱动数据覆盖")
cov = get_driver_coverage()
order_days = int(cov["订单天数"] or 0)
order_city_days = int(cov["订单城市日"] or 0)
weather_cov = (
    float(cov["天气匹配城市日"]) / order_city_days * 100
    if order_city_days else 0.0
)
crypto_cov = (
    float(cov["币价匹配天数"]) / order_days * 100
    if order_days else 0.0
)

c1, c2, c3 = st.columns(3)
c1.metric(
    "订单日期范围",
    f"{cov['订单起始日']} ~ {cov['订单结束日']}",
    help=f"共 {order_days} 天",
)
c2.metric("天气覆盖率", f"{weather_cov:.1f}%", help="订单城市日中能找到天气数据的比例")
c3.metric("币价覆盖率", f"{crypto_cov:.1f}%", help="订单日期中能找到 BTC 价格的比例")

if weather_cov < 99.9 or crypto_cov < 99.9:
    st.warning("""
    部分订单找不到对应的天气/币价。影响分析只会使用**有订单的日期**，
    新抓取但没有订单的驱动数据不会进入分析。
    """)
else:
    st.success("订单与天气/币价覆盖完整，影响分析使用的是同一时间窗口。")

st.info("""
**数据刷新方式（当前为手动触发，未配置定时任务）：**
- 天气：`python -m orchestration.flows.ingest_weather`（最近 7 个已结束日期，按城市当地时区）
- 币价：`python -m orchestration.flows.ingest_crypto`（当前现货价）
- 历史演示数据：`python rebuild_demo_data.py`（365 天窗口，重生成订单）
- 顺便导出 Power BI：`python rebuild_demo_data.py --pbi`
- dbt 转换：`cd dbt_project && dbt run --profiles-dir .`
- 完整流程：`python -m orchestration.flows.run_full_pipeline`（默认采集模拟窗口内的历史数据并执行 dbt build）
- 离线流程：`python -m orchestration.flows.run_full_pipeline --offline`（使用已有驱动数据，仍执行质量门禁和 dbt build）

> 单独抓取新天气/币价只会追加维度数据；要让它们影响订单和看板，
> 需要重建订单（或调整 `config/settings.py` 的 `SIM_START` / `SIM_END` 后重建）。
""")

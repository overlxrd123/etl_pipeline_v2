"""
管道健康 — ETL 运行监控页
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import streamlit as st
import pandas as pd
from datetime import datetime
from dashboard.utils.db_queries import get_pipeline_stats

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

st.info("""
**数据刷新方式（当前为手动触发，未配置定时任务）：**
- 天气：`python -m orchestration.flows.ingest_weather`（最近 7 天）
- 币价：`python -m orchestration.flows.ingest_crypto`（当前现货价）
- 历史演示数据：`python rebuild_demo_data.py`（365 天窗口）
- dbt 转换：`cd dbt_project && dbt run --profiles-dir .`
""")

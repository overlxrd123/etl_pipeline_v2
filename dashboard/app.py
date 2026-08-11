"""
电商数据分析看板
数据工程 ETL 管道 — Streamlit 交互看板
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st

st.set_page_config(
    page_title="电商数据分析看板",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    .main-header {
        font-size: 2em;
        font-weight: 700;
        background: linear-gradient(135deg, #06d6a0, #118ab2);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0;
    }
    .sub-header {
        color: #64748b;
        font-size: 1em;
        margin-bottom: 20px;
    }
    .stMetric { background: #111827; padding: 16px; border-radius: 12px; border: 1px solid #1e293b; }
</style>
""", unsafe_allow_html=True)

with st.sidebar:
    st.markdown("## 📊 数据工程看板")
    st.markdown("*自动化 ETL 管道 · 数据仓库 · dbt · Prefect*")
    st.divider()

    st.markdown("### 导航")
    st.markdown("""
    - 📈 **概览** — KPI总览
    - 💰 **销售分析** — 销售趋势与排名
    - 🌤 **天气影响** — 天气与销售关联
    - 👥 **客户分层** — RFM客户价值分层
    - 🔧 **管道健康** — ETL运行监控
    """)

    st.divider()
    st.markdown("### 技术栈")
    st.caption("Python · Prefect · dbt · SQLite · Streamlit")
    st.caption("数据源: 电商模拟 + Open-Meteo天气 + CoinGecko加密")

# ── 主页 ─────────────────────────────────
st.markdown('<p class="main-header">电商数据分析看板</p>', unsafe_allow_html=True)
st.markdown('<p class="sub-header">自动化 ETL 管道驱动的实时商业智能看板</p>',
            unsafe_allow_html=True)

from dashboard.utils.db_queries import get_kpi_summary, get_pipeline_stats, get_monthly_trend, get_category_revenue
from dashboard.utils.charts import line_chart, bar_chart

kpi = get_kpi_summary()
cols = st.columns(5)
cols[0].metric("总营收", f"${kpi['total_revenue']:,.0f}")
cols[1].metric("总订单数", f"{kpi['total_orders']:,}")
cols[2].metric("客单价", f"${kpi['avg_order_value']:.0f}")
cols[3].metric("客户数", f"{kpi['unique_customers']:,}")
cols[4].metric("销售件数", f"{kpi['total_units']:,}")

st.divider()

col_left, col_right = st.columns(2)

with col_left:
    st.subheader("月度营收趋势")
    monthly = get_monthly_trend()
    monthly["月份标签"] = monthly["年份"].astype(str) + "-" + monthly["月份"].astype(str).str.zfill(2)
    st.plotly_chart(line_chart(monthly, "月份标签", "营收", "月度营收趋势"), width='stretch')

with col_right:
    st.subheader("各品类营收")
    cat = get_category_revenue()
    st.plotly_chart(bar_chart(cat, "品类", "营收", "各品类营收", horizontal=True), width='stretch')

st.divider()
st.subheader("数据仓库表统计")

stats = get_pipeline_stats()
cols = st.columns(len(stats))
for i, row in stats.iterrows():
    cols[i].metric(row["表名"], f"{row['行数']:,}")

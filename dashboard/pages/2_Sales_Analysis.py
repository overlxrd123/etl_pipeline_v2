"""
销售分析 — 深度分析页
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import streamlit as st
from dashboard.utils.db_queries import (
    get_top_products, get_category_revenue, get_daily_sales, get_monthly_trend,
)
from dashboard.utils.charts import line_chart, bar_chart

st.title("💰 销售分析")

days = st.slider("显示天数", 7, 365, 90)

st.subheader("月度营收趋势")
monthly = get_monthly_trend()
monthly["月份标签"] = monthly["年份"].astype(str) + "-" + monthly["月份"].astype(str).str.zfill(2)
st.plotly_chart(line_chart(monthly, "月份标签", "营收", "月度营收趋势"), width='stretch')

st.subheader("营收最高 Top 10 产品")
top = get_top_products(10)
st.plotly_chart(bar_chart(top, "产品名", "营收", "Top 10 产品营收排名", horizontal=True), width='stretch')

st.subheader(f"每日销售趋势（近{days}天）")
daily = get_daily_sales(days)
st.plotly_chart(line_chart(daily, "日期", "营收", "每日营收"), width='stretch')

st.subheader("品类表现")
cat = get_category_revenue()

c1, c2 = st.columns(2)
with c1:
    st.plotly_chart(bar_chart(cat, "品类", "营收", "各品类营收"), width='stretch')
with c2:
    cat_display = cat.copy()
    st.dataframe(cat_display.style.format({
        "营收": "${:,.0f}", "客单价": "${:,.0f}", "平均折扣": "{:.1f}%"
    }), width='stretch', hide_index=True)

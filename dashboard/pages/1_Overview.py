"""
概览 — KPI 总览页
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import streamlit as st
from dashboard.utils.db_queries import (
    get_kpi_summary, get_daily_sales, get_category_revenue,
    get_city_revenue, get_payment_breakdown,
)
from dashboard.utils.charts import line_chart, bar_chart, pie_chart

st.title("📈 概览")

kpi = get_kpi_summary()
cols = st.columns(5)
cols[0].metric("总营收", f"${kpi['total_revenue']:,.0f}")
cols[1].metric("总订单数", f"{kpi['total_orders']:,}")
cols[2].metric("客单价", f"${kpi['avg_order_value']:.0f}")
cols[3].metric("客户数", f"{kpi['unique_customers']:,}")
cols[4].metric("销售件数", f"{kpi['total_units']:,}")

st.divider()

st.subheader("每日销售趋势（近90天）")
daily = get_daily_sales(90)
st.plotly_chart(line_chart(daily, "日期", "营收", "每日营收"), width='stretch')

c1, c2 = st.columns(2)
with c1:
    st.subheader("各品类营收")
    cat = get_category_revenue()
    st.plotly_chart(bar_chart(cat, "品类", "营收", "各品类营收", horizontal=True), width='stretch')

with c2:
    st.subheader("各城市营收")
    city = get_city_revenue()
    st.plotly_chart(bar_chart(city, "城市", "营收", "各城市营收", horizontal=True), width='stretch')

st.subheader("支付方式分布")
pay = get_payment_breakdown()
st.plotly_chart(pie_chart(pay, "支付方式", "数量", "支付方式分布"), width='stretch')

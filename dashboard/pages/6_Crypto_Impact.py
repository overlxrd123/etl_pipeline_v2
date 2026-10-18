"""
币价影响 — BTC 涨跌与加密支付占比
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import streamlit as st
from dashboard.utils.db_queries import get_crypto_impact, get_crypto_impact_summary
from dashboard.utils.charts import line_chart, bar_chart

st.title("₿ 币价对销售的影响")
st.caption("BTC 上涨时，用户更愿意用加密币付款吗？")

impact = get_crypto_impact()
summary = get_crypto_impact_summary()

if impact.empty:
    st.warning(
        "暂无币价分析数据。请先运行 `python rebuild_demo_data.py`，"
        "再执行 `cd dbt_project && dbt run --profiles-dir .`"
    )
else:
    valid = impact.dropna(subset=["BTC价格"])
    latest = valid.iloc[-1] if len(valid) else None

    c1, c2, c3 = st.columns(3)
    if latest is not None:
        c1.metric("最新 BTC 价格", f"${latest['BTC价格']:,.0f}")
    c2.metric("整体加密支付占比", f"{impact['加密支付占比'].mean():.1f}%")
    c3.metric("分析天数", f"{len(impact)} 天")

    st.divider()

    left, right = st.columns(2)
    with left:
        st.subheader("BTC 收盘价")
        st.plotly_chart(
            line_chart(impact, "日期", "BTC价格", "BTC 每日收盘价 (USD)"),
            width='stretch',
        )
    with right:
        st.subheader("加密支付占比")
        st.plotly_chart(
            line_chart(impact, "日期", "加密支付占比", "每日加密支付订单占比 (%)"),
            width='stretch',
        )

    st.divider()
    st.subheader("不同行情下的平均加密支付占比")
    st.plotly_chart(
        bar_chart(summary, "行情", "平均加密支付占比",
                  "BTC 行情 vs 加密支付占比"),
        width='stretch',
    )

    st.dataframe(
        summary.style.format({
            "平均加密支付占比": "{:.2f}%",
            "平均日订单数": "{:,.0f}",
            "天数": "{:,}",
        }),
        width='stretch', hide_index=True,
    )

    st.info("""
    **效应设定（可验证）：**
    - BTC 单日上涨 >2% → 加密支付占比设为 **40%**
    - BTC 单日下跌 >2% → 加密支付占比设为 **20%**
    - 其他情况 → **30%**

    上表应能还原出接近这三组设定值的差异；如果不能，说明数据关联或分析口径有问题。
    """)

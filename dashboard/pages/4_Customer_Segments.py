"""
客户分层 — RFM 客户价值分析
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import streamlit as st
import plotly.express as px
from dashboard.utils.db_queries import get_rfm_segments
from dashboard.utils.charts import scatter_chart, pie_chart

st.title("👥 客户价值分层（RFM）")
st.caption("最近购买时间 · 购买频率 · 消费金额")

rfm = get_rfm_segments()

if rfm.empty:
    st.warning("暂无客户数据。")
else:
    rfm["rfm总分"] = rfm["r_score"] + rfm["f_score"] + rfm["m_score"]

    rfm["分层"] = rfm["segment"].map({
        'Champions': '核心客户', 'Loyal': '忠诚客户', 'Potential': '潜力客户',
        'At Risk': '流失风险', 'Lost': '已流失', 'Needs Attention': '需关注',
    }).fillna('需关注')

    c1, c2 = st.columns(2)

    with c1:
        st.subheader("客户分层占比")
        seg_counts = rfm.groupby("分层").size().reset_index(name="数量")
        st.plotly_chart(pie_chart(seg_counts, "分层", "数量", "客户分层分布"), width='stretch')

    with c2:
        st.subheader("各分层指标汇总")
        seg_summary = rfm.groupby("分层").agg(
            人数=("customer_id", "count"),
            平均距上次购买天=("距上次购买天", "mean"),
            平均购买次数=("购买次数", "mean"),
            平均消费金额=("消费金额", "mean"),
            总营收贡献=("消费金额", "sum"),
        ).round(1)
        st.dataframe(seg_summary.style.format({
            "平均消费金额": "${:,.0f}", "总营收贡献": "${:,.0f}", "平均距上次购买天": "{:.0f} 天"
        }), width='stretch')

    st.subheader("客户价值分布图")
    st.plotly_chart(
        scatter_chart(rfm, "购买次数", "消费金额", "分层", "购买频率 vs 消费金额", "距上次购买天"),
        width='stretch'
    )

    st.subheader("各城市客户分层")
    city_seg = rfm.groupby(["城市", "分层"]).size().reset_index(name="人数")
    fig = px.bar(city_seg, x="城市", y="人数", color="分层",
                 template="plotly_dark", barmode="stack",
                 color_discrete_sequence=["#06d6a0", "#118ab2", "#ffd166", "#ef476f", "#7b2ff7", "#64748b"])
    fig.update_layout(paper_bgcolor="#0d1520", plot_bgcolor="#0d1520",
                      font_color="#f8fafc", height=400)
    st.plotly_chart(fig, width='stretch')

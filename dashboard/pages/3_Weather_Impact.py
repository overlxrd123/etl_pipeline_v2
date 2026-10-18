"""
天气影响 — 天气对销售的影响分析
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import streamlit as st
from dashboard.utils.db_queries import get_weather_sales_summary
from dashboard.utils.charts import bar_chart, pie_chart

st.title("🌤 天气对销售的影响")
st.caption(
    "按城市日平均对比。订单指数已剔除日期/季节波动：100 = 该城市平常水平，"
    "低于 100 表示需求下降。订单量由真实天气驱动，效应参数见 config/settings.py。"
)

weather = get_weather_sales_summary()

if weather.empty:
    st.warning("暂无天气数据，请先运行：python rebuild_demo_data.py 或 python -m orchestration.flows.ingest_weather")
else:
    weather_display = weather.copy()
    weather_display["天气"] = weather_display["天气"].replace({
        "Clear": "晴天", "Mostly Clear": "大部晴", "Partly Cloudy": "多云",
        "Overcast": "阴天", "Foggy": "雾", "Rime Fog": "霜雾",
        "Light Drizzle": "毛毛雨", "Drizzle": "小雨", "Heavy Drizzle": "大雨",
        "Light Rain": "小雨", "Rain": "雨", "Heavy Rain": "大雨",
        "Light Snow": "小雪", "Snow": "雪", "Heavy Snow": "大雪",
        "Light Showers": "小阵雨", "Showers": "阵雨", "Heavy Showers": "大阵雨",
        "Thunderstorm": "雷暴", "Hail Thunderstorm": "冰雹雷暴", "Severe Thunderstorm": "强雷暴",
        "Unknown": "未知",
    })

    c1, c2, c3 = st.columns(3)

    with c1:
        st.subheader("订单指数")
        st.plotly_chart(
            bar_chart(weather_display, "天气", "订单指数", "天气-订单指数（100=平常水平）",
                      horizontal=True),
            width='stretch'
        )

    with c2:
        st.subheader("平均日营收")
        st.plotly_chart(
            bar_chart(weather_display, "天气", "营收", "天气-营收对比", horizontal=True),
            width='stretch'
        )

    with c3:
        st.subheader("样本分布")
        st.plotly_chart(
            pie_chart(weather_display, "天气", "城市天数", "天气样本分布"),
            width='stretch'
        )

    st.subheader("详细数据（城市日平均）")
    st.dataframe(weather_display.style.format({
        "营收": "${:,.0f}", "客单价": "${:,.0f}",
        "订单数": "{:,.1f}", "城市天数": "{:,}", "订单指数": "{:.1f}"
    }), width='stretch', hide_index=True)

    if len(weather_display) >= 2:
        best = weather_display.sort_values("订单指数", ascending=False).iloc[0]
        worst = weather_display.sort_values("订单指数", ascending=False).iloc[-1]
        st.info(f"""
        **关键发现（已剔除日期/季节波动）：**
        - 订单指数最高：**{best['天气']}**（{best['订单指数']:.1f}）
        - 订单指数最低：**{worst['天气']}**（{worst['订单指数']:.1f}）

        **效应设定：** 雨天订单量 ×0.90，雷暴/降雪 ×0.80，高温 ×0.95。
        由于样本量和取整误差，分析结果不会与设定值完全相等，但方向和幅度应基本一致。
        """)

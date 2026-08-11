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
st.caption("晴天卖得多还是雨天卖得多？数据说话。")

weather = get_weather_sales_summary()

if weather.empty:
    st.warning("暂无天气数据，请先运行天气采集管道：python -m src.extract.weather_api")
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

    c1, c2 = st.columns(2)

    with c1:
        st.subheader("不同天气下的营收")
        st.plotly_chart(
            bar_chart(weather_display, "天气", "营收", "天气-营收对比", horizontal=True),
            width='stretch'
        )

    with c2:
        st.subheader("订单分布（按天气）")
        st.plotly_chart(
            pie_chart(weather_display, "天气", "订单数", "订单-天气分布"),
            width='stretch'
        )

    st.subheader("详细数据")
    st.dataframe(weather_display.style.format({
        "营收": "${:,.0f}", "客单价": "${:,.0f}", "订单数": "{:,}"
    }), width='stretch', hide_index=True)

    if len(weather_display) >= 2:
        best = weather_display.iloc[0]
        worst = weather_display.iloc[-1]
        st.info(f"""
        **关键发现：**
        - 销售额最高的天气：**{best['天气']}**（营收 ${best['营收']:,.0f}，{best['订单数']:,} 单）
        - 销售额最低的天气：**{worst['天气']}**（营收 ${worst['营收']:,.0f}，{worst['订单数']:,} 单）
        """)

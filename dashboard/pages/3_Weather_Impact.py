"""
天气影响 — 天气对销售的影响分析
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import streamlit as st
from dashboard.utils.db_queries import get_weather_sales_summary, get_weather_effect
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

# ── 效应还原：同日跨城市对比 ───────────────────────────────────────────
st.divider()
st.subheader("🎯 效应还原：同日跨城市对比")
st.caption(
    "上面的「订单指数」是跨天比较，雪天集中在冬季、高温集中在夏季，"
    "季节和周末效应会和天气效应混在一起。这里改成**固定日期、比较同日不同城市**："
    "同一天所有城市共享同一基础订单量，只有天气乘数不同，"
    "所以「当天受影响城市均值 ÷ 当天未受影响城市均值」就是纯粹的天气效应。"
)

effect = get_weather_effect()

if effect.empty:
    st.warning("未找到 mart_weather_effect，请先运行：dbt run --select mart_weather_effect")
else:
    effect_display = effect.copy()
    effect_display = effect_display[[
        "因子", "说明", "受影响城市天数", "可比天数",
        "未隔离比值", "隔离后比值", "设定值", "偏差百分点",
    ]]

    st.dataframe(effect_display.style.format({
        "未隔离比值": "{:.4f}", "隔离后比值": "{:.4f}",
        "设定值": "{:.2f}", "偏差百分点": "{:+.2f}",
    }), width='stretch', hide_index=True)

    valid = effect.dropna(subset=["隔离后比值"])
    if not valid.empty:
        max_dev = valid["偏差百分点"].abs().max()
        st.success(
            f"同日对比法把设定乘数还原到 **{valid['隔离后比值'].min():.3f} ~ "
            f"{valid['隔离后比值'].max():.3f}**，"
            f"最大偏差 **{max_dev:.2f} 个百分点**；"
            f"而直接跨天比较给出的是 "
            f"{valid['未隔离比值'].min():.3f} ~ {valid['未隔离比值'].max():.3f}，"
            "明显被季节效应拉偏。"
        )

    no_sample = effect[effect["隔离后比值"].isna()]
    if not no_sample.empty:
        st.caption(
            "无样本因子：" + "、".join(no_sample["因子"].tolist())
            + " —— 当前天气数据里没有这类天气的城市日，属于样本问题，不是管道问题。"
        )

st.markdown("""
**为什么必须这样比？**

- 直接比较「雪天订单」和「非雪天订单」：雪天集中在冬季，冬季本身订单基数就低，
  算出来的差距里既有天气效应也有季节效应，无法归因。
- 同日跨城市比较：日期被固定住，季节、周末、节假日对所有城市影响相同，被除法约掉，
  剩下的就只剩天气乘数。
- 这也是数据分析里「控制变量」最朴素的应用：**想让一个因素显形，就让其他因素保持相同。**
""")

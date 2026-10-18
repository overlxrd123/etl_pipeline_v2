"""
Streamlit 图表构建器 — 基于 Plotly
"""
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

# 配色
COLORS = ["#06d6a0", "#118ab2", "#ef476f", "#ffd166", "#073b4c", "#7b2ff7"]


def kpi_tile(label: str, value: str, delta: str = None):
    """KPI 指标卡片"""
    fig = go.Figure(go.Indicator(
        mode="number+delta" if delta else "number",
        value=float(value.replace("$", "").replace(",", "").replace("K", "000").replace("M", "000000"))
            if isinstance(value, str) else value,
        title={"text": label, "font": {"size": 14, "color": "#cbd5e1"}},
        number={"font": {"size": 36, "color": "#06d6a0"},
                "prefix": "$" if label.lower() in ["total revenue", "avg order value", "总营收", "客单价"] else ""},
        delta={"reference": float(delta)} if delta else None,
    ))
    fig.update_layout(height=160, margin=dict(l=10, r=10, t=10, b=10),
                      paper_bgcolor="#111827", font_color="#f8fafc")
    return fig


def line_chart(df: pd.DataFrame, x: str, y: str, title: str,
               color: str = None, weekend_col: str = None):
    """折线图 — 销售趋势"""
    fig = px.line(df, x=x, y=y, color=color,
                  title=title,
                  template="plotly_dark",
                  color_discrete_sequence=COLORS)
    fig.update_layout(
        paper_bgcolor="#0d1520", plot_bgcolor="#0d1520",
        font_color="#f8fafc", title_font_color="#ffffff",
        height=400, margin=dict(l=10, r=10, t=40, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
    )
    return fig


def bar_chart(df: pd.DataFrame, x: str, y: str, title: str, horizontal: bool = False):
    """柱状图 — 排名对比"""
    if horizontal:
        fig = px.bar(df, y=x, x=y, title=title, orientation='h',
                     template="plotly_dark", color_discrete_sequence=COLORS)
    else:
        fig = px.bar(df, x=x, y=y, title=title,
                     template="plotly_dark", color_discrete_sequence=COLORS)
    fig.update_layout(
        paper_bgcolor="#0d1520", plot_bgcolor="#0d1520",
        font_color="#f8fafc", title_font_color="#ffffff",
        height=400, margin=dict(l=10, r=10, t=40, b=10),
    )
    return fig


def pie_chart(df: pd.DataFrame, names: str, values: str, title: str):
    """饼图 — 分布占比"""
    fig = px.pie(df, names=names, values=values, title=title,
                 template="plotly_dark", color_discrete_sequence=COLORS,
                 hole=0.35)
    fig.update_traces(textinfo='percent+label', textfont_size=11,
                      textfont_color="#f8fafc")
    fig.update_layout(
        paper_bgcolor="#0d1520", font_color="#f8fafc",
        title_font_color="#ffffff", height=400,
        margin=dict(l=10, r=10, t=40, b=10),
    )
    return fig


def scatter_chart(df: pd.DataFrame, x: str, y: str, color: str,
                  title: str, size: str = None):
    """散点图 — RFM 等"""
    fig = px.scatter(df, x=x, y=y, color=color, size=size,
                     title=title, template="plotly_dark",
                     color_discrete_sequence=COLORS)
    fig.update_layout(
        paper_bgcolor="#0d1520", plot_bgcolor="#0d1520",
        font_color="#f8fafc", title_font_color="#ffffff",
        height=450, margin=dict(l=10, r=10, t=40, b=10),
    )
    return fig


def metric_row(values: list[dict]):
    """一行指标（首页概览用）"""
    cols = []
    for v in values:
        cols.append(go.Indicator(
            mode="number",
            title={"text": v["label"], "font": {"size": 12, "color": "#cbd5e1"}},
            number={"font": {"size": 28, "color": "#06d6a0"}, "prefix": v.get("prefix", ""),
                    "valueformat": v.get("format", ",.0f")},
            value=v["value"],
        ))
    fig = go.Figure(cols)
    fig.update_layout(
        grid={"rows": 1, "columns": len(values)},
        height=120, margin=dict(l=10, r=10, t=10, b=10),
        paper_bgcolor="#0d1520", font_color="#f8fafc",
    )
    return fig

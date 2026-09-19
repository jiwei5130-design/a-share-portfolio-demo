"""Portfolio Demo 市场环境（V2.1：面向用户的产品化展示）。

所有数字仍来自只读 API；未新增算法/评分/指标。研发口径与数据边界不在本页展示。
"""

import altair as alt
import pandas as pd
import streamlit as st

from portfolio_demo.api_client import (
    ApiError,
    market_overview,
    market_regime,
    market_regime_history,
    overview,
)
from portfolio_demo.presentation import (
    format_number,
    format_pct,
    format_turnover_cny,
    turnover_metrics,
)


try:
    strategy = overview()
    market_date = strategy["current_market_date"]
    market = market_overview(market_date)
    regime = market_regime(market_date)
except ApiError as exc:
    st.error(str(exc), icon=":material/error:")
    st.stop()

latest = market["breadth"]["latest"]
ma5 = latest["ma_breadth"]["ma5"]
ma20 = latest["ma_breadth"]["ma20"]
ma60 = latest["ma_breadth"]["ma60"]
turnover = turnover_metrics(market["breadth"]["history"])

st.write("观察大盘强弱、量能与市场宽度。")

st.subheader("核心判断")
with st.container(border=True):
    state_col, score_col = st.columns(2)
    with state_col:
        st.caption("当前市场环境")
        st.markdown(f"# {regime['state_label']}")
    with score_col:
        st.caption("市场环境评分")
        st.markdown(f"# {regime['regime_score']:.2f}")
turnover_cols = st.columns(3)
with turnover_cols[0]:
    st.metric("市场成交额", format_turnover_cny(turnover["latest"]), border=True)
with turnover_cols[1]:
    st.metric("较前一交易日", format_pct(turnover["change_1d"]), border=True)
with turnover_cols[2]:
    st.metric("MA20 站上比例", format_pct(ma20["above_ratio"]), border=True)
st.caption(
    f"5日平均成交额 {format_turnover_cny(turnover['avg_5d'])} · "
    f"20日平均成交额 {format_turnover_cny(turnover['avg_20d'])}"
)

st.subheader("市场环境评分")
with st.container(border=True):
    score_cols = st.columns(3)
    with score_cols[0]:
        st.metric("综合评分", f"{regime['regime_score']:.2f}", border=True)
    with score_cols[1]:
        st.metric("指数表现", f"{regime['components']['index_score']:.2f}", border=True)
    with score_cols[2]:
        st.metric("市场宽度", f"{regime['components']['breadth_score']:.2f}", border=True)
    st.caption("评分范围：-100 ～ +100（负值偏弱，正值偏强）")
    st.caption("分档：≥60 强势｜≥20 偏强｜≥-20 震荡｜≥-60 偏弱｜＜-60 弱势")
    index_names = "、".join(item["name"] for item in market["indices"]["items"])
    st.caption(f"指数表现评分构成：{index_names}（各指数收盘站上 MA5 / MA20 / MA60 的比例）")
    st.caption("市场宽度评分构成：样本中收盘站上 MA5 / MA20 / MA60 的比例")

st.subheader("市场涨跌与强弱")
breadth_cols = st.columns(3)
with breadth_cols[0]:
    st.metric("上涨", format_number(latest["advances"]), border=True)
with breadth_cols[1]:
    st.metric("下跌", format_number(latest["declines"]), border=True)
with breadth_cols[2]:
    st.metric("平盘", format_number(latest["unchanged"]), border=True)
ma_cols = st.columns(3)
with ma_cols[0]:
    st.metric("站上 MA5", format_pct(ma5["above_ratio"]), border=True)
with ma_cols[1]:
    st.metric("站上 MA20", format_pct(ma20["above_ratio"]), border=True)
with ma_cols[2]:
    st.metric("站上 MA60", format_pct(ma60["above_ratio"]), border=True)

st.subheader("市场指数")
index_rows = [
    {
        "指数": item["name"],
        "收盘": item["close"],
        "1日": item["return_1d"],
        "5日": item["return_5d"],
        "20日": item["return_20d"],
    }
    for item in market["indices"]["items"]
]
st.dataframe(
    pd.DataFrame(index_rows),
    hide_index=True,
    column_config={
        "收盘": st.column_config.NumberColumn(format="%.2f"),
        "1日": st.column_config.NumberColumn(format="percent"),
        "5日": st.column_config.NumberColumn(format="percent"),
        "20日": st.column_config.NumberColumn(format="percent"),
    },
)

st.subheader("市场环境走势")
st.caption(f"过去 120 个交易日 · 数据截至 {market_date}")
try:
    regime_history = market_regime_history(market_date, 120)
    history_frame = pd.DataFrame(regime_history["items"])
    history_frame["date"] = pd.to_datetime(history_frame["date"])
    line = (
        alt.Chart(history_frame)
        .mark_line(color="#155EEF", strokeWidth=2)
        .encode(
            x=alt.X(
                "date:T",
                title=None,
                axis=alt.Axis(format="%Y-%m", tickCount=6, labelAngle=0, grid=False),
            ),
            y=alt.Y(
                "regime_score:Q",
                title="市场环境评分",
                scale=alt.Scale(domain=[-100, 100]),
                axis=alt.Axis(tickCount=5, grid=True, gridColor="#EEF2F7"),
            ),
            tooltip=[
                alt.Tooltip("date:T", title="日期"),
                alt.Tooltip("regime_score:Q", title="评分", format=".2f"),
            ],
        )
    )
    zero_line = (
        alt.Chart(pd.DataFrame({"y": [0]}))
        .mark_rule(color="#B9C4D2", strokeDash=[4, 4])
        .encode(y="y:Q")
    )
    st.altair_chart((line + zero_line).properties(height=260))
    st.caption(f"当前评分 {regime['regime_score']:.2f}（0 分为强弱分界，负值偏弱）")
except ApiError:
    st.info("历史走势数据暂不可用。", icon=":material/info:")

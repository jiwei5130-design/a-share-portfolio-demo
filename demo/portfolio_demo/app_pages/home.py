"""Portfolio Demo 首页｜Dashboard（V2：结果优先的产品化展示层）。

只做展示层重组：所有数字仍来自只读 API，未新增算法/评分/推荐。
研究细节（六项事实、数据边界、负结果等）下沉到市场环境 / 策略中心 / 今日信号 / 个股详情。
"""

import streamlit as st

from portfolio_demo.api_client import (
    ApiError,
    market_overview,
    market_regime,
    overview,
    performance,
    sector_overview,
    signals,
    strategy1_regime_performance,
)
from portfolio_demo.presentation import (
    format_number,
    format_pct,
    format_turnover_cny,
    turnover_comparison_label,
    turnover_metrics,
)


try:
    strategy = overview()
    market_date = strategy["current_market_date"]
    market = market_overview(market_date)
    regime = market_regime(market_date)
    sectors = sector_overview(market_date)
    signal_payload = signals(market_date)
except ApiError as exc:
    st.error(str(exc), icon=":material/error:")
    st.stop()

try:
    backtest = performance()
    regime_research = strategy1_regime_performance()
except ApiError:
    backtest = None
    regime_research = None

latest = market["breadth"]["latest"]
turnover = turnover_metrics(market["breadth"]["history"])
ma20 = latest["ma_breadth"]["ma20"]
current_regime_row = None
if regime_research is not None:
    current_regime_row = next(
        (row for row in regime_research["by_regime"] if row["state"] == regime["state"]),
        None,
    )

st.header("A股智能交易决策系统 V1.0")
st.write("从市场环境到策略与个股信号，提供一套可解释的交易决策辅助。")
st.caption(f"数据截至 {market_date}")

st.subheader("今日市场")
environment_col, kpi_col = st.columns([1, 2])
with environment_col:
    with st.container(border=True, height="stretch"):
        st.metric("当前市场环境", regime["state_label"], border=True)
        st.metric("市场环境评分", f"{regime['regime_score']:.2f}", border=True)
        st.caption(f"指数分 {regime['components']['index_score']:.2f} · 宽度分 {regime['components']['breadth_score']:.2f}")
with kpi_col:
    with st.container(border=True, height="stretch"):
        kpi_cols = st.columns(3)
        with kpi_cols[0]:
            st.metric("市场成交额", format_turnover_cny(turnover["latest"]), border=True)
        with kpi_cols[1]:
            st.metric("较前一交易日", format_pct(turnover["change_1d"]), border=True)
        with kpi_cols[2]:
            st.metric("MA20 站上比例", format_pct(ma20["above_ratio"]), border=True)
        st.caption(f"成交额量能：{turnover_comparison_label(turnover['vs_5d_avg'], turnover['vs_20d_avg'])}")

st.subheader("市场与板块")
environment_summary_col, sector_summary_col = st.columns(2)
with environment_summary_col:
    with st.container(border=True, height="stretch"):
        st.markdown("**市场环境**")
        st.markdown(f"### {regime['state_label']}　{regime['regime_score']:.2f}")
        st.caption("指数表现偏弱 · 市场宽度中性偏弱")
with sector_summary_col:
    with st.container(border=True, height="stretch"):
        st.markdown("**强势板块**")
        strongest = sectors["items"][:3]
        st.markdown("### " + " · ".join(item["sector_name"] for item in strongest))
        st.caption("近 5 日表现相对活跃")

st.subheader("今日适合策略")
strategy_col, research_col = st.columns(2)
with strategy_col:
    with st.container(border=True, height="stretch"):
        st.markdown("**隔日超短趋势策略**　当前环境下重点关注")
        if backtest is not None:
            st.write(
                f"{format_number(backtest['total_trades'])} 笔历史交易 · "
                f"{format_pct(backtest['win_rate'])} 胜率 · "
                f"{format_pct(backtest['avg_return'])} 平均净收益"
            )
        if current_regime_row is not None:
            st.caption(
                f"当前环境（{regime['state_label']}）历史分层："
                f"{format_number(current_regime_row['trade_count'])} 笔 · "
                f"{format_pct(current_regime_row['win_rate'])} 胜率（描述性）"
            )
        st.caption("历史统计仅供参考，不构成策略推荐。")
        st.link_button("查看策略详情", "strategies", icon=":material/arrow_forward:")
with research_col:
    with st.container(border=True, height="stretch"):
        st.markdown("**支撑位策略**")
        st.write("基于历史价格形成的关键支撑位，观察价格回落后的支撑与反弹表现。")
        st.link_button("查看策略详情", "strategies", icon=":material/arrow_forward:")

st.subheader("今日重点信号")
if not signal_payload["total"]:
    st.info(f"{signal_payload['signal_date']}：该日期真实筛选结果为空。", icon=":material/info:")
else:
    signal_cols = st.columns(min(signal_payload["total"], 3))
    for index, item in enumerate(signal_payload["items"][:3]):
        with signal_cols[index]:
            with st.container(border=True, height="stretch"):
                st.markdown(f"**{item['name']} {item['code']}**")
                st.caption("隔日超短趋势策略 · 候选信号")
                st.markdown("**信号状态：候选**")
                st.write("价格位置条件符合策略要求（规则触发）。")
                st.link_button(
                    "查看个股详情",
                    f"stock?code={item['code']}",
                    icon=":material/arrow_forward:",
                )
    st.caption("候选信号不代表推荐买入；详情与交易条件见「今日信号」页。")

st.caption("历史研究结果不代表未来收益，本系统用于研究与决策辅助，不构成投资建议。")

"""Portfolio Demo 个股详情（V2.1：面向用户的个股信号与风险展示）。

所有数字来自只读 API；未新增算法/评分/排序。研发口径与内部字段不在本页展示。
"""

import pandas as pd
import streamlit as st

from portfolio_demo.api_client import ApiError, stock_detail, stock_sector_context
from portfolio_demo.presentation import format_number, format_pct, format_price


EXIT_REASON_LABELS = {
    "Extreme_Risk_Stop": "风险止损",
    "Trend_Break_Stop": "趋势破坏",
    "Maximum_Holding_Period": "最大持仓",
}

code = (st.query_params.get("code") or "").strip()

st.write("查看该股票的信号条件、风险约束与历史验证。")
st.link_button("返回今日信号", "signals", icon=":material/arrow_back:")

if not code:
    st.info("未指定股票代码，请从「今日信号」进入个股详情。", icon=":material/info:")
    st.stop()

try:
    detail = stock_detail(code)
except ApiError as exc:
    st.warning(f"数据不足：{exc}", icon=":material/warning:")
    st.caption("请返回「今日信号」选择候选股票。")
    st.stop()

try:
    sector_context = stock_sector_context(code)
except ApiError:
    sector_context = {}

summary = detail["market_data_summary"]
latest_signal = detail["latest_signal"]
performance = detail["performance"]
trades = detail.get("historical_trade_records") or []
exit_stats = detail.get("sell_reason_statistics")

with st.container(border=True):
    st.markdown(f"**{detail['code']} {detail['name']}**")
    header_cols = st.columns(2)
    with header_cols[0]:
        st.metric("交易所 / 市场", f"{detail['exchange']} / {detail['market']}", border=True)
    with header_cols[1]:
        st.metric("行情区间", f"{summary['first_date']} ～ {summary['last_date']}", border=True)

st.subheader("当前信号")
if latest_signal is None:
    st.info("该股票暂无历史信号。", icon=":material/info:")
else:
    with st.container(border=True):
        st.markdown(f"**信号日期 {latest_signal['signal_date']}**　候选信号｜等待 T+1 成交确认")
        st.markdown("**信号条件**")
        st.write(f"- ✓ 短期趋势条件满足：均线距离 {format_pct(latest_signal['ma5_distance'], 4)}")
        st.write(f"- ✓ 价格位置条件满足：压力距离 {format_pct(latest_signal['pressure_distance'], 4)}")
        st.write("- 成交确认：待 T+1 竞价确认")
        st.markdown(
            f"**计划买入价**：{format_price(latest_signal['buy_price'])}"
            "（计划买入价 ≠ 实际成交价）"
        )
        st.markdown("**成交条件**：T+1 开盘价不高于计划价才可能成交。")
        st.markdown(f"**规则满足度**：{latest_signal['score']}")

st.subheader("风险与退出约束")
with st.container(border=True):
    st.markdown("**退出规则**")
    st.write("1. 风险止损：从最早可卖日开始，盘中触及止损条件时退出。")
    st.write("2. 趋势破坏：收盘价跌破短期均线时退出。")
    st.write("3. 最大持仓：前两项均未触发时，按最大持仓时间退出。")
    st.caption("规则满足不等于上涨；本页不展示任何自动买卖指令。")

st.subheader("历史验证")
with st.container(border=True):
    if not trades:
        st.info("该股票暂无历史交易记录。", icon=":material/info:")
    else:
        hist_cols = st.columns(4)
        with hist_cols[0]:
            st.metric("历史交易", f"{format_number(performance['trade_count'])} 笔", border=True)
        with hist_cols[1]:
            st.metric("胜率", format_pct(performance["win_rate"]), border=True)
        with hist_cols[2]:
            st.metric("平均收益", format_pct(performance["average_return"]), border=True)
        with hist_cols[3]:
            st.metric("累计简单收益", format_pct(performance["cumulative_simple_return"]), border=True)
        returns = [item["return"] for item in trades]
        st.caption(
            f"该股历史最差单笔收益 {format_pct(min(returns))}｜最好单笔收益 {format_pct(max(returns))}"
            "（由该股历史交易记录聚合，非策略整体口径）。"
        )
        trade_frame = pd.DataFrame(trades).rename(
            columns={
                "buy_date": "买入日期",
                "buy_price": "买入价格",
                "sell_date": "卖出日期",
                "sell_price": "卖出价格",
                "holding_days": "持仓天数",
                "return": "收益率",
                "exit_reason": "退出原因",
            }
        )[["买入日期", "买入价格", "卖出日期", "卖出价格", "持仓天数", "收益率", "退出原因"]]
        trade_frame["退出原因"] = trade_frame["退出原因"].map(EXIT_REASON_LABELS).fillna(
            trade_frame["退出原因"]
        )
        st.dataframe(
            trade_frame,
            hide_index=True,
            column_config={
                "买入价格": st.column_config.NumberColumn(format="%.3f"),
                "卖出价格": st.column_config.NumberColumn(format="%.3f"),
                "收益率": st.column_config.NumberColumn(format="percent"),
            },
        )
        if exit_stats:
            st.caption(
                "退出原因统计："
                + "｜".join(
                    f"{EXIT_REASON_LABELS.get(key, key)} {value}"
                    for key, value in exit_stats.items()
                )
            )

st.subheader("所属行业")
with st.container(border=True):
    sector = sector_context.get("sector")
    sector_name = None
    if isinstance(sector, dict):
        sector_name = sector.get("sector_name") or sector.get("name")
    if sector_name:
        st.markdown(f"**{sector_name}**")
    else:
        st.markdown("行业信息暂未提供。")

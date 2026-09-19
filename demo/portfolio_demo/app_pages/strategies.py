"""Portfolio Demo 策略中心（V2.1：面向用户的策略产品展示）。

只读调用正式 API；未新增算法/指标/排序。研发口径、研究状态与数据边界不在本页展示。
"""

import pandas as pd
import streamlit as st

from portfolio_demo.api_client import (
    ApiError,
    overview,
    performance,
    strategy1_portfolio_risk,
    strategy1_regime_performance,
    strategy2_landmark_evidence,
    strategy2_landmark_research,
)
from portfolio_demo.presentation import format_number, format_pct


try:
    strategy = overview()
    backtest = performance()
    regime_research = strategy1_regime_performance()
    portfolio = strategy1_portfolio_risk()
    gate = strategy2_landmark_research()
    evidence = strategy2_landmark_evidence()
except ApiError as exc:
    st.error(str(exc), icon=":material/error:")
    st.stop()

baseline = portfolio["portfolios"][portfolio["baseline_portfolio"]]
landmark = evidence["landmark"]
trade_20d = landmark["trade_level"]["L_ALL"]["TIME_20"]

st.write("查看当前策略体系、历史验证表现与研究结果。")

st.header("隔日超短趋势策略")

st.subheader("历史验证表现")
st.caption(
    f"历史样本：2020-01-01 — {strategy['current_market_date']}｜"
    f"历史买入信号 {format_number(regime_research['signal_count'])}｜"
    f"实际成交 {format_number(backtest['total_trades'])} 笔"
)
s1_metric_cols = st.columns(4)
with s1_metric_cols[0]:
    st.metric("胜率", format_pct(backtest["win_rate"]), border=True)
with s1_metric_cols[1]:
    st.metric("平均净收益", format_pct(backtest["avg_return"]), border=True)
with s1_metric_cols[2]:
    st.metric("盈亏比", f"{backtest['profit_loss_ratio']:.2f}", border=True)
with s1_metric_cols[3]:
    st.metric("组合模拟最大回撤", format_pct(baseline["max_drawdown"]), border=True)

st.subheader("资金管理敏感性")
sensitivity_rows = [
    {
        "方案": name,
        "单笔仓位": item["position_size"],
        "最大持仓": item["max_positions"],
        "组合模拟最大回撤": item["max_drawdown"],
    }
    for name, item in portfolio["portfolios"].items()
]
st.dataframe(
    pd.DataFrame(sensitivity_rows),
    hide_index=True,
    column_config={
        "单笔仓位": st.column_config.NumberColumn(format="localized"),
        "最大持仓": st.column_config.NumberColumn(format="localized"),
        "组合模拟最大回撤": st.column_config.NumberColumn(format="percent"),
    },
)
st.caption("不同资金管理方案下的组合模拟结果。")

st.subheader("策略逻辑")
st.write("基于短期趋势与价格位置条件，寻找符合规则的隔日交易机会。")

st.divider()

st.header("支撑位策略")

st.subheader("历史研究表现")
st.caption(
    f"研究样本：{format_number(landmark['definition']['stocks'])} 只股票 / "
    f"{format_number(landmark['definition']['formal_landmarks'])} 个支撑位地标｜"
    f"回踩事件 {format_number(landmark['revisit']['events'])}｜"
    f"研究交易记录 {format_number(landmark['revisit']['trades'])}｜20 日研究退出口径"
)
s2_metric_cols = st.columns(4)
with s2_metric_cols[0]:
    st.metric("胜率", format_pct(trade_20d["win_rate"]), border=True)
with s2_metric_cols[1]:
    st.metric("平均净收益", format_pct(trade_20d["average_net_return"]), border=True)
with s2_metric_cols[2]:
    st.metric("盈亏比", f"{trade_20d['payoff']:.2f}", border=True)
with s2_metric_cols[3]:
    st.metric(
        "组合模拟最大回撤",
        format_pct(landmark["portfolio"]["L_ALL"]["TIME_20"]["max_drawdown"]),
        border=True,
    )
validation = gate.get("return_validation") or []
if validation:
    st.caption(f"研究结果：回踩支撑位相对普通回调{validation[0]['value']}。")

st.subheader("策略逻辑")
st.write(
    "识别历史价格形成的关键支撑位，观察价格回落到支撑位附近后的表现，"
    "寻找具有研究价值的反弹机会。"
)

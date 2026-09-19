"""Portfolio Demo 今日信号（V2.1：面向用户的候选信号展示）。

所有数字来自只读 API；未新增算法/评分/排序。研发口径与内部字段不在本页展示。
"""

import pandas as pd
import streamlit as st

from portfolio_demo.api_client import (
    ApiError,
    market_regime,
    overview,
    signals,
)
from portfolio_demo.presentation import format_pct, format_price


try:
    strategy = overview()
    market_date = strategy["current_market_date"]
    payload = signals(market_date)
    regime = market_regime(market_date)
except ApiError as exc:
    st.error(f"数据服务暂不可用：{exc}", icon=":material/error:")
    st.stop()

st.write("从市场环境到个股条件，形成可解释的候选信号。")

metric_cols = st.columns(4)
with metric_cols[0]:
    st.metric("数据日期", market_date, border=True)
with metric_cols[1]:
    st.metric("当前策略", "隔日超短趋势策略", border=True)
with metric_cols[2]:
    st.metric("候选数量", f"{payload['total']} 条", border=True)
with metric_cols[3]:
    st.metric("市场环境", regime["state_label"], border=True)

st.subheader("决策链路")
st.markdown("**市场环境 → 策略背景 → 个股条件 → 信号产生 → T+1 成交确认 → T+2 最早退出**")
chain_rows = [
    {"步骤": "① 市场环境", "内容": f"当前市场环境：{regime['state_label']}"},
    {"步骤": "② 策略背景", "内容": "隔日超短趋势策略"},
    {"步骤": "③ 个股条件", "内容": "短期趋势与价格位置条件"},
    {"步骤": "④ 信号产生", "内容": f"T 日收盘确认，候选 {payload['total']} 条"},
    {"步骤": "⑤ T+1 成交确认", "内容": "T+1 开盘价不高于计划价才可能成交"},
    {"步骤": "⑥ T+2 最早退出", "内容": "最早 T+2 按退出规则判断"},
]
st.dataframe(pd.DataFrame(chain_rows), hide_index=True)
st.caption("以上为信号形成过程，不构成自动推荐。")

st.subheader("今日候选")
if not payload["total"]:
    st.info(f"{payload['signal_date']}：该日期筛选结果为空。", icon=":material/info:")
else:
    st.caption(
        f"{payload['signal_date']} 共 {payload['total']} 条候选"
        f"（以下展示前 {min(payload['total'], 5)} 条）。"
    )
    for item in payload["items"][:5]:
        with st.container(border=True):
            st.markdown(f"**{item['code']} {item['name']}**　候选信号｜等待 T+1 成交确认")
            st.caption(
                f"数据日期 {item['signal_date']}｜隔日超短趋势策略"
                f"｜规则满足度 {item['score']}"
            )
            st.markdown("**为什么产生**")
            st.write(f"- ✓ 短期趋势条件满足：均线距离 {format_pct(item['ma5_distance'], 4)}")
            st.write(f"- ✓ 价格位置条件满足：压力距离 {format_pct(item['pressure_distance'], 4)}")
            st.write("- 成交确认：待 T+1 竞价确认")
            st.markdown(
                f"**计划买入价 {format_price(item['buy_price'])}**"
                "｜成交条件：T+1 开盘价不高于计划价才可能成交"
            )
            st.caption("计划买入价 ≠ 实际成交价；规则满足不代表上涨。")
            st.link_button(
                f"查看 {item['code']} 个股详情",
                f"stock?code={item['code']}",
                icon=":material/candlestick_chart:",
            )

st.subheader("交易约束（A股 T+1）")
st.warning(
    "A股 T+1 约束：T+1 买入后不能当日卖出，最早 T+2 退出。",
    icon=":material/gavel:",
)
st.markdown(
    "**T 日** 产生信号 → **T+1** 满足成交条件才可能成交（且不能卖出） → **T+2** 最早允许退出"
)
st.caption("退出按固定规则执行：风险止损 → 趋势破坏 → 最大持仓；本页不展示任何自动买卖指令。")

st.subheader("风险提示")
st.markdown("**计划买入价 ≠ 实际成交价**　计划价只是 T+1 挂单条件，是否成交取决于 T+1 开盘价。")
st.markdown("**规则满足 ≠ 上涨概率**　规则满足度只表示策略条件被满足的程度。")
st.markdown("**候选 ≠ 推荐买入**　候选信号用于研究与决策辅助，不构成买卖建议。")

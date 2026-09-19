"""Portfolio Demo 板块环境（V2.1：面向用户的产品化展示）。

所有数字来自只读 API；未新增算法/指标。研发口径与数据边界不在本页展示。
Online Dataset V1 适配：日期选择器窗口 250 → 120 个交易日（与线上数据窗口一致）。
"""

import pandas as pd
import streamlit as st

from portfolio_demo.api_client import (
    ApiError,
    market_regime_history,
    overview,
    sector_overview,
)


try:
    latest_date = overview()["current_market_date"]
except ApiError as exc:
    st.error(str(exc), icon=":material/error:")
    st.stop()

try:
    trading_dates = [item["date"] for item in market_regime_history(None, 120)["items"]][::-1]
except ApiError:
    trading_dates = [latest_date]

st.write("观察行业表现、活跃度与板块轮动特征。")

date_col, _ = st.columns([1, 3])
with date_col:
    selected_date = st.selectbox("数据日期", trading_dates, index=0)

try:
    sectors = sector_overview(selected_date)
except ApiError as exc:
    st.error(str(exc), icon=":material/error:")
    st.stop()

items = sectors["items"]

st.subheader("活跃板块")
strongest = items[:3]
strengthening = [item for item in items if item["rotation_state"] == "STRENGTHENING"][:3]
weakening = [item for item in items if item["rotation_state"] == "WEAKENING"][:3]
activity_cols = st.columns(3)
with activity_cols[0]:
    st.metric("5日强势行业", " / ".join(item["sector_name"] for item in strongest) or "无", border=True)
with activity_cols[1]:
    st.metric("排名强化", " / ".join(item["sector_name"] for item in strengthening) or "无", border=True)
with activity_cols[2]:
    st.metric("排名转弱", " / ".join(item["sector_name"] for item in weakening) or "无", border=True)

with st.expander("查看完整 31 行业数据", icon=":material/table_chart:"):
    sector_rows = [
        {
            "行业": item["sector_name"],
            "1日": item["return_1d"],
            "5日": item["return_5d"],
            "20日": item["return_20d"],
            "相对沪深300（5日）": item["relative_hs300_5d"],
            "相对沪深300（20日）": item["relative_hs300_20d"],
            "5日排名": item["rank_5d"],
            "20日排名": item["rank_20d"],
        }
        for item in items
    ]
    st.dataframe(
        pd.DataFrame(sector_rows),
        hide_index=True,
        column_config={
            "1日": st.column_config.NumberColumn(format="percent"),
            "5日": st.column_config.NumberColumn(format="percent"),
            "20日": st.column_config.NumberColumn(format="percent"),
            "相对沪深300（5日）": st.column_config.NumberColumn(format="percent"),
            "相对沪深300（20日）": st.column_config.NumberColumn(format="percent"),
        },
    )

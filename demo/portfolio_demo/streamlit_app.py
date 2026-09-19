"""Portfolio Demo entry — A股智能交易决策系统 V1.0（只读展示版）。

独立于研发研究后台（src/web_dashboard/）；只读调用正式 API，不修改任何策略/数据/研究结论。
"""

from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st

from portfolio_demo.api_client import ApiError, overview
from portfolio_demo.presentation import DISCLAIMER


st.set_page_config(
    page_title="A股智能交易决策系统 V1.0｜Portfolio Demo",
    page_icon=":material/query_stats:",
    layout="wide",
)

APP_DIR = Path(__file__).resolve().parent

page = st.navigation(
    {
        "": [
            st.Page(APP_DIR / "app_pages" / "home.py", title="首页", icon=":material/dashboard:", default=True),
            st.Page(APP_DIR / "app_pages" / "market.py", title="市场环境", icon=":material/public:", url_path="market"),
            st.Page(APP_DIR / "app_pages" / "sectors.py", title="板块环境", icon=":material/category:", url_path="sectors"),
            st.Page(APP_DIR / "app_pages" / "strategies.py", title="策略中心", icon=":material/hub:", url_path="strategies"),
            st.Page(APP_DIR / "app_pages" / "signals.py", title="今日信号", icon=":material/bolt:", url_path="signals"),
            st.Page(
                APP_DIR / "app_pages" / "stock_detail.py",
                title="个股详情",
                icon=":material/candlestick_chart:",
                url_path="stock",
                visibility="hidden",
            ),
        ],
    },
    position="top",
)

try:
    market_date = overview()["current_market_date"]
except ApiError:
    market_date = None

st.caption("A股智能交易决策系统 V1.0 · Portfolio Demo")

if market_date is None:
    st.warning("数据服务暂不可用，请稍后刷新重试。", icon=":material/error:")

if page.url_path:
    st.title(f"{page.icon} {page.title}")
page.run()

st.divider()
st.caption(DISCLAIMER)

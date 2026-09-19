"""Read-only API client for the Portfolio Demo.

独立于研发后台的 `src/web_dashboard/api_client.py`；只读调用正式 API，不修改任何字段或语义。
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request

import streamlit as st


__all__ = (
    "ApiError",
    "overview",
    "signals",
    "performance",
    "strategy1_regime_performance",
    "strategy1_portfolio_risk",
    "strategy2_landmark_research",
    "strategy2_landmark_evidence",
    "market_overview",
    "market_regime",
    "market_regime_history",
    "sector_overview",
    "sector_detail",
    "stock_detail",
    "stock_sector_context",
    "stocks",
)


API_BASE_URL = os.getenv("STRATEGY1_API_URL", "http://127.0.0.1:8000").rstrip("/")
API_TIMEOUT_SECONDS = 45


class ApiError(RuntimeError):
    pass


@st.cache_data(ttl="30m", max_entries=120, show_spinner=False)
def api_get(path: str, params: tuple[tuple[str, str], ...] = ()) -> dict:
    query = urllib.parse.urlencode(params)
    url = f"{API_BASE_URL}{path}" + (f"?{query}" if query else "")
    try:
        with urllib.request.urlopen(url, timeout=API_TIMEOUT_SECONDS) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        try:
            payload = json.loads(exc.read().decode("utf-8"))
            message = payload.get("error", str(exc))
        except (ValueError, UnicodeDecodeError):
            message = str(exc)
        raise ApiError(message) from exc
    except TimeoutError as exc:
        raise ApiError("数据服务响应超时，请稍后重试。") from exc
    except urllib.error.URLError as exc:
        if isinstance(exc.reason, TimeoutError):
            raise ApiError("数据服务响应超时，请稍后重试。") from exc
        raise ApiError("数据服务暂不可用，请稍后刷新重试。") from exc


def overview() -> dict:
    return api_get("/api/v1/overview")


def signals(date: str | None = None, limit: int = 1000) -> dict:
    params: tuple[tuple[str, str], ...] = (("limit", str(limit)),)
    if date:
        params += (("date", date),)
    return api_get("/api/v1/signals", params)


def performance() -> dict:
    return api_get("/api/v1/backtest/performance")


def strategy1_regime_performance() -> dict:
    return api_get("/api/v1/strategies/strategy1/regime-performance")


def strategy1_portfolio_risk() -> dict:
    return api_get("/api/v1/strategies/strategy1/portfolio-risk")


def strategy2_landmark_research() -> dict:
    return api_get("/api/v1/strategies/strategy2/landmark-research")


def strategy2_landmark_evidence() -> dict:
    return api_get("/api/v1/strategies/strategy2/landmark-evidence")


def market_overview(date: str | None = None) -> dict:
    params: tuple[tuple[str, str], ...] = ()
    if date:
        params = (("date", date),)
    return api_get("/api/v1/market/overview", params)


def market_regime(date: str | None = None) -> dict:
    params: tuple[tuple[str, str], ...] = ()
    if date:
        params = (("date", date),)
    return api_get("/api/v1/market/regime", params)


def market_regime_history(date: str | None = None, lookback: int = 120) -> dict:
    params: tuple[tuple[str, str], ...] = (("lookback", str(lookback)),)
    if date:
        params += (("date", date),)
    return api_get("/api/v1/market/regime/history", params)


def sector_overview(date: str | None = None) -> dict:
    params: tuple[tuple[str, str], ...] = ()
    if date:
        params = (("date", date),)
    return api_get("/api/v1/sectors/overview", params)


def sector_detail(sector_code: str, date: str | None = None, lookback: int = 120) -> dict:
    params: tuple[tuple[str, str], ...] = (("lookback", str(lookback)),)
    if date:
        params += (("date", date),)
    return api_get(f"/api/v1/sectors/{sector_code}", params)


def stock_detail(code: str, lookback: int = 120) -> dict:
    return api_get(f"/api/v1/stocks/{code.zfill(6)}", (("lookback", str(lookback)),))


def stocks(status: str = "COMMITTED", query: str | None = None, limit: int = 100) -> dict:
    params: tuple[tuple[str, str], ...] = (("status", status), ("limit", str(limit)))
    if query:
        params += (("q", query),)
    return api_get("/api/v1/stocks", params)


def stock_sector_context(code: str, date: str | None = None) -> dict:
    params: tuple[tuple[str, str], ...] = ()
    if date:
        params = (("date", date),)
    return api_get(f"/api/v1/stocks/{code.zfill(6)}/sector-context", params)

"""Starlette application exposing Strategy1 MVP product endpoints."""

from __future__ import annotations

from starlette.applications import Starlette
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from .repository import get_repository
from .market_repository import (
    market_breadth as cached_market_breadth,
    market_indices as cached_market_indices,
    market_overview as cached_market_overview,
    market_quality as cached_market_quality,
)
from .market_regime_repository import get_market_regime_service
from .sector_repository import get_sector_service
from .strategy_research_repository import (
    strategy1_portfolio_risk,
    strategy1_regime_performance,
    strategy2_landmark_evidence,
    strategy2_landmark_research,
)


def _error(message: str, status_code: int = 400) -> JSONResponse:
    return JSONResponse({"error": message}, status_code=status_code)


async def health(_: Request) -> JSONResponse:
    repository = get_repository()
    return JSONResponse({"status": "ok", "market_date": repository.market_date})


async def overview(_: Request) -> JSONResponse:
    return JSONResponse(get_repository().overview())


async def signals(request: Request) -> JSONResponse:
    try:
        offset = int(request.query_params.get("offset", "0"))
        limit = int(request.query_params.get("limit", "100"))
    except ValueError:
        return _error("offset and limit must be integers")
    if offset < 0 or not 1 <= limit <= 1000:
        return _error("offset must be >=0 and limit must be between 1 and 1000")
    date = request.query_params.get("date")
    return JSONResponse(get_repository().signal_page(date, offset, limit))


async def backtest_performance(_: Request) -> JSONResponse:
    return JSONResponse(get_repository().backtest_performance())


async def strategy1_regime_research(_: Request) -> JSONResponse:
    return _market_response(strategy1_regime_performance)


async def strategy1_portfolio_risk_research(_: Request) -> JSONResponse:
    return _market_response(strategy1_portfolio_risk)


async def strategy2_landmark_research_gate(_: Request) -> JSONResponse:
    return _market_response(strategy2_landmark_research)


async def strategy2_landmark_evidence_view(_: Request) -> JSONResponse:
    return _market_response(strategy2_landmark_evidence)


async def stocks(request: Request) -> JSONResponse:
    try:
        offset = int(request.query_params.get("offset", "0"))
        limit = int(request.query_params.get("limit", "100"))
    except ValueError:
        return _error("offset and limit must be integers")
    if offset < 0 or not 1 <= limit <= 500:
        return _error("offset must be >=0 and limit must be between 1 and 500")
    status = request.query_params.get("status", "COMMITTED").upper()
    if status not in {"ALL", "COMMITTED", "FAILED"}:
        return _error("status must be ALL, COMMITTED or FAILED")
    market = request.query_params.get("market")
    if market and market not in {"SH_MAIN", "STAR", "SZ_MAIN", "GEM", "BSE"}:
        return _error("unsupported market")
    query = request.query_params.get("q") or None
    return JSONResponse(get_repository().stock_page(status, market, query, offset, limit))


async def stock_detail(request: Request) -> JSONResponse:
    code = request.path_params["code"]
    if not code.isdigit() or len(code) > 6:
        return _error("code must contain at most 6 digits")
    try:
        lookback = int(request.query_params.get("lookback", "120"))
    except ValueError:
        return _error("lookback must be an integer")
    if not 1 <= lookback <= 500:
        return _error("lookback must be between 1 and 500")
    detail = get_repository().stock_detail(code, lookback)
    if detail is None:
        return _error(f"Stock code {code.zfill(6)} does not exist in stock_basic", 404)
    return JSONResponse(detail)


def _market_params(request: Request, default_lookback: int) -> tuple[str | None, int] | JSONResponse:
    date = request.query_params.get("date")
    if date is not None:
        try:
            from datetime import date as date_type
            date_type.fromisoformat(date)
        except ValueError:
            return _error("date must use YYYY-MM-DD")
    try:
        lookback = int(request.query_params.get("lookback", str(default_lookback)))
    except ValueError:
        return _error("lookback must be an integer")
    return date, lookback


def _market_response(function, *args) -> JSONResponse:
    try:
        return JSONResponse(function(*args))
    except ValueError as exc:
        return _error(str(exc))
    except LookupError as exc:
        return _error(str(exc), 404)


async def market_indices(request: Request) -> JSONResponse:
    params = _market_params(request, 60)
    if isinstance(params, JSONResponse):
        return params
    return _market_response(cached_market_indices, *params)


async def market_overview(request: Request) -> JSONResponse:
    date = request.query_params.get("date")
    if date:
        params = _market_params(request, 30)
        if isinstance(params, JSONResponse):
            return params
        date = params[0]
    return _market_response(cached_market_overview, date)


async def market_breadth(request: Request) -> JSONResponse:
    params = _market_params(request, 30)
    if isinstance(params, JSONResponse):
        return params
    return _market_response(cached_market_breadth, *params)


async def market_quality(request: Request) -> JSONResponse:
    date = request.query_params.get("date")
    if date:
        params = _market_params(request, 30)
        if isinstance(params, JSONResponse):
            return params
        date = params[0]
    return _market_response(cached_market_quality, date)


async def market_regime(request: Request) -> JSONResponse:
    date = request.query_params.get("date")
    if date:
        params = _market_params(request, 120)
        if isinstance(params, JSONResponse):
            return params
        date = params[0]
    return _market_response(get_market_regime_service().current, date)


async def market_regime_history(request: Request) -> JSONResponse:
    params = _market_params(request, 120)
    if isinstance(params, JSONResponse):
        return params
    date, lookback = params
    return _market_response(get_market_regime_service().history, date, lookback)


async def sector_overview(request: Request) -> JSONResponse:
    date = request.query_params.get("date")
    if date:
        params = _market_params(request, 80)
        if isinstance(params, JSONResponse):
            return params
        date = params[0]
    return _market_response(get_sector_service().overview, date)


async def sector_detail(request: Request) -> JSONResponse:
    sector_code = request.path_params["sector_code"]
    if not sector_code.isdigit() or len(sector_code) != 6:
        return _error("sector_code must contain exactly 6 digits")
    params = _market_params(request, 120)
    if isinstance(params, JSONResponse):
        return params
    date, lookback = params
    return _market_response(get_sector_service().detail, sector_code, date, lookback)


async def stock_sector_context(request: Request) -> JSONResponse:
    stock_code = request.path_params["stock_code"]
    if not stock_code.isdigit() or len(stock_code) > 6:
        return _error("stock_code must contain at most 6 digits")
    date = request.query_params.get("date")
    if date:
        params = _market_params(request, 80)
        if isinstance(params, JSONResponse):
            return params
        date = params[0]
    return _market_response(get_sector_service().stock_context, stock_code.zfill(6), date)


async def stock_sector_contexts(request: Request) -> JSONResponse:
    raw_codes = request.query_params.get("codes", "")
    codes = [code.strip().zfill(6) for code in raw_codes.split(",") if code.strip()]
    if not codes or len(codes) > 100 or any(not code.isdigit() or len(code) != 6 for code in codes):
        return _error("codes must contain between 1 and 100 comma-separated stock codes")
    date = request.query_params.get("date")
    if date:
        params = _market_params(request, 80)
        if isinstance(params, JSONResponse):
            return params
        date = params[0]
    return _market_response(get_sector_service().stock_contexts, codes, date)


routes = [
    Route("/health", health, methods=["GET"]),
    Route("/api/v1/overview", overview, methods=["GET"]),
    Route("/api/v1/signals", signals, methods=["GET"]),
    Route("/api/v1/backtest/performance", backtest_performance, methods=["GET"]),
    Route("/api/v1/strategies/strategy1/regime-performance", strategy1_regime_research, methods=["GET"]),
    Route("/api/v1/strategies/strategy1/portfolio-risk", strategy1_portfolio_risk_research, methods=["GET"]),
    Route("/api/v1/strategies/strategy2/landmark-research", strategy2_landmark_research_gate, methods=["GET"]),
    Route("/api/v1/strategies/strategy2/landmark-evidence", strategy2_landmark_evidence_view, methods=["GET"]),
    Route("/api/v1/stocks", stocks, methods=["GET"]),
    Route("/api/v1/stocks/{code}", stock_detail, methods=["GET"]),
    Route("/api/v1/market/indices", market_indices, methods=["GET"]),
    Route("/api/v1/market/overview", market_overview, methods=["GET"]),
    Route("/api/v1/market/breadth", market_breadth, methods=["GET"]),
    Route("/api/v1/market/quality", market_quality, methods=["GET"]),
    Route("/api/v1/market/regime", market_regime, methods=["GET"]),
    Route("/api/v1/market/regime/history", market_regime_history, methods=["GET"]),
    Route("/api/v1/sectors/overview", sector_overview, methods=["GET"]),
    Route("/api/v1/sectors/stock-contexts", stock_sector_contexts, methods=["GET"]),
    Route("/api/v1/sectors/{sector_code}", sector_detail, methods=["GET"]),
    Route("/api/v1/stocks/{stock_code}/sector-context", stock_sector_context, methods=["GET"]),
]

app = Starlette(debug=False, routes=routes)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1", "http://localhost"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

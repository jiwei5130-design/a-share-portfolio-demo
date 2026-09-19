"""Thread-safe access to the read-only Market Regime Engine."""

from functools import lru_cache

from src.market_regime import MarketRegimeService

from .market_repository import get_market_service, market_overview


class _CachedMarketService:
    """Reuse the Web API's date-aware P4 cache without changing P4 itself."""

    def __init__(self) -> None:
        self.repository = get_market_service().repository

    def overview(self, date: str | None = None) -> dict[str, object]:
        return market_overview(date)


@lru_cache(maxsize=1)
def get_market_regime_service() -> MarketRegimeService:
    return MarketRegimeService(market_service=_CachedMarketService())

"""Compose truthful P4 market overview responses."""

from __future__ import annotations

from src.market_intelligence.config import CALCULATION_VERSION, DEFAULT_LOOKBACK, MAX_LOOKBACK, UNIVERSE_SCOPE, UNIVERSE_STATUS
from src.market_intelligence.indicators.breadth import calculate_breadth
from src.market_intelligence.indicators.index_trend import calculate_index_indicators
from src.market_intelligence.repositories.market_repository import MarketIntelligenceRepository


class MarketOverviewService:
    def __init__(self, repository: MarketIntelligenceRepository | None = None) -> None:
        self.repository = repository or MarketIntelligenceRepository()

    @staticmethod
    def validate_lookback(lookback: int) -> int:
        if not 1 <= lookback <= MAX_LOOKBACK:
            raise ValueError(f"lookback must be between 1 and {MAX_LOOKBACK}")
        return lookback

    def indices(self, date: str | None = None, lookback: int = DEFAULT_LOOKBACK) -> dict[str, object]:
        lookback = self.validate_lookback(lookback)
        as_of = self.repository.resolve_date(date)
        frame = self.repository.index_history(as_of, max(61, lookback + 20))
        items = calculate_index_indicators(frame, lookback)
        return {"as_of_date": as_of, "calculation_version": CALCULATION_VERSION,
                "data_status": "COMPLETE_7_OF_7" if len(items) == 7 else "INCOMPLETE_INDEX_COVERAGE",
                "items": items, "quality": self.repository.index_summary()}

    @staticmethod
    def unavailable() -> list[dict[str, str]]:
        return [
            {"indicator": "LIMIT_UP_DOWN", "reason": "historical stock status and point-in-time price-limit rules unavailable"},
            {"indicator": "SECTOR_ANALYSIS", "reason": "provided independently by P6 Sector Intelligence; not part of P4 calculations"},
            {"indicator": "MARKET_REGIME", "reason": "not implemented in P4 MVP"},
            {"indicator": "INDEX_VOLUME_RATING", "reason": "index volume unit remains UNKNOWN"},
        ]

    def breadth(self, date: str | None = None, lookback: int = 30) -> dict[str, object]:
        lookback = self.validate_lookback(lookback)
        as_of = self.repository.resolve_date(date)
        series = calculate_breadth(self.repository.stock_window(as_of, max(90, lookback + 60)), lookback)
        coverage = self.repository.coverage(as_of)
        return {"as_of_date": as_of, "calculation_version": CALCULATION_VERSION, "scope": UNIVERSE_SCOPE,
                "universe_status": UNIVERSE_STATUS, "coverage": coverage, "series": series,
                "warning": "仅基于已加载RAW行情证券计算，不代表A股全市场。缺失行情不计为停牌或下跌。"}

    def quality(self, date: str | None = None) -> dict[str, object]:
        as_of = self.repository.resolve_date(date)
        return {"as_of_date": as_of, "calculation_version": CALCULATION_VERSION, "scope": UNIVERSE_SCOPE,
                "universe_status": UNIVERSE_STATUS, "coverage": self.repository.coverage(as_of),
                "database": self.repository.database_quality(), "unavailable": self.unavailable()}

    def overview(self, date: str | None = None) -> dict[str, object]:
        indices = self.indices(date, 60)
        breadth = self.breadth(indices["as_of_date"], 30)
        latest = breadth["series"][-1]
        observations = []
        if latest["advances"] > latest["declines"]:
            observations.append(f"已加载样本中上涨 {latest['advances']} 家，多于下跌 {latest['declines']} 家。")
        elif latest["declines"] > latest["advances"]:
            observations.append(f"已加载样本中下跌 {latest['declines']} 家，多于上涨 {latest['advances']} 家。")
        else:
            observations.append("已加载样本上涨与下跌家数相同。")
        ma20 = latest["ma_breadth"]["ma20"]
        if ma20["above_ratio"] is not None:
            observations.append(f"可计算样本中 {ma20['above_ratio']:.1%} 站上 MA20（分母 {ma20['eligible_count']}）。")
        volume = latest["volume_change_1d"]
        observations.append("样本总成交量较前一交易日无法比较。" if volume is None else f"样本总成交量较前一交易日变化 {volume:+.1%}。")
        return {"as_of_date": indices["as_of_date"], "calculation_version": CALCULATION_VERSION,
                "scope": UNIVERSE_SCOPE, "universe_status": UNIVERSE_STATUS,
                "indices": indices, "breadth": {"latest": latest, "history": breadth["series"]},
                "coverage": breadth["coverage"], "observations": observations[:3],
                "unavailable": self.unavailable(),
                "disclaimer": "历史收盘事实观察；不是Market Regime评分、预测或策略推荐。"}

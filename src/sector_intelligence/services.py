"""Compose truthful P6 sector responses without changing strategy results."""

from __future__ import annotations

from .config import BENCHMARK_NAME, CALCULATION_VERSION, MAX_LOOKBACK, RANK_CHANGE_THRESHOLD
from .indicators import calculate_sector_indicators, context_label
from .repositories import SectorRepository


class SectorIntelligenceService:
    def __init__(self, repository: SectorRepository | None = None) -> None:
        self.repository = repository or SectorRepository()

    def overview(self, date: str | None = None) -> dict[str, object]:
        as_of = self.repository.resolve_date(date)
        items = calculate_sector_indicators(
            self.repository.history(as_of, 80), self.repository.benchmark_history(as_of, 80)
        )
        items.sort(key=lambda item: item["rank_5d"] if item["rank_5d"] is not None else 10_000)
        quality = self.repository.quality(as_of)
        return {
            "as_of_date": as_of,
            "calculation_version": CALCULATION_VERSION,
            "sector_system": "SW",
            "sector_level": 1,
            "benchmark": BENCHMARK_NAME,
            "source": quality["source"],
            "quality_status": quality["quality_status"],
            "coverage": quality,
            "classification_version": quality["classification_version"],
            "membership_basis": quality["membership_basis"],
            "rotation_rule": f"5日排名相对20日排名改善≥{RANK_CHANGE_THRESHOLD}名为强化，恶化≥{RANK_CHANGE_THRESHOLD}名为转弱，其余为稳定。",
            "strategy_effect": "CONTEXT_ONLY_DOES_NOT_CHANGE_STRATEGY1",
            "items": items,
        }

    def detail(self, sector_code: str, date: str | None = None, lookback: int = 120) -> dict[str, object]:
        if not 1 <= lookback <= MAX_LOOKBACK:
            raise ValueError(f"lookback must be between 1 and {MAX_LOOKBACK}")
        if not self.repository.sector_exists(sector_code):
            raise LookupError("SECTOR_NOT_FOUND")
        payload = self.overview(date)
        item = next(entry for entry in payload["items"] if entry["sector_code"] == sector_code)
        item = {**item, "history": item["history"][-lookback:]}
        return {key: value for key, value in payload.items() if key != "items"} | {"item": item}

    def stock_context(self, stock_code: str, date: str | None = None) -> dict[str, object]:
        as_of = self.repository.resolve_date(date)
        memberships = self.repository.stock_membership(stock_code)
        if len(memberships) != 1:
            return {
                "stock_code": stock_code,
                "as_of_date": as_of,
                "status": "NOT_AVAILABLE",
                "quality_status": "NOT_AVAILABLE",
                "membership_basis": "NOT_AVAILABLE_UNIQUE_POINT_IN_TIME_CLASSIFICATION",
                "classification_version": "SW_CURRENT_LEVEL1_VERSION_UNSPECIFIED",
                "source": "SHENWAN_OFFICIAL_VIA_AKSHARE",
                "reason": "申万成分接口无法提供唯一、可验证的时点行业归属；未写入sector_membership，不进行猜测或历史归因。",
                "strategy_effect": "NONE",
                "sector": None,
            }
        membership = memberships[0]
        payload = self.overview(as_of)
        sector = next(
            (item for item in payload["items"] if item["sector_code"] == membership["sector_code"]), None
        )
        return {
            "stock_code": stock_code,
            "as_of_date": as_of,
            "status": "AVAILABLE" if sector else "NOT_AVAILABLE",
            "quality_status": membership["quality_status"],
            "membership_basis": membership["membership_basis"],
            "classification_version": membership["classification_version"],
            "source": membership["source"],
            "reason": None if sector else "NO_SECTOR_DAILY_CONTEXT",
            "strategy_effect": "CONTEXT_ONLY_DOES_NOT_CHANGE_STRATEGY1",
            "sector": None if sector is None else {**sector, "context_label": context_label(sector)},
        }

    def stock_contexts(self, stock_codes: list[str], date: str | None = None) -> dict[str, object]:
        return {
            "as_of_date": self.repository.resolve_date(date),
            "strategy_effect": "CONTEXT_ONLY_DOES_NOT_CHANGE_STRATEGY1",
            "items": [self.stock_context(code, date) for code in stock_codes],
        }

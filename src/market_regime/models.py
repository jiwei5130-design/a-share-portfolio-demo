"""Typed inputs for Market Regime calculations."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class MarketRegimeInputs:
    as_of_date: str
    source_dates: tuple[str, ...]
    index_above_ratios: dict[int, float | None]
    index_valid_counts: dict[int, int]
    breadth_above_ratios: dict[int, float | None]
    breadth_eligible_counts: dict[int, int]
    traded_count: int
    universe_status: str
    coverage: dict[str, Any]


@dataclass(frozen=True)
class RegimeCalculation:
    state: str
    state_label: str
    regime_score: float | None
    index_score: float | None
    breadth_score: float | None
    evidence: tuple[dict[str, Any], ...]
    quality_checks: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        return {
            "state": self.state,
            "state_label": self.state_label,
            "regime_score": self.regime_score,
            "components": {
                "index_score": self.index_score,
                "breadth_score": self.breadth_score,
            },
            "evidence": list(self.evidence),
            "quality_checks": self.quality_checks,
        }

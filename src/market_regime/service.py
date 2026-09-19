"""Compose P4 and P6 facts into an independent Market Regime context."""

from __future__ import annotations

from functools import lru_cache
import math
from typing import Any

import pandas as pd

from src.market_intelligence.config import UNIVERSE_STATUS
from src.market_intelligence.indicators.index_trend import calculate_index_indicators
from src.market_intelligence.services.market_overview_service import MarketOverviewService
from src.sector_intelligence.services import SectorIntelligenceService

from .calculator import calculate_regime, volume_context
from .config import (
    CALCULATION_VERSION,
    DEFAULT_HISTORY_LOOKBACK,
    DISCLAIMER,
    MA_WINDOWS,
    MAX_HISTORY_LOOKBACK,
    STRATEGY_EFFECT,
)
from .models import MarketRegimeInputs


class MarketRegimeService:
    def __init__(
        self,
        market_service: MarketOverviewService | None = None,
        sector_service: SectorIntelligenceService | None = None,
    ) -> None:
        self.market_service = market_service or MarketOverviewService()
        self.sector_service = sector_service or SectorIntelligenceService()

    @staticmethod
    def _point_in_time_breadth_history(frame: pd.DataFrame, lookback: int) -> list[dict[str, Any]]:
        """Reproduce P4's latest-date breadth for each date using a fixed 90-date window.

        Calculations run chronologically. Rolling values and comparisons only use
        the current row and earlier rows; later rows in the requested range never
        enter an earlier date's calculation.
        """
        data = frame.sort_values(["code", "exchange", "date"]).copy()
        dates = sorted(str(value) for value in data["date"].unique())
        if not dates:
            return []
        date_rank = {date: index for index, date in enumerate(dates)}
        data["date"] = data["date"].astype(str)
        data["date_rank"] = data["date"].map(date_rank)
        grouped = data.groupby(["code", "exchange"], sort=False)
        data["prior_close"] = grouped["close"].shift(1)
        data["prior_rank"] = grouped["date_rank"].shift(1)
        data["cutoff_rank"] = (data["date_rank"] - 89).clip(lower=0)
        for window in MA_WINDOWS:
            data[f"ma{window}"] = grouped["close"].transform(
                lambda values, size=window: values.rolling(size, min_periods=size).mean()
            )
            data[f"oldest_rank_ma{window}"] = grouped["date_rank"].shift(window - 1)

        rows: list[dict[str, Any]] = []
        for date, day in data.groupby("date", sort=True):
            comparable = day[
                day["prior_close"].notna() & (day["prior_rank"] >= day["cutoff_rank"])
            ]
            ma: dict[str, dict[str, Any]] = {}
            for window in MA_WINDOWS:
                eligible = day[
                    day[f"ma{window}"].notna()
                    & (day[f"oldest_rank_ma{window}"] >= day["cutoff_rank"])
                ]
                above = int((eligible["close"] > eligible[f"ma{window}"]).sum())
                ma[f"ma{window}"] = {
                    "above_count": above,
                    "eligible_count": int(len(eligible)),
                    "above_ratio": above / len(eligible) if len(eligible) else None,
                }
            volume_sum = day["volume"].sum(min_count=1)
            volume = None if pd.isna(volume_sum) or not math.isfinite(float(volume_sum)) else float(volume_sum)
            rows.append({
                "date": str(date),
                "traded_count": int(len(day)),
                "comparable_count": int(len(comparable)),
                "advances": int((comparable["close"] > comparable["prior_close"]).sum()),
                "declines": int((comparable["close"] < comparable["prior_close"]).sum()),
                "unchanged": int((comparable["close"] == comparable["prior_close"]).sum()),
                "ma_breadth": ma,
                "volume": volume,
            })
        for position, row in enumerate(rows):
            prior_volume = rows[position - 1]["volume"] if position else None
            row["volume_change_1d"] = (
                None if prior_volume in (None, 0) or row["volume"] is None
                else row["volume"] / prior_volume - 1
            )
            for window in (5, 20):
                prior = [
                    item["volume"] for item in rows[max(0, position - window):position]
                    if item["volume"] is not None
                ]
                average = sum(prior) / len(prior) if len(prior) == window else None
                row[f"volume_vs_{window}d_avg"] = (
                    None if average in (None, 0) or row["volume"] is None
                    else row["volume"] / average - 1
                )
        return rows[-lookback:]

    @staticmethod
    def _inputs(
        as_of_date: str,
        index_items: list[dict[str, Any]],
        breadth: dict[str, Any],
        coverage: dict[str, Any],
        universe_status: str,
    ) -> MarketRegimeInputs:
        index_ratios: dict[int, float | None] = {}
        index_counts: dict[int, int] = {}
        breadth_ratios: dict[int, float | None] = {}
        breadth_counts: dict[int, int] = {}
        source_dates = [str(breadth.get("date"))]
        source_dates.extend(str(item.get("date")) for item in index_items)
        for window in MA_WINDOWS:
            values = [item.get(f"above_ma{window}") for item in index_items]
            valid = [value for value in values if value is not None]
            index_counts[window] = len(valid)
            index_ratios[window] = (
                sum(value is True for value in valid) / len(valid) if valid else None
            )
            metric = breadth.get("ma_breadth", {}).get(f"ma{window}", {})
            breadth_ratios[window] = metric.get("above_ratio")
            breadth_counts[window] = int(metric.get("eligible_count") or 0)
        return MarketRegimeInputs(
            as_of_date=as_of_date,
            source_dates=tuple(source_dates),
            index_above_ratios=index_ratios,
            index_valid_counts=index_counts,
            breadth_above_ratios=breadth_ratios,
            breadth_eligible_counts=breadth_counts,
            traded_count=int(breadth.get("traded_count") or 0),
            universe_status=universe_status,
            coverage=coverage,
        )

    @staticmethod
    def _sector_context(payload: dict[str, Any] | None, as_of_date: str) -> dict[str, Any]:
        if not payload or payload.get("as_of_date") != as_of_date or not payload.get("items"):
            return {"status": "UNKNOWN", "score_effect": "NONE", "reason": "SECTOR_DATA_NOT_AVAILABLE_FOR_DATE"}
        items = payload["items"]
        rotation = {
            key: sum(item.get("rotation_state") == key for item in items)
            for key in ("STRENGTHENING", "STABLE", "WEAKENING", "UNKNOWN")
        }
        trends = {
            key: sum(item.get("trend_state") == key for item in items)
            for key in ("ABOVE_MA5_MA20", "NEUTRAL", "BELOW_MA5_MA20", "UNKNOWN")
        }
        relative = {
            "outperform_hs300_5d": sum(
                item.get("relative_hs300_5d") is not None and item["relative_hs300_5d"] > 0
                for item in items
            ),
            "outperform_hs300_20d": sum(
                item.get("relative_hs300_20d") is not None and item["relative_hs300_20d"] > 0
                for item in items
            ),
        }
        return {
            "status": "AVAILABLE",
            "as_of_date": payload["as_of_date"],
            "sector_count": len(items),
            "rotation_counts": rotation,
            "trend_counts": trends,
            "relative_strength_counts": relative,
            "source": payload.get("source"),
            "quality_status": payload.get("quality_status"),
            "score_effect": "NONE",
        }

    @staticmethod
    def _summary(calculation: dict[str, Any], volume: dict[str, Any]) -> str:
        if calculation["state"] == "INSUFFICIENT_DATA":
            return "关键市场指标未通过数据质量门禁，当前无法形成市场环境分类。"
        index_score = calculation["components"]["index_score"]
        breadth_score = calculation["components"]["breadth_score"]
        index_text = "指数趋势偏强" if index_score >= 20 else "指数趋势偏弱" if index_score < -20 else "指数趋势接近中性"
        breadth_text = "市场宽度偏强" if breadth_score >= 20 else "市场宽度偏弱" if breadth_score < -20 else "市场宽度接近中性"
        return f"{index_text}，{breadth_text}，近期成交量{volume['status_label']}。"

    @lru_cache(maxsize=512)
    def current(self, date: str | None = None) -> dict[str, Any]:
        market = self.market_service.overview(date)
        as_of = str(market["as_of_date"])
        inputs = self._inputs(
            as_of,
            market["indices"]["items"],
            market["breadth"]["latest"],
            market["coverage"],
            str(market["universe_status"]),
        )
        calculation = calculate_regime(inputs).as_dict()
        volume = volume_context(
            market["breadth"]["latest"].get("volume_change_1d"),
            market["breadth"]["latest"].get("volume_vs_5d_avg"),
            market["breadth"]["latest"].get("volume_vs_20d_avg"),
        )
        try:
            sector_payload = self.sector_service.overview(as_of)
        except (LookupError, ValueError):
            sector_payload = None
        return {
            "as_of_date": as_of,
            "calculation_version": CALCULATION_VERSION,
            **calculation,
            "universe_status": inputs.universe_status,
            "coverage": inputs.coverage,
            "volume_context": volume,
            "sector_context": self._sector_context(sector_payload, as_of),
            "summary": self._summary(calculation, volume),
            "strategy_effect": STRATEGY_EFFECT,
            "disclaimer": DISCLAIMER,
        }

    @lru_cache(maxsize=32)
    def history(
        self, date: str | None = None, lookback: int = DEFAULT_HISTORY_LOOKBACK
    ) -> dict[str, Any]:
        if not 1 <= lookback <= MAX_HISTORY_LOOKBACK:
            raise ValueError(f"lookback must be between 1 and {MAX_HISTORY_LOOKBACK}")
        as_of = self.market_service.repository.resolve_date(date)
        stock_frame = self.market_service.repository.stock_window(as_of, lookback + 89)
        breadth_rows = self._point_in_time_breadth_history(stock_frame, lookback)
        if not breadth_rows:
            raise LookupError("NO_MARKET_BREADTH_HISTORY")
        index_frame = self.market_service.repository.index_history(as_of, lookback + 60)
        coverage = self.market_service.repository.coverage(as_of)
        items: list[dict[str, Any]] = []
        for breadth in breadth_rows:
            item_date = str(breadth["date"])
            point_in_time = index_frame[index_frame["date"] <= item_date]
            index_items = calculate_index_indicators(point_in_time, 1) if not point_in_time.empty else []
            inputs = self._inputs(
                item_date,
                index_items,
                breadth,
                coverage,
                UNIVERSE_STATUS,
            )
            calculation = calculate_regime(inputs).as_dict()
            volume = volume_context(
                breadth.get("volume_change_1d"),
                breadth.get("volume_vs_5d_avg"),
                breadth.get("volume_vs_20d_avg"),
            )
            items.append({
                "date": item_date,
                "state": calculation["state"],
                "state_label": calculation["state_label"],
                "regime_score": calculation["regime_score"],
                "index_score": calculation["components"]["index_score"],
                "breadth_score": calculation["components"]["breadth_score"],
                "volume_status": volume["status"],
            })
        return {
            "as_of_date": as_of,
            "calculation_version": CALCULATION_VERSION,
            "lookback": lookback,
            "universe_status": UNIVERSE_STATUS,
            "strategy_effect": STRATEGY_EFFECT,
            "items": items,
            "disclaimer": DISCLAIMER,
        }

"""Pure, reproducible Market Regime V1.0 calculations."""

from __future__ import annotations

import math
from typing import Any

from .config import (
    BREADTH_WEIGHT,
    INDEX_WEIGHT,
    MA_WINDOWS,
    MIN_BREADTH_ELIGIBLE_RATIO,
    MIN_VALID_CORE_INDICES,
    STATE_LABELS,
)
from .models import MarketRegimeInputs, RegimeCalculation


def _finite(value: float | None) -> bool:
    return value is not None and math.isfinite(float(value))


def balance(proportion: float) -> float:
    """Map a proportion in [0, 1] linearly to [-1, 1]."""
    if not _finite(proportion) or not 0.0 <= float(proportion) <= 1.0:
        raise ValueError("proportion must be a finite number between 0 and 1")
    return 2.0 * float(proportion) - 1.0


def classify_score(score: float) -> str:
    """Apply the frozen V1.0 state boundaries exactly."""
    if score >= 60.0:
        return "STRONG"
    if score >= 20.0:
        return "MODERATELY_STRONG"
    if score >= -20.0:
        return "RANGE_BOUND"
    if score >= -60.0:
        return "MODERATELY_WEAK"
    return "WEAK"


def volume_context(
    volume_change_1d: float | None,
    volume_vs_5d_avg: float | None,
    volume_vs_20d_avg: float | None,
) -> dict[str, Any]:
    """Describe volume facts without changing the market-state score."""
    if not _finite(volume_vs_5d_avg) or not _finite(volume_vs_20d_avg):
        status = "UNKNOWN"
        label = "数据不足"
    elif float(volume_vs_5d_avg) > 0 and float(volume_vs_20d_avg) > 0:
        status = "ABOVE_RECENT_AVERAGE"
        label = "高于5日及20日均量"
    elif float(volume_vs_5d_avg) < 0 and float(volume_vs_20d_avg) < 0:
        status = "BELOW_RECENT_AVERAGE"
        label = "低于5日及20日均量"
    else:
        status = "MIXED"
        label = "5日与20日均量比较方向不一致"
    return {
        "status": status,
        "status_label": label,
        "volume_change_1d": float(volume_change_1d) if _finite(volume_change_1d) else None,
        "volume_vs_5d_avg": float(volume_vs_5d_avg) if _finite(volume_vs_5d_avg) else None,
        "volume_vs_20d_avg": float(volume_vs_20d_avg) if _finite(volume_vs_20d_avg) else None,
        "score_effect": "NONE",
    }


def calculate_regime(inputs: MarketRegimeInputs) -> RegimeCalculation:
    """Calculate the primary state from six equal indicators with hard quality gates."""
    checks: dict[str, Any] = {
        "input_dates_match": bool(inputs.source_dates)
        and all(date == inputs.as_of_date for date in inputs.source_dates),
        "minimum_valid_indices": {},
        "breadth_eligible_ratio": {},
        "all_six_indicators_available": True,
    }
    evidence: list[dict[str, Any]] = []
    index_balances: list[float] = []
    breadth_balances: list[float] = []

    for window in MA_WINDOWS:
        index_ratio = inputs.index_above_ratios.get(window)
        valid_count = int(inputs.index_valid_counts.get(window, 0))
        index_ok = valid_count >= MIN_VALID_CORE_INDICES and _finite(index_ratio)
        checks["minimum_valid_indices"][f"ma{window}"] = {
            "valid_count": valid_count,
            "required": MIN_VALID_CORE_INDICES,
            "passed": index_ok,
        }
        if index_ok:
            index_balance = balance(float(index_ratio))
            index_balances.append(index_balance)
        else:
            index_balance = None
            checks["all_six_indicators_available"] = False

        breadth_ratio = inputs.breadth_above_ratios.get(window)
        eligible_count = int(inputs.breadth_eligible_counts.get(window, 0))
        eligible_ratio = eligible_count / inputs.traded_count if inputs.traded_count > 0 else None
        breadth_ok = (
            _finite(breadth_ratio)
            and eligible_ratio is not None
            and eligible_ratio >= MIN_BREADTH_ELIGIBLE_RATIO
        )
        checks["breadth_eligible_ratio"][f"ma{window}"] = {
            "eligible_count": eligible_count,
            "traded_count": inputs.traded_count,
            "ratio": eligible_ratio,
            "required": MIN_BREADTH_ELIGIBLE_RATIO,
            "passed": breadth_ok,
        }
        if breadth_ok:
            breadth_balance = balance(float(breadth_ratio))
            breadth_balances.append(breadth_balance)
        else:
            breadth_balance = None
            checks["all_six_indicators_available"] = False

        evidence.append({
            "window": f"MA{window}",
            "index_above_ratio": float(index_ratio) if _finite(index_ratio) else None,
            "index_valid_count": valid_count,
            "index_balance": index_balance,
            "breadth_above_ratio": float(breadth_ratio) if _finite(breadth_ratio) else None,
            "breadth_eligible_count": eligible_count,
            "breadth_balance": breadth_balance,
        })

    passed = (
        checks["input_dates_match"]
        and checks["all_six_indicators_available"]
        and len(index_balances) == len(MA_WINDOWS)
        and len(breadth_balances) == len(MA_WINDOWS)
    )
    checks["passed"] = passed
    if not passed:
        return RegimeCalculation(
            state="INSUFFICIENT_DATA",
            state_label=STATE_LABELS["INSUFFICIENT_DATA"],
            regime_score=None,
            index_score=None,
            breadth_score=None,
            evidence=tuple(evidence),
            quality_checks=checks,
        )

    index_score = sum(index_balances) / len(index_balances) * 100.0
    breadth_score = sum(breadth_balances) / len(breadth_balances) * 100.0
    regime_score = INDEX_WEIGHT * index_score + BREADTH_WEIGHT * breadth_score
    state = classify_score(regime_score)
    return RegimeCalculation(
        state=state,
        state_label=STATE_LABELS[state],
        regime_score=regime_score,
        index_score=index_score,
        breadth_score=breadth_score,
        evidence=tuple(evidence),
        quality_checks=checks,
    )

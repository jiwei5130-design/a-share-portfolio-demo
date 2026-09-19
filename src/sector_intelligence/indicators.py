"""Reproducible P6 sector indicators and rankings."""

from __future__ import annotations

import math

import pandas as pd

from .config import RANK_CHANGE_THRESHOLD


def _optional(value):
    return None if pd.isna(value) else float(value)


def calculate_sector_indicators(
    sector_history: pd.DataFrame, benchmark_history: pd.DataFrame
) -> list[dict[str, object]]:
    benchmark = benchmark_history.copy()
    benchmark["benchmark_return_5d"] = benchmark["close"].pct_change(5, fill_method=None)
    benchmark["benchmark_return_20d"] = benchmark["close"].pct_change(20, fill_method=None)
    benchmark_latest = benchmark.iloc[-1]
    results: list[dict[str, object]] = []
    histories: dict[str, list[dict[str, object]]] = {}

    for code, group in sector_history.groupby("sector_code", sort=True):
        group = group.sort_values("date").copy()
        group["return_1d"] = group["close"].pct_change(1, fill_method=None)
        group["return_5d"] = group["close"].pct_change(5, fill_method=None)
        group["return_20d"] = group["close"].pct_change(20, fill_method=None)
        group["ma5"] = group["close"].rolling(5, min_periods=5).mean()
        group["ma20"] = group["close"].rolling(20, min_periods=20).mean()
        latest = group.iloc[-1]
        ma5 = _optional(latest["ma5"])
        ma20 = _optional(latest["ma20"])
        close = float(latest["close"])
        if ma5 is None or ma20 is None:
            trend = "UNKNOWN"
        elif close > ma5 and close > ma20 and ma5 >= ma20:
            trend = "ABOVE_MA5_MA20"
        elif close < ma5 and close < ma20 and ma5 <= ma20:
            trend = "BELOW_MA5_MA20"
        else:
            trend = "NEUTRAL"
        return_5d = _optional(latest["return_5d"])
        return_20d = _optional(latest["return_20d"])
        result = {
            "sector_code": str(code),
            "sector_name": str(latest["sector_name"]),
            "date": str(latest["date"]),
            "close": close,
            "return_1d": _optional(latest["return_1d"]),
            "return_5d": return_5d,
            "return_20d": return_20d,
            "ma5": ma5,
            "ma20": ma20,
            "close_vs_ma5": None if ma5 is None else close / ma5 - 1,
            "close_vs_ma20": None if ma20 is None else close / ma20 - 1,
            "trend_state": trend,
            "relative_hs300_5d": None if return_5d is None or pd.isna(benchmark_latest["benchmark_return_5d"]) else return_5d - float(benchmark_latest["benchmark_return_5d"]),
            "relative_hs300_20d": None if return_20d is None or pd.isna(benchmark_latest["benchmark_return_20d"]) else return_20d - float(benchmark_latest["benchmark_return_20d"]),
            "volume": _optional(latest["volume"]),
            "amount": _optional(latest["amount"]),
            "volume_unit": str(latest["volume_unit"]),
            "amount_unit": str(latest["amount_unit"]),
            "source": str(latest["source"]),
            "quality_status": str(latest["quality_status"]),
            "classification_version": str(latest["classification_version"]),
            "classification_basis": str(latest["classification_basis"]),
        }
        results.append(result)
        histories[str(code)] = [
            {"date": str(row.date), "close": float(row.close)}
            for row in group.itertuples()
        ]

    ranking_frame = pd.DataFrame(results)
    for column, output in (("return_1d", "rank_1d"), ("return_5d", "rank_5d"), ("return_20d", "rank_20d")):
        ranking_frame[output] = ranking_frame[column].rank(method="min", ascending=False).astype("Int64")
    by_code = ranking_frame.set_index("sector_code").to_dict("index")
    count = len(ranking_frame)
    for result in results:
        ranks = by_code[result["sector_code"]]
        for rank_name in ("rank_1d", "rank_5d", "rank_20d"):
            rank = ranks[rank_name]
            result[rank_name] = None if pd.isna(rank) else int(rank)
        if result["rank_5d"] is None or result["rank_20d"] is None:
            result["rank_change_5d_vs_20d"] = None
            result["rank_direction"] = "UNKNOWN"
            result["rotation_state"] = "UNKNOWN"
        else:
            improvement = result["rank_20d"] - result["rank_5d"]
            result["rank_change_5d_vs_20d"] = improvement
            if improvement >= RANK_CHANGE_THRESHOLD:
                result["rank_direction"] = "IMPROVING"
                result["rotation_state"] = "STRENGTHENING"
            elif improvement <= -RANK_CHANGE_THRESHOLD:
                result["rank_direction"] = "DETERIORATING"
                result["rotation_state"] = "WEAKENING"
            else:
                result["rank_direction"] = "STABLE"
                result["rotation_state"] = "STABLE"
        result["strength_rank"] = result["rank_5d"]
        result["sector_count"] = count
        result["history"] = histories[result["sector_code"]]
    return results


def context_label(item: dict[str, object]) -> str:
    rank = item.get("rank_5d")
    count = int(item.get("sector_count") or 0)
    trend = item.get("trend_state")
    if rank is None or not count or trend == "UNKNOWN":
        return "数据不足"
    if int(rank) <= math.ceil(count / 3) and trend == "ABOVE_MA5_MA20":
        return "板块共振"
    if int(rank) > math.ceil(count * 2 / 3) or trend == "BELOW_MA5_MA20":
        return "板块偏弱"
    return "行业趋势中性"

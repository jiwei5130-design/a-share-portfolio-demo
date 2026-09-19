"""Partial-universe breadth and aggregate stock volume calculations."""

from __future__ import annotations

import math
import pandas as pd


def _finite(value):
    return None if value is None or pd.isna(value) or not math.isfinite(float(value)) else float(value)


def calculate_breadth(frame: pd.DataFrame, lookback: int) -> list[dict[str, object]]:
    data = frame.sort_values(["code", "exchange", "date"]).copy()
    grouped = data.groupby(["code", "exchange"], sort=False)
    data["prior_close"] = grouped["close"].shift(1)
    for window in (5, 20, 60):
        data[f"ma{window}"] = grouped["close"].transform(lambda values: values.rolling(window, min_periods=window).mean())

    rows = []
    for date, day in data.groupby("date", sort=True):
        comparable = day[day["prior_close"].notna()]
        advances = int((comparable["close"] > comparable["prior_close"]).sum())
        declines = int((comparable["close"] < comparable["prior_close"]).sum())
        unchanged = int((comparable["close"] == comparable["prior_close"]).sum())
        ma = {}
        for window in (5, 20, 60):
            eligible = day[day[f"ma{window}"].notna()]
            above = int((eligible["close"] > eligible[f"ma{window}"]).sum())
            ma[f"ma{window}"] = {"above_count": above, "eligible_count": len(eligible), "above_ratio": above / len(eligible) if len(eligible) else None}
        rows.append({
            "date": str(date), "traded_count": int(len(day)), "comparable_count": int(len(comparable)),
            "advances": advances, "declines": declines, "unchanged": unchanged,
            "advance_ratio": advances / len(comparable) if len(comparable) else None,
            "decline_ratio": declines / len(comparable) if len(comparable) else None,
            "advance_decline_ratio": advances / declines if declines else None,
            "ma_breadth": ma,
            "volume": _finite(day["volume"].sum(min_count=1)), "amount": _finite(day["amount"].sum(min_count=1)),
            "market_breakdown": [
                {"market": str(market), "traded_count": int(len(part)),
                 "advances": int((part["close"] > part["prior_close"]).sum()),
                 "declines": int((part["close"] < part["prior_close"]).sum())}
                for market, part in day.groupby("market", sort=True)
            ],
        })
    for position, row in enumerate(rows):
        row["volume_change_1d"] = None if position < 1 or not rows[position - 1]["volume"] else row["volume"] / rows[position - 1]["volume"] - 1
        for window in (5, 20):
            previous = [item["volume"] for item in rows[max(0, position-window):position] if item["volume"] is not None]
            average = sum(previous) / len(previous) if len(previous) == window else None
            row[f"volume_vs_{window}d_avg"] = None if average in (None, 0) else row["volume"] / average - 1
    return rows[-lookback:]

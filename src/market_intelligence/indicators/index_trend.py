"""Core index trend indicators without future data."""

from __future__ import annotations

import math
import pandas as pd


def _value(value):
    return None if value is None or pd.isna(value) or (isinstance(value, float) and not math.isfinite(value)) else float(value)


def calculate_index_indicators(frame: pd.DataFrame, lookback: int) -> list[dict[str, object]]:
    items = []
    for (_, _), group in frame.groupby(["index_code", "exchange"], sort=False):
        group = group.sort_values("date").copy()
        for window in (5, 20, 60):
            group[f"ma{window}"] = group["close"].rolling(window, min_periods=window).mean()
        latest = group.iloc[-1]
        close = float(latest["close"])
        returns = {period: _value(close / group.iloc[-period - 1]["close"] - 1) if len(group) > period else None for period in (1, 5, 20)}
        ma5, ma20, ma60 = (_value(latest[f"ma{window}"]) for window in (5, 20, 60))
        if ma20 is None:
            state = "INSUFFICIENT_HISTORY"
        elif ma60 is not None and close > ma5 > ma20 > ma60:
            state = "STRONG_UP"
        elif close > ma5 and close > ma20:
            state = "UP"
        elif close < ma5 and close < ma20:
            state = "DOWN"
        else:
            state = "MIXED"
        history = group.tail(lookback)
        items.append({
            "code": f"{latest['index_code']}.{'SH' if latest['exchange']=='SSE' else 'SZ'}",
            "index_code": str(latest["index_code"]), "exchange": str(latest["exchange"]), "name": str(latest["index_name"]),
            "date": str(latest["date"]), "close": close, "return_1d": returns[1], "return_5d": returns[5], "return_20d": returns[20],
            "ma5": ma5, "ma20": ma20, "ma60": ma60,
            "above_ma5": None if ma5 is None else close > ma5, "above_ma20": None if ma20 is None else close > ma20,
            "above_ma60": None if ma60 is None else close > ma60, "trend_state": state,
            "trend_evidence": {"close_above_ma5": None if ma5 is None else close > ma5, "close_above_ma20": None if ma20 is None else close > ma20, "ma5_above_ma20": None if ma5 is None or ma20 is None else ma5 > ma20},
            "source": str(latest["source"]), "volume": _value(latest.get("volume")), "volume_unit": "UNKNOWN",
            "history": [{"date": str(row.date), "close": float(row.close)} for row in history.itertuples()],
        })
    return sorted(items, key=lambda item: item["code"])

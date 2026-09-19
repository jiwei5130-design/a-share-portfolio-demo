"""Presentation helpers for the Portfolio Demo（只读展示层）。

成交额派生口径与研发后台 `turnover_metrics` 保持一致（同一 API `amount` 字段、同一算法），
但本模块为 Demo 独立实现，不依赖 `src/web_dashboard/`。
"""

from __future__ import annotations

DISCLAIMER = "研究与决策辅助｜不是荐股或自动交易系统｜不承诺收益｜不连接券商执行交易"
DATA_SCOPE_NOTE = "PARTIAL_UNIVERSE：市场宽度与成交额只覆盖已加载行情证券，不代表完整 A 股市场。"
SYNTHETIC_MARKER = "STATISTICAL SYNTHETIC CURVE — NOT PORTFOLIO RISK"
NOT_AVAILABLE = "NOT_AVAILABLE"
INSUFFICIENT = "数据不足"


def badge(text: str, color: str = "gray") -> str:
    return f":{color}-badge[{text}]"


def format_pct(value: float | None, digits: int = 2) -> str:
    return INSUFFICIENT if value is None else f"{value:.{digits}%}"


def format_number(value: float | None, digits: int = 0) -> str:
    return INSUFFICIENT if value is None else f"{value:,.{digits}f}"


def format_price(value: float | None) -> str:
    return INSUFFICIENT if value is None else f"{value:.3f}"


def format_turnover_cny(value: float | None) -> str:
    """Format market turnover whose validated database unit is CNY."""
    if value is None:
        return INSUFFICIENT
    if abs(value) >= 1_000_000_000_000:
        return f"{value / 1_000_000_000_000:,.2f} 万亿元"
    return f"{value / 100_000_000:,.2f} 亿元"


def turnover_metrics(history: list[dict], windows: tuple[int, ...] = (5, 20)) -> dict:
    """Derive market turnover metrics from the API's daily amount history.

    与研发后台 `turnover_metrics` 同口径：只使用 `amount`，不使用 `volume`。
    """
    series = [row["amount"] for row in history if row.get("amount") is not None]
    latest = series[-1] if series else None
    previous = series[-2] if len(series) >= 2 else None
    metrics: dict[str, float | None] = {
        "latest": latest,
        "change_1d": latest / previous - 1 if latest and previous else None,
    }
    for window in windows:
        average = sum(series[-window - 1:-1]) / window if len(series) >= window + 1 else None
        metrics[f"avg_{window}d"] = average
        metrics[f"vs_{window}d_avg"] = latest / average - 1 if latest and average else None
    return metrics


def turnover_comparison_label(change_5d: float | None, change_20d: float | None) -> str:
    if change_5d is None or change_20d is None:
        return INSUFFICIENT
    if change_5d < 0 and change_20d < 0:
        return "低于5日和20日平均成交额"
    if change_5d > 0 and change_20d > 0:
        return "高于5日和20日平均成交额"
    return "短期与中期成交额对比不一致"

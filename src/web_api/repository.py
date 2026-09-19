"""Read-only product repository for Strategy1 MVP artifacts."""

from __future__ import annotations

import csv
import json
import os
import sqlite3
from collections import Counter, defaultdict
from pathlib import Path
from threading import Lock


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
MARKET_REPORT_DIR = DATA_DIR / "market_data_reports"
MVP_REPORT_DIR = DATA_DIR / "strategy1_mvp_reports"
DATABASE_PATH = DATA_DIR / "market_data.db"
DATASET_PATH = MARKET_REPORT_DIR / "strategy1_demo_dataset.csv"
DATASET_REPORT_PATH = MARKET_REPORT_DIR / "strategy1_demo_dataset_report.json"
SIGNAL_REPORT_PATH = MVP_REPORT_DIR / "strategy1_signal_report.csv"
TRADE_REPORT_PATH = MVP_REPORT_DIR / "strategy1_trade_records.csv"
BACKTEST_SUMMARY_PATH = MVP_REPORT_DIR / "strategy1_mvp_backtest_summary.json"
SIGNAL_CACHE_PATH = MVP_REPORT_DIR / "strategy1_signal_details.csv"

SIGNAL_CACHE_COLUMNS = (
    "code", "name", "signal_date", "buy_price", "ma5_distance",
    "pressure_distance", "score", "entry_reason", "risk_warning",
)

RISK_WARNING = (
    "当前历史研究版本尚未应用历史流通市值和历史ST过滤；buy_price为T+1计划挂单价，"
    "实际成交仍要求T+1开盘价不高于该价格。"
)


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _stock_names() -> dict[str, str]:
    connection = sqlite3.connect(DATABASE_PATH, timeout=30)
    try:
        return {
            str(code): str(name)
            for code, name in connection.execute("SELECT code,name FROM stock_basic")
        }
    finally:
        connection.close()


def _cache_is_current() -> bool:
    """Online Dataset V1: the 1.13 GB dataset CSV is not shipped online.

    The pre-built signal cache is the runtime source; the dataset CSV only takes
    part in the freshness comparison when it is actually present (research env).
    """
    if not SIGNAL_CACHE_PATH.exists():
        return False
    references = [SIGNAL_REPORT_PATH.stat().st_mtime]
    if DATASET_PATH.exists():
        references.append(DATASET_PATH.stat().st_mtime)
    return SIGNAL_CACHE_PATH.stat().st_mtime >= max(references)


def build_signal_cache(force: bool = False) -> dict[str, object]:
    """Materialize signal details once; never changes strategy calculations."""
    if not force and _cache_is_current():
        with SIGNAL_CACHE_PATH.open("r", encoding="utf-8-sig", newline="") as handle:
            count = sum(1 for _ in csv.DictReader(handle))
        return {"status": "CURRENT", "row_count": count, "path": str(SIGNAL_CACHE_PATH)}

    signal_keys: set[tuple[str, str]] = set()
    with SIGNAL_REPORT_PATH.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            signal_keys.add((row["股票"].zfill(6), row["日期"]))

    if not DATASET_PATH.exists():
        raise RuntimeError(
            "ONLINE_DATASET_V1: signal cache rebuild requires the full dataset CSV, "
            "which is intentionally not part of the online dataset. Keep the pre-built cache."
        )

    names = _stock_names()
    temporary = SIGNAL_CACHE_PATH.with_suffix(".csv.tmp")
    found: set[tuple[str, str]] = set()
    with DATASET_PATH.open("r", encoding="utf-8-sig", newline="") as source, \
         temporary.open("w", encoding="utf-8-sig", newline="") as target:
        reader = csv.DictReader(source)
        writer = csv.DictWriter(target, fieldnames=SIGNAL_CACHE_COLUMNS, lineterminator="\n")
        writer.writeheader()
        for row in reader:
            key = (row["code"].zfill(6), row["date"])
            if key not in signal_keys:
                continue
            ma5_distance = float(row["ma5_distance"])
            pressure_distance = float(row["pressure_distance"])
            ma5_ok = 0.03 <= ma5_distance <= 0.10
            pressure_ok = 0.30 <= pressure_distance <= 0.50
            score = (50 if ma5_ok else 0) + (50 if pressure_ok else 0)
            writer.writerow({
                "code": key[0],
                "name": names.get(key[0], "UNKNOWN"),
                "signal_date": key[1],
                "buy_price": float(row["MA5"]) * 1.03,
                "ma5_distance": ma5_distance,
                "pressure_distance": pressure_distance,
                "score": score,
                "entry_reason": (
                    f"MA5距离={ma5_distance:.4%}，满足3%-10%；"
                    f"20日压力距离={pressure_distance:.4%}，满足30%-50%"
                ),
                "risk_warning": RISK_WARNING,
            })
            found.add(key)
    if found != signal_keys:
        temporary.unlink(missing_ok=True)
        missing = sorted(signal_keys - found)[:20]
        raise RuntimeError(f"Signal cache incomplete: missing {len(signal_keys-found)} keys; sample={missing}")
    os.replace(temporary, SIGNAL_CACHE_PATH)
    return {"status": "BUILT", "row_count": len(found), "path": str(SIGNAL_CACHE_PATH)}


class Strategy1ProductRepository:
    def __init__(self) -> None:
        build_signal_cache()
        self.backtest = _load_json(BACKTEST_SUMMARY_PATH)
        self.dataset = _load_json(DATASET_REPORT_PATH)
        self.signals: list[dict[str, object]] = []
        self.signals_by_date: dict[str, list[dict[str, object]]] = defaultdict(list)
        self.signals_by_code: dict[str, list[dict[str, object]]] = defaultdict(list)
        with SIGNAL_CACHE_PATH.open("r", encoding="utf-8-sig", newline="") as handle:
            for raw in csv.DictReader(handle):
                item: dict[str, object] = {
                    "code": raw["code"].zfill(6),
                    "name": raw["name"],
                    "signal_date": raw["signal_date"],
                    "buy_price": float(raw["buy_price"]),
                    "ma5_distance": float(raw["ma5_distance"]),
                    "pressure_distance": float(raw["pressure_distance"]),
                    "score": int(raw["score"]),
                    "entry_reason": raw["entry_reason"],
                    "risk_warning": raw["risk_warning"],
                }
                self.signals.append(item)
                self.signals_by_date[str(item["signal_date"])].append(item)
                self.signals_by_code[str(item["code"])].append(item)

        self.trades_by_code: dict[str, list[dict[str, object]]] = defaultdict(list)
        with TRADE_REPORT_PATH.open("r", encoding="utf-8-sig", newline="") as handle:
            for raw in csv.DictReader(handle):
                code = raw["股票代码"].zfill(6)
                self.trades_by_code[code].append({
                    "code": code,
                    "buy_date": raw["买入日期"],
                    "buy_price": float(raw["买入价格"]),
                    "sell_date": raw["卖出日期"],
                    "sell_price": float(raw["卖出价格"]),
                    "holding_days": int(raw["持仓天数"]),
                    "return": float(raw["收益率"]),
                    "exit_reason": raw["卖出原因"],
                })

    @property
    def market_date(self) -> str:
        return str(self.dataset["last_date"])

    def overview(self) -> dict[str, object]:
        candidates = self.signals_by_date.get(self.market_date, [])
        return {
            "current_market_date": self.market_date,
            "strategy_name": "Strategy1 V1.1 历史研究版",
            "stock_count": int(self.dataset["security_count"]),
            "today_candidate_count": len(candidates),
            "today_candidate_stocks": candidates,
            "data_scope_warning": RISK_WARNING,
        }

    def signal_page(self, date: str | None, offset: int, limit: int) -> dict[str, object]:
        selected_date = date or self.market_date
        items = self.signals_by_date.get(selected_date, [])
        return {
            "signal_date": selected_date,
            "total": len(items),
            "offset": offset,
            "limit": limit,
            "items": items[offset:offset + limit],
            "score_definition": "MA5距离条件50分 + 20日压力距离条件50分；仅表示冻结规则满足度，不改变排序或交易规则。",
        }

    @staticmethod
    def _market_connection() -> sqlite3.Connection:
        uri = DATABASE_PATH.resolve().as_uri() + "?mode=ro"
        connection = sqlite3.connect(uri, uri=True, timeout=30)
        connection.row_factory = sqlite3.Row
        return connection

    def stock_page(
        self,
        status: str,
        market: str | None,
        query: str | None,
        offset: int,
        limit: int,
    ) -> dict[str, object]:
        """Return a paginated P1-backed security directory without changing Strategy1."""
        where = ["c.dataset='market_daily_full_history'"]
        params: list[object] = []
        if status != "ALL":
            where.append("c.status=?")
            params.append(status)
        if market:
            where.append("b.market=?")
            params.append(market)
        if query:
            where.append("(b.code LIKE ? OR b.name LIKE ?)")
            pattern = f"%{query.strip()}%"
            params.extend((pattern, pattern))
        predicate = " AND ".join(where)
        with self._market_connection() as connection:
            total = int(connection.execute(
                f"""
                SELECT COUNT(*)
                FROM stock_basic b
                JOIN ingestion_checkpoint c USING(code,exchange)
                WHERE {predicate}
                """,
                params,
            ).fetchone()[0])
            rows = connection.execute(
                f"""
                SELECT b.code,b.name,b.exchange,b.market,b.is_currently_listed,
                       c.status AS checkpoint_status,c.last_success_date,
                       (SELECT COUNT(*) FROM market_daily d
                        WHERE d.code=b.code AND d.exchange=b.exchange AND d.adjust_type='RAW') AS raw_rows,
                       (SELECT MIN(date) FROM market_daily d
                        WHERE d.code=b.code AND d.exchange=b.exchange AND d.adjust_type='RAW') AS first_date,
                       (SELECT MAX(date) FROM market_daily d
                        WHERE d.code=b.code AND d.exchange=b.exchange AND d.adjust_type='RAW') AS last_date
                FROM stock_basic b
                JOIN ingestion_checkpoint c USING(code,exchange)
                WHERE {predicate}
                ORDER BY b.code,b.exchange
                LIMIT ? OFFSET ?
                """,
                (*params, limit, offset),
            ).fetchall()
        return {
            "scope": "P1_FULL_HISTORY_CHECKPOINT",
            "status_filter": status,
            "market_filter": market,
            "query": query,
            "total": total,
            "offset": offset,
            "limit": limit,
            "items": [dict(row) for row in rows],
            "definition": (
                "COMMITTED表示P1全历史采集通过质量门禁；FAILED不被伪装为成功。"
                "证券宇宙、P1完成状态与Strategy1冻结回测范围是不同口径。"
            ),
        }

    def backtest_performance(self) -> dict[str, object]:
        return {
            "total_trades": self.backtest["total_trades"],
            "win_rate": self.backtest["win_rate"],
            "avg_return": self.backtest["average_return"],
            "profit_loss_ratio": self.backtest["profit_loss_ratio"],
            "max_drawdown": self.backtest["maximum_drawdown"],
            "exit_reason_statistics": self.backtest["exit_reason_counts"],
            "equity_curve": self.backtest["equity_curve"],
            "equity_curve_method": self.backtest["equity_curve_method"],
        }

    def stock_detail(self, code: str, lookback: int = 120) -> dict[str, object] | None:
        normalized = code.zfill(6)
        signals = sorted(self.signals_by_code.get(normalized, []), key=lambda item: str(item["signal_date"]))
        trades = sorted(self.trades_by_code.get(normalized, []), key=lambda item: str(item["buy_date"]))
        with self._market_connection() as connection:
            basics = connection.execute(
                """
                SELECT b.code,b.name,b.exchange,b.market,b.list_date,b.delist_date,b.is_currently_listed,
                       c.status checkpoint_status,c.last_success_date,c.rows_written,c.provider,c.error
                FROM stock_basic b
                LEFT JOIN ingestion_checkpoint c ON c.code=b.code AND c.exchange=b.exchange
                    AND c.dataset='market_daily_full_history'
                WHERE b.code=? ORDER BY b.exchange LIMIT 1
                """,
                (normalized,),
            ).fetchone()
            if basics is None:
                return None
            summary = connection.execute(
                """
                SELECT COUNT(*) raw_rows,MIN(date) first_date,MAX(date) last_date,
                       COUNT(DISTINCT source) provider_count
                FROM market_daily WHERE code=? AND exchange=? AND adjust_type='RAW'
                """,
                (normalized, basics["exchange"]),
            ).fetchone()
            history = connection.execute(
                """
                SELECT date,open,high,low,close,volume,amount,source
                FROM market_daily
                WHERE code=? AND exchange=? AND adjust_type='RAW'
                ORDER BY date DESC LIMIT ?
                """,
                (normalized, basics["exchange"], lookback),
            ).fetchall()
        returns = [float(item["return"]) for item in trades]
        exit_reasons = Counter(str(item["exit_reason"]) for item in trades)
        return {
            "code": normalized,
            "name": str(basics["name"]),
            "exchange": str(basics["exchange"]),
            "market": str(basics["market"]),
            "is_currently_listed": basics["is_currently_listed"],
            "p1_status": str(basics["checkpoint_status"] or "NOT_AVAILABLE"),
            "market_data_summary": {
                "adjust_type": "RAW",
                "raw_rows": int(summary["raw_rows"]),
                "first_date": summary["first_date"],
                "last_date": summary["last_date"],
                "last_success_date": basics["last_success_date"],
                "source_count": int(summary["provider_count"]),
                "data_source": "data/market_data.db.market_daily",
            },
            "raw_history": [dict(row) for row in reversed(history)],
            "latest_signal": signals[-1] if signals else None,
            "historical_trade_records": trades,
            "performance": {
                "trade_count": len(trades),
                "win_rate": sum(value > 0 for value in returns) / len(returns) if returns else 0.0,
                "average_return": sum(returns) / len(returns) if returns else 0.0,
                "cumulative_simple_return": sum(returns),
            },
            "buy_reason": signals[-1]["entry_reason"] if signals else None,
            "sell_reason_statistics": dict(sorted(exit_reasons.items())),
            "risk_warning": RISK_WARNING,
            "strategy1_scope": (
                "Strategy1字段来自冻结的历史研究产物；P1 RAW行情接入不会自动重算信号、成交或回测。"
            ),
        }


_repository: Strategy1ProductRepository | None = None
_repository_lock = Lock()


def get_repository() -> Strategy1ProductRepository:
    global _repository
    if _repository is None:
        with _repository_lock:
            if _repository is None:
                _repository = Strategy1ProductRepository()
    return _repository

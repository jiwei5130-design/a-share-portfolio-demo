"""Read-only access to precomputed strategy research artifacts."""

from __future__ import annotations

from functools import lru_cache
import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
REGIME_RESEARCH_PATH = (
    PROJECT_ROOT / "data" / "strategy1_mvp_reports" / "strategy1_market_regime_research.json"
)
PORTFOLIO_RISK_PATH = (
    PROJECT_ROOT / "data" / "strategy1_mvp_reports" / "strategy1_portfolio_risk_research.json"
)
LANDMARK_RESEARCH_GATE_PATH = (
    PROJECT_ROOT / "data" / "strategy2_landmark_research" / "strategy2_landmark_research_gate.json"
)
LANDMARK_EVIDENCE_PATH = (
    PROJECT_ROOT / "data" / "strategy2_landmark_research" / "strategy2_landmark_research_evidence.json"
)


@lru_cache(maxsize=4)
def _load_regime_research(modified_ns: int, size: int) -> dict[str, object]:
    del modified_ns, size
    return json.loads(REGIME_RESEARCH_PATH.read_text(encoding="utf-8"))


@lru_cache(maxsize=4)
def _load_portfolio_risk(modified_ns: int, size: int) -> dict[str, object]:
    del modified_ns, size
    return json.loads(PORTFOLIO_RISK_PATH.read_text(encoding="utf-8"))


def strategy1_regime_performance() -> dict[str, object]:
    """Return the small precomputed artifact; never run a backtest in a request."""
    if not REGIME_RESEARCH_PATH.exists():
        raise LookupError("STRATEGY1_REGIME_RESEARCH_NOT_AVAILABLE")
    stat = REGIME_RESEARCH_PATH.stat()
    return _load_regime_research(stat.st_mtime_ns, stat.st_size)


def strategy1_portfolio_risk() -> dict[str, object]:
    """Return the precomputed portfolio risk study; never run a simulation in a request."""
    if not PORTFOLIO_RISK_PATH.exists():
        raise LookupError("STRATEGY1_PORTFOLIO_RISK_RESEARCH_NOT_AVAILABLE")
    stat = PORTFOLIO_RISK_PATH.stat()
    return _load_portfolio_risk(stat.st_mtime_ns, stat.st_size)


@lru_cache(maxsize=4)
def _load_landmark_research(modified_ns: int, size: int) -> dict[str, object]:
    del modified_ns, size
    return json.loads(LANDMARK_RESEARCH_GATE_PATH.read_text(encoding="utf-8"))


def strategy2_landmark_research() -> dict[str, object]:
    """Return the precomputed Strategy2 research-gate summary; never run research in a request."""
    if not LANDMARK_RESEARCH_GATE_PATH.exists():
        raise LookupError("STRATEGY2_LANDMARK_RESEARCH_GATE_NOT_AVAILABLE")
    stat = LANDMARK_RESEARCH_GATE_PATH.stat()
    return _load_landmark_research(stat.st_mtime_ns, stat.st_size)


@lru_cache(maxsize=4)
def _load_landmark_evidence(modified_ns: int, size: int) -> dict[str, object]:
    del modified_ns, size
    return json.loads(LANDMARK_EVIDENCE_PATH.read_text(encoding="utf-8"))


def strategy2_landmark_evidence() -> dict[str, object]:
    """Return the read-only evidence artifact; never run research in a request."""
    if not LANDMARK_EVIDENCE_PATH.exists():
        raise LookupError("STRATEGY2_LANDMARK_EVIDENCE_NOT_AVAILABLE")
    stat = LANDMARK_EVIDENCE_PATH.stat()
    return _load_landmark_evidence(stat.st_mtime_ns, stat.st_size)

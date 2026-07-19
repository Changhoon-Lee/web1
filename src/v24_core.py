#!/usr/bin/env python3
"""Authoritative V24 core wrapper.

The fully auditable reference implementation is retained in
``v24_core_legacy.py``. This wrapper re-exports it and replaces only:

1. JSON serialization, to guarantee RFC-compatible null values for NaN/Inf.
2. The ex-post feasibility diagnostic, using the exact same static-return
   equation without constructing 601 unnecessary ledgers.

Strategy execution, online updates, risk controls and exact ledgers remain the
reference implementation without modification.
"""
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

import v24_core_legacy as _reference

for _name in dir(_reference):
    if not _name.startswith("__"):
        globals()[_name] = getattr(_reference, _name)


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_safe(v) for v in value]
    if isinstance(value, np.ndarray):
        return [_json_safe(v) for v in value.tolist()]
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating, float)):
        x = float(value)
        return x if math.isfinite(x) else None
    if isinstance(value, (np.bool_, bool)):
        return bool(value)
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if isinstance(value, Path):
        return str(value)
    return value


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(_json_safe(payload), indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def feasibility_screen(data: pd.DataFrame, cfg: Config, baseline: StrategyResult) -> dict[str, Any]:
    """Exact ex-post 50/50-overlay feasibility screen without ledger creation."""
    baseline_metrics = performance_metrics(baseline.returns, pd.Series(1.0, index=baseline.returns.index))
    target_mdd = baseline_metrics["mdd"] + cfg.target_mdd_improvement
    oos = data.reindex(baseline.returns.index)
    base = oos["V10"].to_numpy(dtype=float)
    diversifier = 0.5 * (oos["EQUITY_TREND"].to_numpy(dtype=float) + oos["GOLD_TREND"].to_numpy(dtype=float))
    financing_per_unit = oos["CASH"].to_numpy(dtype=float) + cfg.borrow_spread_annual / ANNUALIZATION
    cost_rate = cfg.one_way_cost_bps / 10_000.0
    index = baseline.returns.index
    required_q: float | None = None
    risk_q = 0.0
    records: list[dict[str, float]] = []
    for q in np.linspace(0.0, cfg.max_overlay, 601):
        values = base + q * diversifier - q * financing_per_unit
        values = values.copy()
        if len(values):
            values[0] -= q * cost_rate
        series = pd.Series(values, index=index)
        gross = pd.Series(1.0 + q, index=index)
        metrics = performance_metrics(series, gross)
        if required_q is None and metrics["cagr"] >= baseline_metrics["cagr"]:
            required_q = float(q)
        if metrics["mdd"] >= target_mdd:
            risk_q = float(q)
        records.append({
            "overlay": float(q),
            "cagr": float(metrics["cagr"]),
            "mdd": float(metrics["mdd"]),
            "sharpe": float(metrics["sharpe"]),
            "final_equity": float(metrics["final_equity"]),
        })
    q_required = float("inf") if required_q is None else required_q
    q_cap = min(float(cfg.max_overlay), risk_q)
    return {
        "diagnostic_only_ex_post": True,
        "required_overlay_for_v10_cagr": q_required,
        "maximum_overlay_under_mdd_gate": q_cap,
        "protocol_max_overlay": cfg.max_overlay,
        "feasible": bool(math.isfinite(q_required) and q_required <= q_cap + 1e-12),
        "feasible_interval": [q_required, q_cap],
        "target_mdd": target_mdd,
        "grid": records,
    }


# Make the overrides visible to introspection and explicit imports.
_reference.write_json = write_json
_reference.feasibility_screen = feasibility_screen

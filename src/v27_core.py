#!/usr/bin/env python3
"""Authoritative V27 wrapper with final liquidation accounting."""
from __future__ import annotations

import math
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

import v27_core_legacy as _legacy

for _name in dir(_legacy):
    if not _name.startswith("__"):
        globals()[_name] = getattr(_legacy, _name)

VERSION = "27.0.1"


def _status(metrics: dict[str, Any], cfg: Config) -> str:
    if metrics.get("calendar_days", 0.0) < cfg.minimum_backtest_days or metrics.get("roll_count", 0) < cfg.minimum_rolls:
        return "INSUFFICIENT_HISTORICAL_OPTIONS_DATA"
    if metrics.get("final_wealth_ratio", 0.0) > 1.0 and metrics.get("cagr", -1.0) > 0.0 and metrics.get("top_5pct_positive_day_concentration", 1.0) <= cfg.concentration_limit:
        return "HISTORICAL_LONG_GAMMA_PASS_NEEDS_NEW_OOS"
    return "HISTORICAL_LONG_GAMMA_REJECTED"


def run_long_gamma(data: pd.DataFrame, cfg: Config, name: str = "V27_PRIMARY", cost_multiplier: float = 1.0, latency_bars: int | None = None, hedge_enabled: bool = True) -> BacktestResult:
    result = _legacy.run_long_gamma(data, cfg, name, cost_multiplier, latency_bars, hedge_enabled)
    if result.ledger.empty or result.trades.empty:
        return result
    end = result.trades[result.trades.get("reason", "") == "END_OF_SAMPLE"]
    if end.empty:
        return result
    last = result.ledger.iloc[-1].copy()
    final_cash = float(last["cash"]) + float(pd.to_numeric(end["cash_flow"], errors="coerce").fillna(0.0).sum())
    final_ts = pd.Timestamp(last["timestamp"]) + pd.Timedelta(nanoseconds=1)
    last["timestamp"] = final_ts
    last["cash"] = final_cash
    last["option_value"] = 0.0
    last["equity"] = final_cash
    last["hedge_quantity"] = 0.0
    last["option_delta"] = 0.0
    last["net_delta"] = 0.0
    last["option_quantity"] = 0.0
    last["call_symbol"] = ""
    last["put_symbol"] = ""
    last["cumulative_fees"] = float(last["cumulative_fees"]) + float(pd.to_numeric(end["fee_usd"], errors="coerce").fillna(0.0).sum())
    last["cash_nano"] = int(round(final_cash * NANO))
    last["option_value_nano"] = 0
    last["equity_nano"] = int(round(final_cash * NANO))
    ledger = pd.concat([result.ledger, pd.DataFrame([last])], ignore_index=True)
    metrics = _legacy._performance_metrics(ledger)
    metrics.update({
        "roll_count": result.metrics.get("roll_count", 0),
        "skipped_entries": result.metrics.get("skipped_entries", 0),
        "total_fees": float(last["cumulative_fees"]),
        "total_funding": result.metrics.get("total_funding", 0.0),
        "maximum_abs_hedge": float(ledger["hedge_quantity"].abs().max()),
    })
    return BacktestResult(result.name, ledger, result.trades, result.diagnostics, metrics, _status(metrics, cfg))


def audit_suite(data: pd.DataFrame, cfg: Config) -> tuple[dict[str, BacktestResult], dict[str, Any]]:
    variants = {
        "primary": run_long_gamma(data, cfg, "PRIMARY_COST_1X_LATENCY_1", 1.0, cfg.hedge_latency_bars, True),
        "unhedged": run_long_gamma(data, cfg, "UNHEDGED_STRADDLE", 1.0, 0, False),
        "cost_2x": run_long_gamma(data, cfg, "COST_2X", 2.0, cfg.hedge_latency_bars, True),
        "cost_3x": run_long_gamma(data, cfg, "COST_3X", 3.0, cfg.hedge_latency_bars, True),
        "latency_2": run_long_gamma(data, cfg, "LATENCY_2_BARS", 1.0, 2, True),
        "latency_3": run_long_gamma(data, cfg, "LATENCY_3_BARS", 1.0, 3, True),
    }
    primary = variants["primary"]
    sufficient = primary.status != "INSUFFICIENT_HISTORICAL_OPTIONS_DATA"
    tests = {
        "sufficient_contiguous_history": sufficient,
        "standalone_wealth_above_one": primary.metrics.get("final_wealth_ratio", 0.0) > 1.0,
        "positive_cagr": primary.metrics.get("cagr", -1.0) > 0.0,
        "cost_2x_survives": variants["cost_2x"].metrics.get("final_wealth_ratio", 0.0) > 1.0,
        "cost_3x_survives": variants["cost_3x"].metrics.get("final_wealth_ratio", 0.0) > 1.0,
        "latency_2_survives": variants["latency_2"].metrics.get("final_wealth_ratio", 0.0) > 1.0,
        "latency_3_survives": variants["latency_3"].metrics.get("final_wealth_ratio", 0.0) > 1.0,
        "not_concentrated": primary.metrics.get("top_5pct_positive_day_concentration", 1.0) <= cfg.concentration_limit,
        "no_liquidation": not (len(primary.diagnostics) and (primary.diagnostics.get("event") == "LIQUIDATION").any()),
    }
    if not sufficient:
        overall = "INSUFFICIENT_HISTORICAL_OPTIONS_DATA"
    elif all(tests.values()):
        overall = "HISTORICAL_DERIBIT_LONG_GAMMA_PASS_NEEDS_NEW_OOS"
    else:
        overall = "HISTORICAL_DERIBIT_LONG_GAMMA_REJECTED"
    return variants, {"version": VERSION, "primary_status": primary.status, "overall_status": overall, "tests": tests, "variant_metrics": {k: v.metrics for k, v in variants.items()}}


def output_manifest(root: Path, exclude: set[str] | None = None) -> dict[str, Any]:
    payload = _legacy.output_manifest(root, exclude)
    payload["version"] = VERSION
    return payload

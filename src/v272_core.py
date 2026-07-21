#!/usr/bin/env python3
"""V27.2.4 authoritative wrapper over the inverse-accounting implementation.

The accounting engine is unchanged. This wrapper adds the pre-trade baseline
and verifies that every live option leg used by the hedge has an actual
exchange-provided delta in the point-in-time WebSocket snapshot.
"""
from __future__ import annotations

import math
from pathlib import Path
from typing import Any, Iterable

import pandas as pd

import v272_core_legacy as _legacy

for _name in dir(_legacy):
    if not _name.startswith("__"):
        globals()[_name] = getattr(_legacy, _name)

VERSION = "27.2.4-websocket-authority"

_PERFORMANCE_KEYS = {
    "observations", "start", "end", "calendar_days", "final_equity",
    "final_wealth_ratio", "cagr", "sharpe", "mdd",
    "top_5pct_positive_day_concentration",
}


def _status(metrics: dict[str, Any], cfg: Config) -> str:
    sufficient = metrics.get("calendar_days", 0.0) >= cfg.minimum_backtest_days and metrics.get("roll_count", 0) >= cfg.minimum_rolls
    continuity = (
        metrics.get("held_option_quote_coverage", 0.0) >= cfg.minimum_held_quote_coverage
        and metrics.get("held_option_delta_coverage", 0.0) >= 0.99
        and metrics.get("missing_delta_bar_count", 1) == 0
        and metrics.get("executable_close_coverage", 0.0) >= 1.0
        and metrics.get("perpetual_quote_coverage", 0.0) >= cfg.minimum_perp_quote_coverage
        and metrics.get("funding_coverage", 0.0) >= cfg.minimum_funding_coverage
    )
    if not sufficient:
        return "INSUFFICIENT_HISTORICAL_OPTIONS_DATA"
    if not continuity:
        return "MARKET_DATA_CONTINUITY_GATE_FAILED"
    if (
        metrics.get("final_wealth_ratio", 0.0) > 1.0
        and metrics.get("cagr", -1.0) > 0.0
        and metrics.get("top_5pct_positive_day_concentration", 1.0) <= cfg.concentration_limit
    ):
        return "HISTORICAL_LONG_GAMMA_PASS_NEEDS_NEW_OOS"
    return "HISTORICAL_LONG_GAMMA_REJECTED"


def _prepend_initial_equity(result: BacktestResult, cfg: Config) -> BacktestResult:
    if result.ledger.empty:
        return result
    first = result.ledger.iloc[0].copy()
    baseline = first.copy()
    baseline["timestamp"] = pd.Timestamp(first["timestamp"]) - pd.Timedelta(1, unit="ns")
    baseline["cash_usd"] = cfg.initial_equity_usd
    baseline["option_value_usd"] = 0.0
    baseline["equity_usd"] = cfg.initial_equity_usd
    baseline["perp_notional_usd"] = 0.0
    baseline["option_delta_btc"] = 0.0
    baseline["net_delta_btc"] = 0.0
    baseline["maintenance_margin_usd"] = 0.0
    baseline["margin_ratio"] = 0.0
    baseline["option_quantity"] = 0.0
    baseline["call_symbol"] = ""
    baseline["put_symbol"] = ""
    for column in (
        "cumulative_option_fees_usd", "cumulative_perp_fees_usd",
        "cumulative_funding_usd", "cumulative_perp_pnl_usd",
    ):
        baseline[column] = 0.0
    baseline["cash_nano"] = int(round(cfg.initial_equity_usd * NANO))
    baseline["option_value_nano"] = 0
    baseline["equity_nano"] = int(round(cfg.initial_equity_usd * NANO))
    ledger = pd.concat([pd.DataFrame([baseline]), result.ledger], ignore_index=True)
    metrics = _legacy._performance_metrics(ledger)
    metrics.update({key: value for key, value in result.metrics.items() if key not in _PERFORMANCE_KEYS})
    return BacktestResult(result.name, ledger, result.trades, result.diagnostics, metrics, _status(metrics, cfg))


def _held_delta_metrics(data: pd.DataFrame, ledger: pd.DataFrame) -> dict[str, Any]:
    """Measure actual exchange delta availability for every live option leg.

    No Black-Scholes fallback is accepted for this authority gate. The
    accounting engine may calculate a diagnostic fallback, but the economic
    result cannot pass unless the recorded point-in-time rows contain delta.
    """
    if ledger.empty:
        return {"held_option_delta_coverage": 0.0, "missing_delta_bar_count": 0, "held_delta_required": 0, "held_delta_available": 0}
    market = data.copy()
    market["timestamp"] = pd.to_datetime(market["timestamp"], utc=True, errors="coerce")
    market["symbol"] = market["symbol"].astype(str).str.upper()
    market = market.sort_values(["timestamp", "symbol"]).drop_duplicates(["timestamp", "symbol"], keep="last")
    lookup = {(row.timestamp, row.symbol): row.delta for row in market[["timestamp", "symbol", "delta"]].itertuples(index=False)}
    required = 0
    available = 0
    missing_bars = 0
    for row in ledger.itertuples(index=False):
        timestamp = pd.Timestamp(getattr(row, "timestamp"))
        symbols = [str(getattr(row, "call_symbol", "")).upper(), str(getattr(row, "put_symbol", "")).upper()]
        symbols = [symbol for symbol in symbols if symbol]
        if not symbols:
            continue
        bar_missing = False
        for symbol in symbols:
            required += 1
            value = lookup.get((timestamp, symbol))
            if value is not None and math.isfinite(float(value)):
                available += 1
            else:
                bar_missing = True
        if bar_missing:
            missing_bars += 1
    return {
        "held_option_delta_coverage": available / required if required else 1.0,
        "missing_delta_bar_count": missing_bars,
        "held_delta_required": required,
        "held_delta_available": available,
    }


def run_long_gamma(
    data: pd.DataFrame,
    cfg: Config,
    name: str = "V272_PRIMARY",
    cost_multiplier: float = 1.0,
    latency_bars: int | None = None,
    hedge_enabled: bool = True,
    held_state_file: Path | None = None,
) -> BacktestResult:
    _legacy.VERSION = VERSION
    raw = _legacy.run_long_gamma(data, cfg, name, cost_multiplier, latency_bars, hedge_enabled, held_state_file)
    result = _prepend_initial_equity(raw, cfg)
    metrics = dict(result.metrics)
    metrics.update(_held_delta_metrics(data, result.ledger))
    return BacktestResult(result.name, result.ledger, result.trades, result.diagnostics, metrics, _status(metrics, cfg))


def audit_suite(data: pd.DataFrame, cfg: Config, held_state_file: Path | None = None) -> tuple[dict[str, BacktestResult], dict[str, Any]]:
    variants = {
        "primary": run_long_gamma(data, cfg, "PRIMARY_ACTUAL_INVERSE", 1.0, cfg.hedge_latency_bars, True, held_state_file),
        "unhedged": run_long_gamma(data, cfg, "UNHEDGED", 1.0, 0, False),
        "cost_2x": run_long_gamma(data, cfg, "COST_2X", 2.0, cfg.hedge_latency_bars, True),
        "cost_3x": run_long_gamma(data, cfg, "COST_3X", 3.0, cfg.hedge_latency_bars, True),
        "latency_2": run_long_gamma(data, cfg, "LATENCY_2", 1.0, 2, True),
        "latency_3": run_long_gamma(data, cfg, "LATENCY_3", 1.0, 3, True),
    }
    primary = variants["primary"]
    tests = {
        "sufficient_history": primary.status not in {"INSUFFICIENT_HISTORICAL_OPTIONS_DATA", "MARKET_DATA_CONTINUITY_GATE_FAILED"},
        "held_quote_coverage": primary.metrics.get("held_option_quote_coverage", 0.0) >= cfg.minimum_held_quote_coverage,
        "held_delta_coverage": primary.metrics.get("held_option_delta_coverage", 0.0) >= 0.99,
        "no_missing_delta_bars": primary.metrics.get("missing_delta_bar_count", 1) == 0,
        "all_closes_executable": primary.metrics.get("missing_close_bid_count", 1) == 0,
        "perpetual_quote_coverage": primary.metrics.get("perpetual_quote_coverage", 0.0) >= cfg.minimum_perp_quote_coverage,
        "actual_funding_coverage": primary.metrics.get("funding_coverage", 0.0) >= cfg.minimum_funding_coverage,
        "wealth_above_one": primary.metrics.get("final_wealth_ratio", 0.0) > 1.0,
        "positive_cagr": primary.metrics.get("cagr", -1.0) > 0.0,
        "cost_2x_survives": variants["cost_2x"].metrics.get("final_wealth_ratio", 0.0) > 1.0,
        "cost_3x_survives": variants["cost_3x"].metrics.get("final_wealth_ratio", 0.0) > 1.0,
        "latency_2_survives": variants["latency_2"].metrics.get("final_wealth_ratio", 0.0) > 1.0,
        "latency_3_survives": variants["latency_3"].metrics.get("final_wealth_ratio", 0.0) > 1.0,
        "not_concentrated": primary.metrics.get("top_5pct_positive_day_concentration", 1.0) <= cfg.concentration_limit,
        "no_liquidation": not (
            len(primary.diagnostics)
            and primary.diagnostics.get("event", pd.Series(dtype=str)).astype(str).str.contains("LIQUIDATION").any()
        ),
        "initial_equity_identity": (
            not primary.ledger.empty
            and float(primary.ledger.iloc[0]["equity_usd"]) == cfg.initial_equity_usd
            and int(primary.ledger.iloc[0]["equity_nano"]) == int(round(cfg.initial_equity_usd * NANO))
        ),
    }
    if primary.status == "INSUFFICIENT_HISTORICAL_OPTIONS_DATA":
        overall = "INSUFFICIENT_CONTIGUOUS_OPTIONS_DATA"
    elif primary.status == "MARKET_DATA_CONTINUITY_GATE_FAILED":
        overall = "MARKET_DATA_CONTINUITY_GATE_FAILED"
    elif all(tests.values()):
        overall = "HISTORICAL_DERIBIT_LONG_GAMMA_PASS_NEEDS_NEW_OOS"
    else:
        overall = "HISTORICAL_DERIBIT_LONG_GAMMA_REJECTED"
    return variants, {
        "version": VERSION,
        "primary_status": primary.status,
        "overall_status": overall,
        "tests": tests,
        "variant_metrics": {key: value.metrics for key, value in variants.items()},
    }


def output_manifest(root: Path, exclude: set[str] | None = None) -> dict[str, Any]:
    payload = _legacy.output_manifest(root, exclude)
    payload["version"] = VERSION
    return payload

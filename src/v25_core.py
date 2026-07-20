#!/usr/bin/env python3
"""Authoritative V25 core wrapper.

The complete reference implementation is retained in ``v25_core_legacy.py``.
This wrapper re-exports it and corrects the equal-average diagnostic's initial
turnover so that it starts from the actual V10 100% baseline rather than cash.
"""
from __future__ import annotations

import pandas as pd

import v25_core_legacy as _reference

for _name in dir(_reference):
    if not _name.startswith("__"):
        globals()[_name] = getattr(_reference, _name)

VERSION = "25.0.1"


def run_equal_average_control(data: pd.DataFrame, cfg: Config, source: StrategyResult, name: str) -> StrategyResult:
    idx = source.weights.index
    tails = tail_columns(data)
    average = source.weights[["V10"] + tails + ["CASH"]].mean()
    weights = pd.DataFrame({col: float(average[col]) for col in average.index}, index=idx)
    risky = ["V10"] + tails
    turnover = weights[risky].diff().abs().sum(axis=1)
    initial = abs(float(weights.iloc[0]["V10"]) - 1.0) + sum(abs(float(weights.iloc[0][col])) for col in tails)
    turnover.iloc[0] = initial
    costs = turnover * cfg.one_way_cost_bps / 10_000.0
    returns = weights["V10"] * data.loc[idx, "V10"] + weights["CASH"] * data.loc[idx, "CASH"]
    for col in tails:
        returns += weights[col] * data.loc[idx, col].fillna(0.0)
    returns -= costs
    equity = (1.0 + returns).cumprod()
    ledger = _make_ledger(idx, weights, turnover, costs, returns)
    return StrategyResult(name, returns, weights, turnover, costs, equity, ledger, pd.DataFrame(index=idx), pd.DataFrame())

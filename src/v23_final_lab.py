#!/usr/bin/env python3
"""V23.1 Final Pareto Audit Lab.

A self-contained, causal rolling audit for three engine returns:
GROWTH_CRYPTO, EQUITY_TREND, GOLD_TREND, plus V10 and optional CASH.

It evaluates:
- uniform anchor 1x
- causal inverse-stress-vol anchor 1x
- static anchor 1.30/1.45/1.60x
- dynamic risk-budget anchor without online tilt
- dynamic risk-budget anchor with bounded online mirror-descent tilt
- equal-average-leverage static diagnostics
- feasibility, attribution, statistics and stress tests

No network or LLM calls are made by the research engine.
"""
from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import math
import os
import platform
import shutil
import statistics
import sys
import tempfile
import zipfile
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Any, Iterable, Sequence

import numpy as np
import pandas as pd

VERSION = "23.1.0"
ANNUALIZATION = 365.25
ENGINES = ("GROWTH_CRYPTO", "EQUITY_TREND", "GOLD_TREND")
LEVERAGE_STATES = np.asarray([1.00, 1.15, 1.30, 1.45, 1.60], dtype=float)


@dataclass(frozen=True)
class Config:
    delay: int = 2
    warmup_days: int = 756
    cost_bps: float = 17.0
    financing_rate: float = 0.05
    max_leverage: float = 1.60
    leverage_up_confirm_days: int = 10
    corr_floor: float = 0.75
    shrinkage: float = 0.25
    anchor_min_weight: float = 0.20
    anchor_max_weight: float = 0.50
    tilt_abs_bound: float = 0.10
    final_min_weight: float = 0.15
    final_max_weight: float = 0.55
    mdd_improvement_target: float = 0.08
    margin_min_ratio: float = 0.35
    random_seed: int = 20260719
    bootstrap_samples: int = 20000


@dataclass
class StrategyResult:
    name: str
    returns: pd.Series
    weights: pd.DataFrame
    leverage: pd.Series
    turnover: pd.Series
    financing: pd.Series
    equity: pd.Series
    ledger: pd.DataFrame
    capacities: pd.DataFrame | None = None


def json_default(value: Any) -> Any:
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        value = float(value)
        return value if math.isfinite(value) else None
    if isinstance(value, (np.bool_,)):
        return bool(value)
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, np.ndarray):
        return value.tolist()
    raise TypeError(type(value).__name__)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, default=json_default, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def sha256_frame(frame: pd.DataFrame) -> str:
    payload = frame.to_csv(index=False, lineterminator="\n", float_format="%.12g").encode()
    return hashlib.sha256(payload).hexdigest()


def _normal_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def _read_table(path: Path) -> pd.DataFrame:
    lower = path.name.lower()
    if lower.endswith(".parquet"):
        return pd.read_parquet(path)
    if lower.endswith(".csv.gz"):
        return pd.read_csv(path, compression="gzip", low_memory=False)
    if lower.endswith(".csv"):
        return pd.read_csv(path, low_memory=False)
    raise ValueError(f"Unsupported input: {path}")


def _find_column(frame: pd.DataFrame, aliases: Sequence[str]) -> str | None:
    lookup = {str(c).strip().lower(): str(c) for c in frame.columns}
    for alias in aliases:
        if alias.lower() in lookup:
            return lookup[alias.lower()]
    return None


def normalize_date_frame(frame: pd.DataFrame) -> pd.DataFrame:
    """Normalize date without the historical 'drop date after rename' bug."""
    output = frame.copy()
    aliases = ("date", "datetime", "timestamp", "time", "open_time", "day")
    date_col = _find_column(output, aliases)
    if date_col is None:
        if isinstance(output.index, pd.DatetimeIndex):
            output.index = pd.to_datetime(output.index, utc=True).normalize()
            output.index.name = "date"
            return output.sort_index()
        raise ValueError("No date column")
    raw = output[date_col]
    if pd.api.types.is_numeric_dtype(raw):
        x = pd.to_numeric(raw, errors="coerce")
        median = float(x.dropna().abs().median()) if x.notna().any() else 0.0
        unit = "ns" if median > 1e17 else "us" if median > 1e14 else "ms" if median > 1e11 else "s" if median > 1e8 else None
        dates = pd.to_datetime(x, unit=unit, utc=True, errors="coerce") if unit else pd.to_datetime(x.astype("Int64").astype(str), utc=True, errors="coerce")
    else:
        dates = pd.to_datetime(raw, utc=True, errors="coerce")
    output = output.drop(columns=[date_col]).copy()
    output.insert(0, "date", dates.dt.normalize())
    output = output.dropna(subset=["date"]).set_index("date").sort_index()
    output = output[~output.index.duplicated(keep="last")]
    return output


def canonicalize_input(path: Path) -> pd.DataFrame:
    raw = normalize_date_frame(_read_table(path))
    alias_map = {
        "GROWTH_CRYPTO": ("growth_crypto", "growth", "crypto_growth", "crypto_momentum"),
        "EQUITY_TREND": ("equity_trend", "equity", "spy_qqq", "equity_engine"),
        "GOLD_TREND": ("gold_trend", "gold", "gld", "gold_engine"),
        "V10": ("v10", "baseline_v10", "crypto_v10", "baseline"),
        "CASH": ("cash", "cash_return", "bil", "risk_free"),
    }
    output = pd.DataFrame(index=raw.index)
    for canonical, aliases in alias_map.items():
        col = _find_column(raw, aliases)
        if col is None:
            if canonical == "CASH":
                output[canonical] = 0.0
                continue
            raise ValueError(f"Missing required column {canonical}; available={list(raw.columns)}")
        output[canonical] = pd.to_numeric(raw[col], errors="coerce")
    output = output.replace([np.inf, -np.inf], np.nan).dropna(subset=list(ENGINES) + ["V10"])
    output["CASH"] = output["CASH"].fillna(0.0)
    if len(output) < 900:
        raise ValueError(f"Need at least 900 rows, got {len(output)}")
    if (output[list(ENGINES) + ["V10"]].abs() > 0.95).any().any():
        raise ValueError("Returns appear to contain prices or percentages rather than decimal daily returns")
    return output.astype(float)


def discover_input(root: Path, explicit: Path | None = None) -> Path:
    if explicit is not None:
        if not explicit.exists():
            raise FileNotFoundError(explicit)
        return explicit.resolve()
    env = os.getenv("ENGINE_RETURNS_FILE")
    if env and Path(env).expanduser().exists():
        return Path(env).expanduser().resolve()
    search_roots = [root, Path.home() / "Documents/ZCode/Autotrade", Path.home() / "Downloads"]
    patterns = ("engine_returns.csv.gz", "engine_returns.csv", "daily_engine_returns.csv.gz", "engine_daily_returns.csv.gz")
    candidates: list[Path] = []
    for base in search_roots:
        if not base.exists():
            continue
        for pattern in patterns:
            candidates.extend(base.rglob(pattern))
    if candidates:
        return max(candidates, key=lambda p: p.stat().st_mtime).resolve()
    zips: list[Path] = []
    for base in search_roots:
        if base.exists():
            zips.extend(base.rglob("V23*Handoff*.zip"))
    for archive in sorted(zips, key=lambda p: p.stat().st_mtime, reverse=True):
        try:
            with zipfile.ZipFile(archive) as zf:
                names = [n for n in zf.namelist() if Path(n).name in patterns]
                if names:
                    destination = root / "runtime/discovered" / Path(names[0]).name
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    with zf.open(names[0]) as source, destination.open("wb") as target:
                        shutil.copyfileobj(source, target)
                    return destination.resolve()
        except zipfile.BadZipFile:
            continue
    raise FileNotFoundError("Set ENGINE_RETURNS_FILE or provide --input with engine_returns.csv[.gz]")


def performance_metrics(returns: pd.Series, leverage: pd.Series | None = None) -> dict[str, float]:
    r = pd.Series(returns, dtype=float).dropna()
    if r.empty:
        return {k: 0.0 for k in ("sharpe", "cagr", "mdd", "calmar", "cvar5", "final_equity", "annual_volatility", "average_gross", "maximum_gross")}
    equity = (1.0 + r).cumprod()
    drawdown = equity / equity.cummax() - 1.0
    sd = float(r.std(ddof=1))
    sharpe = float(r.mean() / sd * math.sqrt(ANNUALIZATION)) if sd > 0 else 0.0
    years = max((r.index[-1] - r.index[0]).days / ANNUALIZATION, len(r) / ANNUALIZATION, 1 / ANNUALIZATION)
    final = float(equity.iloc[-1])
    cagr = final ** (1 / years) - 1 if final > 0 else -1.0
    mdd = float(drawdown.min())
    q = float(r.quantile(0.05))
    cvar = float(r[r <= q].mean())
    lev = pd.Series(0.0, index=r.index) if leverage is None else pd.Series(leverage).reindex(r.index).fillna(0.0)
    return {
        "observations": int(len(r)), "start": r.index[0], "end": r.index[-1],
        "sharpe": sharpe, "cagr": float(cagr), "mdd": mdd,
        "calmar": float(cagr / abs(mdd)) if mdd < 0 else 0.0,
        "cvar5": cvar, "final_equity": final,
        "annual_volatility": sd * math.sqrt(ANNUALIZATION),
        "average_gross": float(lev.mean()), "maximum_gross": float(lev.max()),
    }


def bounded_simplex(values: np.ndarray, lower: np.ndarray | float, upper: np.ndarray | float, total: float = 1.0) -> np.ndarray:
    v = np.asarray(values, dtype=float)
    lo = np.broadcast_to(np.asarray(lower, dtype=float), v.shape)
    hi = np.broadcast_to(np.asarray(upper, dtype=float), v.shape)
    if lo.sum() - 1e-12 > total or hi.sum() + 1e-12 < total:
        raise ValueError("Infeasible simplex bounds")
    left = float(np.min(v - hi)) - abs(total)
    right = float(np.max(v - lo)) + abs(total)
    for _ in range(100):
        mid = (left + right) / 2
        x = np.clip(v - mid, lo, hi)
        if x.sum() > total:
            left = mid
        else:
            right = mid
    x = np.clip(v - (left + right) / 2, lo, hi)
    residual = total - x.sum()
    if abs(residual) > 1e-10:
        order = np.argsort(-(hi - x) if residual > 0 else -(x - lo))
        for i in order:
            room = hi[i] - x[i] if residual > 0 else x[i] - lo[i]
            move = min(abs(residual), max(room, 0.0))
            x[i] += move if residual > 0 else -move
            residual += -move if residual > 0 else move
            if abs(residual) <= 1e-12:
                break
    return x


def ewma_vol(series: pd.Series, span: int) -> float:
    data = pd.Series(series, dtype=float).dropna()
    if len(data) < max(10, span // 2):
        return float("nan")
    return float(data.ewm(span=span, adjust=False).std(bias=False).iloc[-1] * math.sqrt(ANNUALIZATION))


def stress_vols(history: pd.DataFrame) -> np.ndarray:
    result = []
    for col in ENGINES:
        vals = [ewma_vol(history[col], span) for span in (20, 60, 120)]
        finite = [x for x in vals if math.isfinite(x) and x > 1e-8]
        result.append(max(finite) if finite else 1.0)
    return np.asarray(result)


def anchor_signals(data: pd.DataFrame, cfg: Config) -> pd.DataFrame:
    values = np.full((len(data), 3), 1 / 3, dtype=float)
    for t in range(120, len(data)):
        vols = stress_vols(data.iloc[: t + 1])
        raw = 1.0 / np.maximum(vols, 1e-8)
        raw /= raw.sum()
        values[t] = bounded_simplex(raw, cfg.anchor_min_weight, cfg.anchor_max_weight)
    return pd.DataFrame(values, index=data.index, columns=ENGINES)


def online_tilt_signals(data: pd.DataFrame, anchor: pd.DataFrame, cfg: Config) -> pd.DataFrame:
    result = np.zeros((len(data), 3), dtype=float)
    current = anchor.iloc[0].to_numpy(float)
    cumulative_gradient_sq = 1.0
    for t in range(len(data)):
        a = anchor.iloc[t].to_numpy(float)
        if t > 0:
            r = data.loc[data.index[t], list(ENGINES)].to_numpy(float)
            denominator = max(1e-6, 1.0 + float(current @ r))
            gradient = -r / denominator
            cumulative_gradient_sq += float(gradient @ gradient)
            eta = 1.0 / math.sqrt(cumulative_gradient_sq)
            candidate = current - eta * gradient
            lo = np.maximum(cfg.final_min_weight, a - cfg.tilt_abs_bound)
            hi = np.minimum(cfg.final_max_weight, a + cfg.tilt_abs_bound)
            current = bounded_simplex(candidate, lo, hi)
        else:
            current = a
        result[t] = current
    return pd.DataFrame(result, index=data.index, columns=ENGINES)


def shifted_targets(signal_weights: pd.DataFrame, signal_leverage: pd.Series, delay: int) -> tuple[pd.DataFrame, pd.Series]:
    actual_w = signal_weights.shift(delay).copy()
    actual_l = signal_leverage.shift(delay).copy()
    initial = signal_weights.iloc[0].to_numpy(float)
    actual_w = actual_w.fillna(pd.Series(dict(zip(ENGINES, initial))))
    actual_l = actual_l.fillna(1.0)
    return actual_w, actual_l


def simulate_from_signals(name: str, data: pd.DataFrame, weight_signal: pd.DataFrame, leverage_signal: pd.Series, cfg: Config) -> StrategyResult:
    weights, leverage = shifted_targets(weight_signal, leverage_signal, cfg.delay)
    asset_weights = weights.mul(leverage, axis=0)
    cash_weight = 1.0 - leverage
    gross_return = (asset_weights * data[list(ENGINES)]).sum(axis=1) + cash_weight * data["CASH"]
    turnover = asset_weights.diff().abs().sum(axis=1) + cash_weight.diff().abs()
    turnover.iloc[0] = asset_weights.iloc[0].abs().sum() + abs(cash_weight.iloc[0])
    trading_cost = turnover * cfg.cost_bps / 10000.0
    financing = np.maximum(leverage - 1.0, 0.0) * cfg.financing_rate / ANNUALIZATION
    net = gross_return - trading_cost - financing
    equity = (1 + net).cumprod()
    ledger = pd.DataFrame(index=data.index)
    ledger["date"] = data.index
    for col in ENGINES:
        ledger[f"signal_{col}_ppm"] = np.rint(weight_signal[col] * 1_000_000).astype(np.int64)
        ledger[f"actual_{col}_ppm"] = np.rint(asset_weights[col] * 1_000_000).astype(np.int64)
    ledger["signal_leverage_bp"] = np.rint(leverage_signal * 10_000).astype(np.int64)
    ledger["actual_leverage_bp"] = np.rint(leverage * 10_000).astype(np.int64)
    ledger["turnover_ppm"] = np.rint(turnover * 1_000_000).astype(np.int64)
    ledger["financing_nano"] = np.rint(financing * 1_000_000_000).astype(np.int64)
    ledger["net_return_nano"] = np.rint(net * 1_000_000_000).astype(np.int64)
    return StrategyResult(name, net, asset_weights, leverage, turnover, pd.Series(financing, index=data.index), equity, ledger.reset_index(drop=True))


def covariance_matrix(history: pd.DataFrame, cfg: Config, stress: bool = False) -> np.ndarray:
    x = history[list(ENGINES)].dropna().to_numpy(float)
    if len(x) < 30:
        return np.eye(3) * 0.10**2 / ANNUALIZATION
    sigma = np.cov(x, rowvar=False, ddof=1)
    sigma = (1 - cfg.shrinkage) * sigma + cfg.shrinkage * np.diag(np.diag(sigma))
    if not np.all(np.isfinite(sigma)):
        diag = np.nan_to_num(np.nanvar(x, axis=0, ddof=1), nan=1e-6, posinf=1e-6, neginf=1e-6)
        sigma = np.diag(np.maximum(diag, 1e-10))
    if stress:
        vols = np.sqrt(np.maximum(np.diag(sigma), 1e-12)) * 1.25
        corr = sigma / np.outer(np.sqrt(np.maximum(np.diag(sigma), 1e-12)), np.sqrt(np.maximum(np.diag(sigma), 1e-12)))
        corr = np.nan_to_num(corr, nan=0.0)
        corr = np.maximum(corr, cfg.corr_floor)
        np.fill_diagonal(corr, 1.0)
        sigma = np.outer(vols, vols) * corr
    return sigma


def worst_es(series: pd.Series) -> float:
    data = pd.Series(series, dtype=float).dropna()
    values: list[float] = []
    for window in (60, 120, 252):
        sample = data.iloc[-window:]
        if len(sample) < max(30, window // 2):
            continue
        q = float(sample.quantile(0.05))
        values.append(float(sample[sample <= q].mean()))
    return min(values) if values else -0.01


def gap_margin_cap(weights: np.ndarray, cfg: Config) -> float:
    shocks = np.asarray([-0.25, -0.12, -0.08])
    allowed = 1.0
    for state in LEVERAGE_STATES[LEVERAGE_STATES <= cfg.max_leverage + 1e-9]:
        risky_after = state * weights * (1.0 + shocks)
        equity_after = 1.0 + state * float(weights @ shocks)
        gross_after = float(np.abs(risky_after).sum())
        ratio = equity_after / gross_after if gross_after > 0 else 999.0
        if equity_after > 0 and ratio >= cfg.margin_min_ratio:
            allowed = float(state)
    return allowed


def nearest_allowed_capacity(capacity: float, cfg: Config) -> float:
    allowed = LEVERAGE_STATES[LEVERAGE_STATES <= cfg.max_leverage + 1e-12]
    eligible = allowed[allowed <= capacity + 1e-12]
    return float(eligible[-1]) if len(eligible) else 1.0


def dynamic_leverage_signals(data: pd.DataFrame, weight_signal: pd.DataFrame, cfg: Config) -> tuple[pd.Series, pd.DataFrame]:
    signal = pd.Series(1.0, index=data.index, dtype=float)
    rows: list[dict[str, Any]] = []
    current = 1.0
    up_counter = 0
    anchor_daily = (weight_signal * data[list(ENGINES)]).sum(axis=1)
    strategy_equity = 1.0
    peak = 1.0
    strategy_returns: list[float] = []
    for t, date in enumerate(data.index):
        if t > 0:
            realized = current * float(anchor_daily.iloc[t - 1]) - max(current - 1.0, 0.0) * cfg.financing_rate / ANNUALIZATION
            strategy_returns.append(realized)
            strategy_equity *= 1 + realized
            peak = max(peak, strategy_equity)
        if t < 252:
            signal.iloc[t] = current
            rows.append({"date": date, "unconstrained": 1.0, "cap_vol": 1.0, "cap_es": 1.0, "cap_corr": 1.0, "cap_gap_margin": 1.0, "cap_drawdown": 1.0, "final_capacity": 1.0, "selected": current, "binding": "warmup"})
            continue
        hist = data.iloc[: t + 1]
        w = weight_signal.iloc[t].to_numpy(float)
        anchor_hist = anchor_daily.iloc[: t + 1]
        v10_hist = data["V10"].iloc[: t + 1]
        anchor_vol = max([ewma_vol(anchor_hist, s) for s in (20, 60, 120) if math.isfinite(ewma_vol(anchor_hist, s))] or [1.0])
        v10_vol = max([ewma_vol(v10_hist, s) for s in (20, 60, 120) if math.isfinite(ewma_vol(v10_hist, s))] or [anchor_vol])
        cap_vol = v10_vol / max(anchor_vol, 1e-8)
        cap_es = abs(worst_es(v10_hist)) / max(abs(worst_es(anchor_hist)), 1e-8)
        stress_sigma = covariance_matrix(hist.iloc[-252:], cfg, stress=True)
        stress_port_vol = math.sqrt(max(float(w @ stress_sigma @ w) * ANNUALIZATION, 1e-12))
        cap_corr = v10_vol / max(stress_port_vol, 1e-8)
        cap_gap = gap_margin_cap(w, cfg)
        current_dd = strategy_equity / peak - 1.0
        v10_recent = (1 + v10_hist.iloc[-756:]).cumprod()
        v10_mdd = float((v10_recent / v10_recent.cummax() - 1).min())
        drawdown_limit = float(np.clip(abs(v10_mdd) - cfg.mdd_improvement_target, 0.20, 0.33))
        ten_day = anchor_hist.rolling(10).apply(lambda x: np.prod(1 + x) - 1, raw=True).dropna()
        empirical = abs(float(ten_day.iloc[-756:].quantile(0.01))) if len(ten_day) else 0.10
        parametric = 2.33 * anchor_vol * math.sqrt(10 / ANNUALIZATION)
        stress_loss = max(empirical, parametric, 0.01)
        remaining = max(0.0, drawdown_limit - abs(current_dd))
        cap_dd = float(np.clip(remaining / stress_loss, 1.0, cfg.max_leverage))
        caps = {"cap_vol": cap_vol, "cap_es": cap_es, "cap_corr": cap_corr, "cap_gap_margin": cap_gap, "cap_drawdown": cap_dd}
        raw = min(cfg.max_leverage, *caps.values())
        target = nearest_allowed_capacity(raw, cfg)
        if target < current - 1e-12:
            current = target
            up_counter = 0
        elif target > current + 1e-12:
            up_counter += 1
            if up_counter >= cfg.leverage_up_confirm_days:
                allowed = LEVERAGE_STATES[(LEVERAGE_STATES > current + 1e-12) & (LEVERAGE_STATES <= target + 1e-12)]
                if len(allowed):
                    current = float(allowed[0])
                up_counter = 0
        else:
            up_counter = 0
        signal.iloc[t] = current
        binding = min(caps, key=caps.get)
        rows.append({"date": date, "unconstrained": cfg.max_leverage, **caps, "final_capacity": raw, "selected": current, "binding": binding, "current_drawdown": current_dd, "drawdown_limit": drawdown_limit, "up_counter": up_counter})
    return signal, pd.DataFrame(rows).set_index("date")


def baseline_result(data: pd.DataFrame, cfg: Config) -> StrategyResult:
    r = data["V10"].copy()
    equity = (1 + r).cumprod()
    weights = pd.DataFrame(0.0, index=data.index, columns=ENGINES)
    weights["GROWTH_CRYPTO"] = 1.0
    leverage = pd.Series(1.0, index=data.index)
    zero = pd.Series(0.0, index=data.index)
    ledger = pd.DataFrame({"date": data.index, "net_return_nano": np.rint(r * 1e9).astype(np.int64), "actual_leverage_bp": 10000})
    return StrategyResult("V10_ALIGNED_COMMON_OOS", r, weights, leverage, zero, zero, equity, ledger)


def run_strategies(data: pd.DataFrame, cfg: Config) -> dict[str, StrategyResult]:
    anchor = anchor_signals(data, cfg)
    online = online_tilt_signals(data, anchor, cfg)
    uniform = pd.DataFrame(1 / 3, index=data.index, columns=ENGINES)
    one = pd.Series(1.0, index=data.index)
    results: dict[str, StrategyResult] = {"V10": baseline_result(data, cfg)}
    results["UNIFORM_1X"] = simulate_from_signals("UNIFORM_1X", data, uniform, one, cfg)
    results["ANCHOR_1X"] = simulate_from_signals("ANCHOR_1X", data, anchor, one, cfg)
    for lev in (1.30, 1.45, 1.60):
        results[f"STATIC_{int(lev*100):03d}"] = simulate_from_signals(f"STATIC_{int(lev*100):03d}", data, anchor, pd.Series(lev, index=data.index), cfg)
    dynamic_signal, capacities = dynamic_leverage_signals(data, anchor, cfg)
    d = simulate_from_signals("DYNAMIC_NO_TILT", data, anchor, dynamic_signal, cfg)
    d.capacities = capacities
    results[d.name] = d
    online_signal, online_capacities = dynamic_leverage_signals(data, online, cfg)
    h = simulate_from_signals("DYNAMIC_ONLINE_TILT", data, online, online_signal, cfg)
    h.capacities = online_capacities
    results[h.name] = h
    for source_name in ("DYNAMIC_NO_TILT", "DYNAMIC_ONLINE_TILT"):
        average = float(results[source_name].leverage.iloc[cfg.warmup_days:].mean())
        results[f"EQUAL_AVG_{source_name}"] = simulate_from_signals(f"EQUAL_AVG_{source_name}", data, anchor if source_name == "DYNAMIC_NO_TILT" else online, pd.Series(average, index=data.index), cfg)
    return results


def slice_oos(results: dict[str, StrategyResult], cfg: Config) -> dict[str, StrategyResult]:
    sliced = {}
    for name, r in results.items():
        sl = slice(cfg.warmup_days, None)
        capacities = r.capacities.iloc[sl] if r.capacities is not None else None
        sliced[name] = StrategyResult(name, r.returns.iloc[sl], r.weights.iloc[sl], r.leverage.iloc[sl], r.turnover.iloc[sl], r.financing.iloc[sl], r.equity.iloc[sl] / float(r.equity.iloc[cfg.warmup_days - 1]), r.ledger.iloc[sl].reset_index(drop=True), capacities)
    return sliced


def feasibility_screen(anchor_metrics: dict[str, float], v10_metrics: dict[str, float], cfg: Config) -> dict[str, Any]:
    mu_a, mu_b, f = anchor_metrics["cagr"], v10_metrics["cagr"], cfg.financing_rate
    required = (mu_b - f) / max(mu_a - f, 1e-8) if mu_a > f else float("inf")
    target_mdd = max(abs(v10_metrics["mdd"]) - cfg.mdd_improvement_target, 0.0)
    risk_cap = target_mdd / max(abs(anchor_metrics["mdd"]), 1e-8)
    upper = min(cfg.max_leverage, risk_cap)
    lower = max(1.0, required)
    return {"lambda_required": required, "lambda_risk_cap": risk_cap, "lambda_execution_cap": cfg.max_leverage, "feasible_lower": lower, "feasible_upper": upper, "feasible": bool(lower <= upper + 1e-12), "assumptions": "first-order CAGR and positively homogeneous drawdown diagnostic; not a guarantee"}


def hac_mean(values: pd.Series, lag: int) -> dict[str, float]:
    x = pd.Series(values).dropna().to_numpy(float)
    n = len(x)
    if n < 20:
        return {"mean": float(x.mean()) if n else 0.0, "t": 0.0, "p_one_sided": 1.0, "n": n}
    u = x - x.mean()
    var = float(u @ u / n)
    maximum = min(lag, n - 1)
    for k in range(1, maximum + 1):
        gamma = float(u[k:] @ u[:-k] / n)
        var += 2 * (1 - k / (maximum + 1)) * gamma
    se = math.sqrt(max(var, 0) / n)
    t = float(x.mean() / se) if se > 0 else 0.0
    return {"mean": float(x.mean()), "t": t, "p_one_sided": float(1 - _normal_cdf(t)), "n": n}


def paired_block_bootstrap(candidate: pd.Series, baseline: pd.Series, block: int, samples: int, seed: int) -> dict[str, float]:
    frame = pd.concat([candidate.rename("c"), baseline.rename("b")], axis=1).dropna()
    c, b = frame.c.to_numpy(float), frame.b.to_numpy(float)
    n = len(frame)
    rng = np.random.default_rng(seed + block)
    deltas = np.empty(samples)
    def s(x: np.ndarray) -> float:
        sd = x.std(ddof=1)
        return float(x.mean() / sd * math.sqrt(ANNUALIZATION)) if sd > 0 else 0.0
    for j in range(samples):
        idx: list[int] = []
        while len(idx) < n:
            start = int(rng.integers(0, max(1, n - block + 1)))
            idx.extend(range(start, min(start + block, n)))
        a = np.asarray(idx[:n])
        deltas[j] = s(c[a]) - s(b[a])
    observed = s(c) - s(b)
    return {"block": block, "samples": samples, "observed_delta_sharpe": observed, "lower_95": float(np.quantile(deltas, .025)), "upper_95": float(np.quantile(deltas, .975)), "p_nonpositive": float((np.sum(deltas <= 0) + 1) / (samples + 1))}


def dsr(returns: pd.Series, trials: int) -> dict[str, float]:
    r = pd.Series(returns).dropna()
    n = len(r)
    if n < 30 or r.std(ddof=1) <= 0:
        return {"dsr": 0.0, "observed_sharpe": 0.0, "trials": trials}
    sr = float(r.mean() / r.std(ddof=1))
    skew = float(r.skew())
    kurt = float(r.kurtosis() + 3)
    se = math.sqrt(max(1 - skew * sr + ((kurt - 1) / 4) * sr * sr, 1e-12) / (n - 1))
    expected_max = se * math.sqrt(2 * math.log(max(trials, 2)))
    z = (sr - expected_max) / se
    return {"dsr": _normal_cdf(z), "observed_sharpe": sr * math.sqrt(ANNUALIZATION), "expected_max_sharpe": expected_max * math.sqrt(ANNUALIZATION), "trials": trials, "skew": skew, "kurtosis": kurt}


def six_month_folds(results: dict[str, StrategyResult]) -> pd.DataFrame:
    rows = []
    for name, result in results.items():
        groups = result.returns.groupby([result.returns.index.year, (result.returns.index.month > 6).astype(int)])
        for (year, half), series in groups:
            if len(series) < 45:
                continue
            m = performance_metrics(series, result.leverage.reindex(series.index))
            rows.append({"strategy": name, "year": int(year), "half": int(half) + 1, **m})
    return pd.DataFrame(rows)


def controller_attribution(result: StrategyResult) -> pd.DataFrame:
    if result.capacities is None or result.capacities.empty:
        return pd.DataFrame()
    frame = result.capacities.copy()
    summary = frame.groupby("binding").agg(days=("selected", "size"), average_selected=("selected", "mean"), average_capacity=("final_capacity", "mean")).reset_index()
    summary["share"] = summary.days / summary.days.sum()
    return summary


def economic_gate(candidate: dict[str, float], baseline: dict[str, float]) -> dict[str, bool]:
    return {
        "sharpe_advantage": candidate["sharpe"] - baseline["sharpe"] >= 0.10,
        "cagr_advantage": candidate["cagr"] >= baseline["cagr"],
        "terminal_wealth_ratio": candidate["final_equity"] / baseline["final_equity"] >= 1.05,
        "mdd_improvement": candidate["mdd"] - baseline["mdd"] >= 0.08,
        "calmar_advantage": candidate["calmar"] - baseline["calmar"] >= 0.20,
        "cvar_improvement": candidate["cvar5"] - baseline["cvar5"] >= 0.15 * abs(baseline["cvar5"]),
        "gross_limit": candidate["maximum_gross"] <= 1.60 + 1e-9,
    }


def stress_tests(data: pd.DataFrame, base_cfg: Config) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    scenarios = []
    for cost in (17.0, 34.0, 51.0): scenarios.append(("cost_bps", cost, replace(base_cfg, cost_bps=cost)))
    for finance in (base_cfg.financing_rate, 0.08, 0.12): scenarios.append(("financing_rate", finance, replace(base_cfg, financing_rate=finance)))
    for delay in (2, 3, 4): scenarios.append(("delay", delay, replace(base_cfg, delay=delay)))
    for floor in (0.50, 0.75, 1.00): scenarios.append(("corr_floor", floor, replace(base_cfg, corr_floor=floor)))
    seen: set[tuple[str, float]] = set()
    for kind, value, cfg in scenarios:
        key = (kind, float(value))
        if key in seen: continue
        seen.add(key)
        out = slice_oos(run_strategies(data, cfg), cfg)
        for name in ("STATIC_160", "DYNAMIC_NO_TILT", "DYNAMIC_ONLINE_TILT"):
            m = performance_metrics(out[name].returns, out[name].leverage)
            rows.append({"scenario": kind, "value": value, "strategy": name, **m})
    years = sorted(set(data.index[base_cfg.warmup_days:].year))
    for year in years:
        reduced = data[data.index.year != year]
        if len(reduced) <= base_cfg.warmup_days + 100: continue
        cfg = replace(base_cfg, warmup_days=min(base_cfg.warmup_days, max(300, len(reduced)//3)))
        out = slice_oos(run_strategies(reduced, cfg), cfg)
        for name in ("V10", "STATIC_160"):
            m = performance_metrics(out[name].returns, out[name].leverage)
            rows.append({"scenario": "leave_one_year_out", "value": year, "strategy": name, **m})
    return pd.DataFrame(rows)


def final_status(metrics: dict[str, dict[str, float]], bootstrap: pd.DataFrame, gates: dict[str, dict[str, bool]]) -> dict[str, Any]:
    v10 = metrics["V10"]
    static = metrics["STATIC_160"]
    dynamic = metrics["DYNAMIC_NO_TILT"]
    online = metrics["DYNAMIC_ONLINE_TILT"]
    static_gate = all(gates["STATIC_160"].values())
    static_boot = bootstrap[bootstrap.comparison == "STATIC_160_vs_V10"]
    static_stat = bool(not static_boot.empty and (static_boot.lower_95 > 0).all())
    online_increment = online["sharpe"] - dynamic["sharpe"] >= .05 and online["final_equity"] / dynamic["final_equity"] >= 1.02 and online["mdd"] >= dynamic["mdd"]
    eq = metrics["EQUAL_AVG_DYNAMIC_NO_TILT"]
    dynamic_increment = dynamic["sharpe"] - eq["sharpe"] >= .05 and dynamic["final_equity"] / eq["final_equity"] >= .98 and dynamic["mdd"] >= eq["mdd"]
    if static_gate and static_stat:
        static_status = "HISTORICAL_STATIC_160_PARETO_PASS_NEEDS_NEW_OOS"
    elif static_gate:
        static_status = "STATIC_160_ECONOMIC_PASS_STATISTICAL_UNRESOLVED"
    else:
        static_status = "STATIC_160_REJECTED"
    if dynamic["cagr"] >= v10["cagr"] and all(gates["DYNAMIC_NO_TILT"].values()):
        dynamic_status = "DYNAMIC_RISK_BUDGET_PASS"
    elif dynamic["sharpe"] > v10["sharpe"] and dynamic["mdd"] > v10["mdd"]:
        dynamic_status = "RISK_ADJUSTED_IMPROVEMENT_RETURN_TRADEOFF"
    else:
        dynamic_status = "DYNAMIC_LEVERAGE_NO_INCREMENTAL_VALUE"
    return {"primary_status": static_status, "static_160_status": static_status, "dynamic_status": dynamic_status, "online_tilt_status": "ONLINE_TILT_PASS" if online_increment else "ONLINE_TILT_NO_INCREMENTAL_VALUE", "dynamic_controller_status": "DYNAMIC_CONTROLLER_INCREMENTAL_VALUE" if dynamic_increment else "DYNAMIC_LEVERAGE_NO_INCREMENTAL_VALUE", "visible_metrics": {"static_wealth_ratio": static["final_equity"] / v10["final_equity"], "online_vs_no_tilt_sharpe": online["sharpe"] - dynamic["sharpe"], "dynamic_vs_equal_average_sharpe": dynamic["sharpe"] - eq["sharpe"]}}


def save_result(result: StrategyResult, output: Path) -> None:
    result.returns.rename("net_return").to_csv(output / f"{result.name}_daily_returns.csv.gz", compression={"method":"gzip","compresslevel":9,"mtime":0})
    position = result.weights.copy()
    position["leverage"] = result.leverage
    position["turnover"] = result.turnover
    position["financing"] = result.financing
    position.to_csv(output / f"{result.name}_positions.csv.gz", compression={"method":"gzip","compresslevel":9,"mtime":0})
    result.ledger.to_csv(output / f"{result.name}_exact_ledger.csv.gz", index=False, compression={"method":"gzip","compresslevel":9,"mtime":0})
    if result.capacities is not None:
        result.capacities.to_csv(output / f"{result.name}_risk_capacity.csv.gz", compression={"method":"gzip","compresslevel":9,"mtime":0})


def build_manifest(directory: Path, name: str = "OUTPUT_MANIFEST.json") -> dict[str, Any]:
    files = []
    for path in sorted(directory.rglob("*")):
        if path.is_file() and path.name != name:
            files.append({"file": path.relative_to(directory).as_posix(), "bytes": path.stat().st_size, "sha256": sha256_file(path)})
    payload = {"version": VERSION, "count": len(files), "files": files}
    write_json(directory / name, payload)
    return payload


def report_markdown(metrics: dict[str, dict[str, float]], feasibility: dict[str, Any], status: dict[str, Any], gates: dict[str, dict[str, bool]], failed_tests: str | None = None) -> str:
    lines = ["# V23.1 Final Pareto Audit", "", f"**Primary status: `{status['primary_status']}`**", "", "## Strategy performance", "", "| Strategy | Sharpe | CAGR | MDD | Calmar | CVaR5 | Final | Avg gross |", "|---|---:|---:|---:|---:|---:|---:|---:|"]
    order = ["V10","UNIFORM_1X","ANCHOR_1X","STATIC_130","STATIC_145","STATIC_160","DYNAMIC_NO_TILT","DYNAMIC_ONLINE_TILT","EQUAL_AVG_DYNAMIC_NO_TILT","EQUAL_AVG_DYNAMIC_ONLINE_TILT"]
    for name in order:
        m = metrics[name]
        lines.append(f"| {name} | {m['sharpe']:.3f} | {m['cagr']*100:.2f}% | {m['mdd']*100:.2f}% | {m['calmar']:.3f} | {m['cvar5']*100:.3f}% | {m['final_equity']:.3f}x | {m['average_gross']:.3f} |")
    lines += ["", "## Feasibility screen", "", f"- Required leverage: {feasibility['lambda_required']:.3f}", f"- Risk leverage cap: {feasibility['lambda_risk_cap']:.3f}", f"- Execution cap: {feasibility['lambda_execution_cap']:.3f}", f"- Feasible interval: [{feasibility['feasible_lower']:.3f}, {feasibility['feasible_upper']:.3f}]", f"- Non-empty: {feasibility['feasible']}", "", "## Strategy-specific decisions", "", f"- Static 1.60: `{status['static_160_status']}`", f"- Dynamic controller: `{status['dynamic_controller_status']}`", f"- Online tilt: `{status['online_tilt_status']}`", "", "## Static 1.60 economic gates", ""]
    for key, passed in gates["STATIC_160"].items():
        lines.append(f"- {key}: {'PASS' if passed else 'FAIL'}")
    if failed_tests:
        lines += ["", "## Test-suite note", "", failed_tests]
    lines += ["", "## Interpretation", "", "A static 1.60 result is a historical candidate only when it was preregistered and all economic, statistical, provenance and stress gates pass. A dynamic or online method is rejected when it fails its simpler equal-average-risk or no-tilt comparator."]
    return "\n".join(lines) + "\n"


def run_lab(input_path: Path, output: Path, cfg: Config, prior_trials: int = 35000) -> dict[str, Any]:
    output.mkdir(parents=True, exist_ok=True)
    data = canonicalize_input(input_path)
    full = run_strategies(data, cfg)
    results = slice_oos(full, cfg)
    metrics = {name: performance_metrics(r.returns, r.leverage) for name, r in results.items()}
    metrics_frame = pd.DataFrame([{"strategy": k, **v} for k, v in metrics.items()])
    metrics_frame.to_csv(output / "strategy_summary.csv", index=False)
    feasibility = feasibility_screen(metrics["ANCHOR_1X"], metrics["V10"], cfg)
    write_json(output / "FEASIBILITY_SCREEN.json", feasibility)
    gates = {name: economic_gate(metrics[name], metrics["V10"]) for name in ("STATIC_160", "DYNAMIC_NO_TILT", "DYNAMIC_ONLINE_TILT")}
    write_json(output / "ECONOMIC_GATES.json", gates)
    bootstrap_rows = []
    comparisons = (("STATIC_160","V10"),("DYNAMIC_NO_TILT","V10"),("DYNAMIC_ONLINE_TILT","V10"),("DYNAMIC_ONLINE_TILT","DYNAMIC_NO_TILT"),("DYNAMIC_NO_TILT","EQUAL_AVG_DYNAMIC_NO_TILT"))
    for candidate, baseline in comparisons:
        for block in (30,60,120):
            row = paired_block_bootstrap(results[candidate].returns, results[baseline].returns, block, cfg.bootstrap_samples, cfg.random_seed)
            row["comparison"] = f"{candidate}_vs_{baseline}"
            bootstrap_rows.append(row)
    bootstrap = pd.DataFrame(bootstrap_rows)
    bootstrap.to_csv(output / "bootstrap_results.csv", index=False)
    hac_rows = []
    for candidate, baseline in comparisons:
        active = results[candidate].returns - results[baseline].returns
        for lag in (20,60,120):
            hac_rows.append({"comparison": f"{candidate}_vs_{baseline}", "lag": lag, **hac_mean(active, lag)})
    pd.DataFrame(hac_rows).to_csv(output / "hac_results.csv", index=False)
    dsr_payload = {name: dsr(r.returns, prior_trials) for name, r in results.items()}
    write_json(output / "dsr_results.json", dsr_payload)
    folds = six_month_folds(results)
    folds.to_csv(output / "fold_metrics.csv", index=False)
    stress = stress_tests(data, cfg)
    stress.to_csv(output / "stress_tests.csv", index=False)
    for name, result in results.items():
        save_result(result, output)
    for name in ("DYNAMIC_NO_TILT","DYNAMIC_ONLINE_TILT"):
        controller_attribution(results[name]).to_csv(output / f"{name}_controller_attribution.csv", index=False)
    status = final_status(metrics, bootstrap, gates)
    baseline_identity = {"aligned_input": str(input_path.resolve()), "aligned_input_sha256": sha256_file(input_path), "aligned_start": data.index[cfg.warmup_days], "aligned_end": data.index[-1], "aligned_rows": len(data) - cfg.warmup_days, "v10_aligned_ledger_sha256": sha256_frame(results["V10"].ledger), "note": "This does not assert equality to an external full-history V10 ledger unless supplied and checked separately."}
    write_json(output / "BASELINE_IDENTITY.json", baseline_identity)
    payload = {"version": VERSION, "status": status, "config": asdict(cfg), "input": baseline_identity, "metrics": metrics, "feasibility": feasibility, "economic_gates": gates, "test_requirement": "42 passed, 0 failed, 0 skipped before authority"}
    write_json(output / "FINAL_GATE.json", payload)
    (output / "FINAL_REPORT.md").write_text(report_markdown(metrics, feasibility, status, gates), encoding="utf-8")
    build_manifest(output)
    return payload


def verify_results(output: Path) -> dict[str, Any]:
    required = ["FINAL_GATE.json","FINAL_REPORT.md","FEASIBILITY_SCREEN.json","strategy_summary.csv","bootstrap_results.csv","hac_results.csv","stress_tests.csv","OUTPUT_MANIFEST.json"]
    missing = [name for name in required if not (output / name).exists()]
    if missing:
        raise RuntimeError(f"Missing result files: {missing}")
    manifest = json.loads((output / "OUTPUT_MANIFEST.json").read_text())
    failures = []
    for item in manifest["files"]:
        path = output / item["file"]
        if not path.exists() or sha256_file(path) != item["sha256"]:
            failures.append(item["file"])
    if failures:
        raise RuntimeError(f"Result hash failures: {failures}")
    gate = json.loads((output / "FINAL_GATE.json").read_text())
    return {"status": "PASS", "files": manifest["count"], "primary_status": gate["status"]["primary_status"]}


def build_handoff(root: Path, output: Path) -> Path:
    results = root / "results"
    verify_results(results)
    files: list[Path] = []
    for base in (results, root / "src", root / "tests"):
        if base.exists(): files.extend(p for p in base.rglob("*") if p.is_file() and "__pycache__" not in p.parts)
    for name in ("README.md","requirements.txt","RUN_EVERYTHING.command","VERIFY_PACKAGE.command","COLLECT_ZCODE_HANDOFF.command","PROTOCOL.json"):
        p = root / name
        if p.exists(): files.append(p)
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for path in sorted(set(files), key=lambda p: p.relative_to(root).as_posix()):
            info = zipfile.ZipInfo(path.relative_to(root).as_posix(), (1980,1,1,0,0,0))
            info.create_system = 3
            info.external_attr = (0o755 if path.suffix == ".command" else 0o644) << 16
            zf.writestr(info, path.read_bytes())
    return output


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run")
    run.add_argument("--root", type=Path, default=Path("."))
    run.add_argument("--input", type=Path)
    run.add_argument("--output", type=Path, default=Path("results"))
    run.add_argument("--bootstrap-samples", type=int, default=20000)
    run.add_argument("--prior-trials", type=int, default=35000)
    verify = sub.add_parser("verify")
    verify.add_argument("--output", type=Path, default=Path("results"))
    package = sub.add_parser("package")
    package.add_argument("--root", type=Path, default=Path("."))
    package.add_argument("--output", type=Path, default=Path("runtime/V23_1_ZCode_Handoff.zip"))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.command == "run":
        root = args.root.resolve()
        path = discover_input(root, args.input)
        cfg = Config(bootstrap_samples=args.bootstrap_samples)
        payload = run_lab(path, (root / args.output).resolve() if not args.output.is_absolute() else args.output, cfg, args.prior_trials)
        print(json.dumps({"status": payload["status"], "output": str(args.output), "input": str(path)}, default=json_default, indent=2))
    elif args.command == "verify":
        print(json.dumps(verify_results(args.output.resolve()), indent=2))
    elif args.command == "package":
        root = args.root.resolve()
        out = args.output if args.output.is_absolute() else root / args.output
        path = build_handoff(root, out)
        print(json.dumps({"path": str(path), "bytes": path.stat().st_size, "sha256": sha256_file(path)}, indent=2))


if __name__ == "__main__":
    main()

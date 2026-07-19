#!/usr/bin/env python3
"""V24 Portable Diversifier Overlay research core.

The immutable primary hypothesis keeps the aligned V10 core at 100% and adds
30% Equity Trend plus 30% Gold Trend, financed by a 60% cash borrowing sleeve.
Dynamic and online variants are secondary diagnostics and may only change the
overlay. They can never reduce or lever the V10 core.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import shutil
import statistics
import tempfile
import zipfile
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Any, Iterable, Sequence

import numpy as np
import pandas as pd

VERSION = "24.0.0"
ANNUALIZATION = 365.25
RISK_COLUMNS = ("V10", "EQUITY_TREND", "GOLD_TREND")
REQUIRED_COLUMNS = ("GROWTH_CRYPTO", "EQUITY_TREND", "GOLD_TREND", "V10")
OVERLAY_STATES = np.asarray([0.00, 0.15, 0.30, 0.45, 0.60], dtype=float)


@dataclass(frozen=True)
class Config:
    delay: int = 2
    warmup_days: int = 756
    one_way_cost_bps: float = 17.0
    borrow_spread_annual: float = 0.05
    max_overlay: float = 0.60
    static_equity_overlay: float = 0.30
    static_gold_overlay: float = 0.30
    up_confirm_days: int = 10
    corr_floor: float = 0.75
    shrinkage: float = 0.25
    online_split_min: float = 0.25
    online_split_max: float = 0.75
    online_eta_scale: float = 0.35
    target_mdd_improvement: float = 0.08
    risk_tolerance_ratio: float = 1.05
    margin_min_ratio: float = 0.35
    trials_for_dsr: int = 250
    random_seed: int = 20260719
    bootstrap_samples: int = 10000

    def validate(self) -> None:
        if self.delay < 0:
            raise ValueError("delay must be non-negative")
        if self.warmup_days < 252:
            raise ValueError("warmup_days must be at least 252")
        if not math.isclose(self.static_equity_overlay + self.static_gold_overlay, self.max_overlay, abs_tol=1e-12):
            raise ValueError("static overlays must sum to max_overlay")
        if self.max_overlay > 0.60 + 1e-12:
            raise ValueError("portable overlay gross cap is 0.60")
        if not 0 <= self.online_split_min <= self.online_split_max <= 1:
            raise ValueError("invalid online split bounds")


@dataclass
class StrategyResult:
    name: str
    returns: pd.Series
    weights: pd.DataFrame
    turnover: pd.Series
    financing: pd.Series
    equity: pd.Series
    ledger: pd.DataFrame
    contributions: pd.DataFrame
    diagnostics: pd.DataFrame | None = None


@dataclass
class DynamicState:
    executed_overlay: float = 0.0
    executed_split: float = 0.5
    signal_overlay: float = 0.0
    signal_split: float = 0.5
    pending_up_days: int = 0
    online_grad_sq: float = 1e-12
    equity: float = 1.0
    high_water: float = 1.0


def json_default(value: Any) -> Any:
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.floating):
        x = float(value)
        return x if math.isfinite(x) else None
    if isinstance(value, np.bool_):
        return bool(value)
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, set):
        return sorted(value)
    raise TypeError(type(value).__name__)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, default=json_default, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def _find_column(frame: pd.DataFrame, aliases: Sequence[str]) -> str | None:
    lookup = {str(c).strip().lower(): str(c) for c in frame.columns}
    for alias in aliases:
        if alias.lower() in lookup:
            return lookup[alias.lower()]
    return None


def _read_table(path: Path) -> pd.DataFrame:
    lower = path.name.lower()
    if lower.endswith(".csv.gz"):
        return pd.read_csv(path, compression="gzip", low_memory=False)
    if lower.endswith(".csv"):
        return pd.read_csv(path, low_memory=False)
    if lower.endswith(".parquet"):
        return pd.read_parquet(path)
    raise ValueError(f"unsupported input format: {path}")


def normalize_date_frame(frame: pd.DataFrame) -> pd.DataFrame:
    output = frame.copy()
    date_col = _find_column(output, ("date", "datetime", "timestamp", "time", "open_time", "day"))
    if date_col is None:
        if not isinstance(output.index, pd.DatetimeIndex):
            raise ValueError("no date column")
        idx = pd.to_datetime(output.index, utc=True, errors="coerce").normalize()
        output.index = idx
        output.index.name = "date"
    else:
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
        output = output.dropna(subset=["date"]).set_index("date")
    output = output[~output.index.duplicated(keep="last")].sort_index()
    return output


def canonicalize_input(path: Path) -> pd.DataFrame:
    raw = normalize_date_frame(_read_table(path))
    aliases = {
        "GROWTH_CRYPTO": ("growth_crypto", "growth", "crypto_growth", "crypto_momentum"),
        "EQUITY_TREND": ("equity_trend", "equity", "spy_qqq", "equity_engine"),
        "GOLD_TREND": ("gold_trend", "gold", "gld", "gold_engine"),
        "V10": ("v10", "baseline_v10", "crypto_v10", "baseline"),
        "CASH": ("cash", "cash_return", "risk_free", "bil", "sgov"),
    }
    out = pd.DataFrame(index=raw.index)
    for canonical, names in aliases.items():
        col = _find_column(raw, names)
        if col is None:
            if canonical == "CASH":
                out[canonical] = 0.0
                continue
            raise ValueError(f"missing required column {canonical}; available={list(raw.columns)}")
        out[canonical] = pd.to_numeric(raw[col], errors="coerce")
    out = out.replace([np.inf, -np.inf], np.nan).dropna(subset=list(REQUIRED_COLUMNS))
    out["CASH"] = out["CASH"].fillna(0.0)
    if len(out) < 900:
        raise ValueError(f"need at least 900 aligned rows; got {len(out)}")
    if (out[list(REQUIRED_COLUMNS)].abs() > 0.95).any().any():
        raise ValueError("input appears to contain prices or whole percentages, not decimal daily returns")
    return out.astype(float)


def discover_input(root: Path, explicit: Path | None = None) -> Path:
    if explicit is not None:
        explicit = explicit.expanduser().resolve()
        if not explicit.exists():
            raise FileNotFoundError(explicit)
        return explicit
    env = os.getenv("ENGINE_RETURNS_FILE")
    if env and Path(env).expanduser().exists():
        return Path(env).expanduser().resolve()
    patterns = ("engine_returns.csv.gz", "engine_returns.csv", "daily_engine_returns.csv.gz", "engine_daily_returns.csv.gz")
    roots = [root, Path.home() / "Downloads", Path.home() / "Documents/ZCode/Autotrade"]
    candidates: list[Path] = []
    for base in roots:
        if not base.exists():
            continue
        for pattern in patterns:
            candidates.extend(base.rglob(pattern))
    if candidates:
        return max(candidates, key=lambda p: p.stat().st_mtime).resolve()
    raise FileNotFoundError("set ENGINE_RETURNS_FILE or pass --input engine_returns.csv[.gz]")


def performance_metrics(returns: pd.Series, risky_gross: pd.Series | None = None) -> dict[str, Any]:
    r = pd.Series(returns, dtype=float).dropna()
    if r.empty:
        raise ValueError("empty return series")
    if (r <= -1.0).any():
        raise ValueError("portfolio return reached or crossed -100%")
    equity = (1.0 + r).cumprod()
    drawdown = equity / equity.cummax() - 1.0
    std = float(r.std(ddof=1))
    sharpe = float(r.mean() / std * math.sqrt(ANNUALIZATION)) if std > 0 else 0.0
    calendar_years = max((r.index[-1] - r.index[0]).days / ANNUALIZATION, len(r) / ANNUALIZATION, 1 / ANNUALIZATION)
    final = float(equity.iloc[-1])
    cagr = float(final ** (1.0 / calendar_years) - 1.0)
    mdd = float(drawdown.min())
    q = float(r.quantile(0.05))
    cvar = float(r[r <= q].mean())
    gross = pd.Series(1.0, index=r.index) if risky_gross is None else pd.Series(risky_gross, dtype=float).reindex(r.index).ffill().fillna(1.0)
    return {
        "observations": int(len(r)),
        "start": r.index[0],
        "end": r.index[-1],
        "sharpe": sharpe,
        "cagr": cagr,
        "mdd": mdd,
        "calmar": float(cagr / abs(mdd)) if mdd < 0 else 0.0,
        "cvar5": cvar,
        "final_equity": final,
        "annual_volatility": std * math.sqrt(ANNUALIZATION),
        "average_risky_gross": float(gross.mean()),
        "maximum_risky_gross": float(gross.max()),
        "liquidations": int((r <= -1.0).sum()),
    }


def bounded_simplex(values: np.ndarray, lower: np.ndarray | float, upper: np.ndarray | float, total: float = 1.0) -> np.ndarray:
    v = np.asarray(values, dtype=float)
    lo = np.broadcast_to(np.asarray(lower, dtype=float), v.shape)
    hi = np.broadcast_to(np.asarray(upper, dtype=float), v.shape)
    if lo.sum() > total + 1e-12 or hi.sum() < total - 1e-12:
        raise ValueError("infeasible simplex bounds")
    left = float(np.min(v - hi)) - abs(total) - 1.0
    right = float(np.max(v - lo)) + abs(total) + 1.0
    for _ in range(120):
        mid = (left + right) / 2.0
        x = np.clip(v - mid, lo, hi)
        if float(x.sum()) > total:
            left = mid
        else:
            right = mid
    x = np.clip(v - (left + right) / 2.0, lo, hi)
    residual = total - float(x.sum())
    if abs(residual) > 1e-11:
        order = np.argsort(-(hi - x) if residual > 0 else -(x - lo))
        for i in order:
            room = float(hi[i] - x[i]) if residual > 0 else float(x[i] - lo[i])
            move = min(abs(residual), max(room, 0.0))
            x[i] += move if residual > 0 else -move
            residual += -move if residual > 0 else move
            if abs(residual) <= 1e-12:
                break
    return x


def _safe_cov(frame: pd.DataFrame) -> np.ndarray:
    x = frame.astype(float).replace([np.inf, -np.inf], np.nan).dropna(how="any")
    if len(x) < 3:
        return np.eye(frame.shape[1]) * 1e-8
    cov = np.asarray(x.cov(), dtype=float)
    cov = np.nan_to_num(cov, nan=0.0, posinf=0.0, neginf=0.0)
    cov = (cov + cov.T) / 2.0
    vals, vecs = np.linalg.eigh(cov)
    vals = np.maximum(vals, 1e-12)
    return (vecs * vals) @ vecs.T


def _stressed_cov(frame: pd.DataFrame, corr_floor: float, shrinkage: float) -> np.ndarray:
    x = frame.astype(float).replace([np.inf, -np.inf], np.nan).dropna(how="any")
    if len(x) < 3:
        return np.eye(frame.shape[1]) * 1e-8
    vols = np.asarray(x.std(ddof=1), dtype=float)
    vols = np.maximum(np.nan_to_num(vols, nan=1e-6), 1e-6)
    corr = np.asarray(x.corr(), dtype=float)
    corr = np.nan_to_num(corr, nan=0.0)
    corr = (1.0 - shrinkage) * corr + shrinkage * np.eye(len(vols))
    for i in range(len(vols)):
        corr[i, i] = 1.0
        for j in range(i):
            value = max(float(corr[i, j]), corr_floor)
            corr[i, j] = corr[j, i] = value
    vals, vecs = np.linalg.eigh((corr + corr.T) / 2.0)
    vals = np.maximum(vals, 1e-9)
    corr_psd = (vecs * vals) @ vecs.T
    scale = np.sqrt(np.maximum(np.diag(corr_psd), 1e-12))
    corr_psd = corr_psd / np.outer(scale, scale)
    return np.outer(vols, vols) * corr_psd


def _annual_vol(series: pd.Series) -> float:
    s = pd.Series(series, dtype=float).dropna()
    return float(s.std(ddof=1) * math.sqrt(ANNUALIZATION)) if len(s) > 1 else float("inf")


def _expected_shortfall(series: pd.Series, alpha: float = 0.05) -> float:
    s = pd.Series(series, dtype=float).dropna()
    if s.empty:
        return float("inf")
    q = float(s.quantile(alpha))
    tail = s[s <= q]
    return abs(float(tail.mean())) if len(tail) else abs(q)


def _robust_risk(history: pd.DataFrame, equity_weight: float, gold_weight: float, cfg: Config) -> dict[str, float]:
    q = float(equity_weight + gold_weight)
    spread_daily = cfg.borrow_spread_annual / ANNUALIZATION
    candidate = history["V10"] + equity_weight * history["EQUITY_TREND"] + gold_weight * history["GOLD_TREND"] - q * history["CASH"] - q * spread_daily
    baseline = history["V10"]
    vols = [_annual_vol(candidate.tail(n)) for n in (20, 60, 120)]
    base_vols = [_annual_vol(baseline.tail(n)) for n in (20, 60, 120)]
    es = [_expected_shortfall(candidate.tail(n)) for n in (60, 120, 252)]
    base_es = [_expected_shortfall(baseline.tail(n)) for n in (60, 120, 252)]
    recent = history[list(RISK_COLUMNS)].tail(120)
    cov = _stressed_cov(recent, cfg.corr_floor, cfg.shrinkage)
    weights = np.asarray([1.0, equity_weight, gold_weight], dtype=float)
    stress_vol = float(math.sqrt(max(float(weights @ cov @ weights), 0.0)) * math.sqrt(ANNUALIZATION))
    baseline_stress_vol = float(math.sqrt(max(float(cov[0, 0]), 0.0)) * math.sqrt(ANNUALIZATION))
    return {
        "candidate_vol": max(vols),
        "baseline_vol": max(base_vols),
        "candidate_es": max(es),
        "baseline_es": max(base_es),
        "stress_vol": stress_vol,
        "baseline_stress_vol": baseline_stress_vol,
    }


def _gap_maintenance(equity_weight: float, gold_weight: float) -> tuple[float, float]:
    q = equity_weight + gold_weight
    shock_loss = 0.25 + 0.12 * equity_weight + 0.08 * gold_weight
    post_equity = 1.0 - shock_loss
    risky_gross = 1.0 + q
    maintenance = post_equity / risky_gross if risky_gross > 0 else -math.inf
    return shock_loss, maintenance


def _exact_ppm_weights(core: float, equity: float, gold: float, cash: float) -> tuple[int, int, int, int]:
    raw = np.asarray([core, equity, gold, cash], dtype=float) * 1_000_000.0
    rounded = np.floor(raw).astype(np.int64)
    target = 1_000_000
    residual = int(target - int(rounded.sum()))
    fractions = raw - np.floor(raw)
    if residual > 0:
        order = np.argsort(-fractions)
        for i in order[:residual]:
            rounded[i] += 1
    elif residual < 0:
        order = np.argsort(fractions)
        for i in order[: abs(residual)]:
            rounded[i] -= 1
    if int(rounded.sum()) != target:
        rounded[0] += target - int(rounded.sum())
    return tuple(int(x) for x in rounded)


def _make_ledger(index: pd.Index, weights: pd.DataFrame, turnover: pd.Series, financing: pd.Series, returns: pd.Series) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for date in index:
        w = weights.loc[date]
        core, eq, gold, cash = _exact_ppm_weights(float(w["V10"]), float(w["EQUITY_TREND"]), float(w["GOLD_TREND"]), float(w["CASH"]))
        rows.append({
            "date": date,
            "v10_ppm": core,
            "equity_ppm": eq,
            "gold_ppm": gold,
            "cash_ppm": cash,
            "net_ppm": core + eq + gold + cash,
            "risky_gross_ppm": abs(core) + abs(eq) + abs(gold),
            "turnover_ppm": int(round(float(turnover.loc[date]) * 1_000_000)),
            "financing_nano": int(round(float(financing.loc[date]) * 1_000_000_000)),
            "return_nano": int(round(float(returns.loc[date]) * 1_000_000_000)),
        })
    ledger = pd.DataFrame(rows)
    payload = ledger.to_csv(index=False, lineterminator="\n").encode("utf-8")
    ledger.attrs["sha256"] = sha256_bytes(payload)
    return ledger


def _simulate_positions(data: pd.DataFrame, weights: pd.DataFrame, cfg: Config, name: str) -> StrategyResult:
    idx = weights.index
    returns_data = data.reindex(idx)
    weights = weights.astype(float).copy()
    if not np.allclose(weights["V10"].to_numpy(), 1.0, atol=1e-12):
        raise ValueError("portable strategies must keep V10 core at exactly 100%")
    if not np.allclose(weights.sum(axis=1).to_numpy(), 1.0, atol=1e-10):
        raise ValueError("portfolio net weights must equal one")
    overlay = weights["EQUITY_TREND"] + weights["GOLD_TREND"]
    if (overlay < -1e-12).any() or (overlay > cfg.max_overlay + 1e-12).any():
        raise ValueError("overlay outside protocol bounds")
    risky = weights[["V10", "EQUITY_TREND", "GOLD_TREND"]]
    turnover = risky.diff().abs().sum(axis=1)
    turnover.iloc[0] = abs(float(risky.iloc[0]["EQUITY_TREND"])) + abs(float(risky.iloc[0]["GOLD_TREND"]))
    cost = turnover * cfg.one_way_cost_bps / 10_000.0
    financing = overlay * (returns_data["CASH"] + cfg.borrow_spread_annual / ANNUALIZATION)
    core_contrib = returns_data["V10"]
    eq_contrib = weights["EQUITY_TREND"] * returns_data["EQUITY_TREND"]
    gold_contrib = weights["GOLD_TREND"] * returns_data["GOLD_TREND"]
    portfolio = core_contrib + eq_contrib + gold_contrib - financing - cost
    if (portfolio <= -1).any():
        raise ValueError(f"{name} liquidated")
    equity = (1.0 + portfolio).cumprod()
    contributions = pd.DataFrame({
        "V10_CORE": core_contrib,
        "EQUITY_OVERLAY": eq_contrib,
        "GOLD_OVERLAY": gold_contrib,
        "FINANCING": -financing,
        "TURNOVER_COST": -cost,
        "TOTAL": portfolio,
    }, index=idx)
    ledger = _make_ledger(idx, weights, turnover, financing, portfolio)
    return StrategyResult(name, portfolio, weights, turnover, financing, equity, ledger, contributions)


def common_oos(data: pd.DataFrame, cfg: Config) -> pd.DataFrame:
    cfg.validate()
    start = cfg.warmup_days + cfg.delay
    if len(data) - start < 120:
        raise ValueError("insufficient common OOS after warmup")
    return data.iloc[start:].copy()


def run_v10(data: pd.DataFrame, cfg: Config) -> StrategyResult:
    oos = common_oos(data, cfg)
    weights = pd.DataFrame({"V10": 1.0, "EQUITY_TREND": 0.0, "GOLD_TREND": 0.0, "CASH": 0.0}, index=oos.index)
    return _simulate_positions(data, weights, cfg, "V10_ALIGNED_COMMON_OOS")


def run_static_portable(data: pd.DataFrame, cfg: Config, equity_overlay: float | None = None, gold_overlay: float | None = None, name: str = "STATIC_PORTABLE_30_30") -> StrategyResult:
    eq = cfg.static_equity_overlay if equity_overlay is None else float(equity_overlay)
    gold = cfg.static_gold_overlay if gold_overlay is None else float(gold_overlay)
    if eq < 0 or gold < 0 or eq + gold > cfg.max_overlay + 1e-12:
        raise ValueError("invalid static overlay")
    oos = common_oos(data, cfg)
    weights = pd.DataFrame({"V10": 1.0, "EQUITY_TREND": eq, "GOLD_TREND": gold, "CASH": -(eq + gold)}, index=oos.index)
    return _simulate_positions(data, weights, cfg, name)


def run_uniform_diluted(data: pd.DataFrame, cfg: Config) -> StrategyResult:
    oos = common_oos(data, cfg)
    weights = pd.DataFrame({"V10": 1 / 3, "EQUITY_TREND": 1 / 3, "GOLD_TREND": 1 / 3, "CASH": 0.0}, index=oos.index)
    # This diagnostic intentionally violates portable-core invariance, so simulate directly.
    risky = weights[["V10", "EQUITY_TREND", "GOLD_TREND"]]
    turnover = risky.diff().abs().sum(axis=1).fillna(1.0)
    cost = turnover * cfg.one_way_cost_bps / 10_000.0
    r = (risky * data.reindex(oos.index)[list(RISK_COLUMNS)]).sum(axis=1) - cost
    equity = (1 + r).cumprod()
    financing = pd.Series(0.0, index=oos.index)
    contributions = pd.DataFrame({
        "V10_CORE": weights["V10"] * data.reindex(oos.index)["V10"],
        "EQUITY_OVERLAY": weights["EQUITY_TREND"] * data.reindex(oos.index)["EQUITY_TREND"],
        "GOLD_OVERLAY": weights["GOLD_TREND"] * data.reindex(oos.index)["GOLD_TREND"],
        "FINANCING": 0.0,
        "TURNOVER_COST": -cost,
        "TOTAL": r,
    }, index=oos.index)
    ledger = _make_ledger(oos.index, weights, turnover, financing, r)
    return StrategyResult("UNIFORM_DILUTED_1X", r, weights, turnover, financing, equity, ledger, contributions)


def causal_inverse_vol_anchor(data: pd.DataFrame, cfg: Config) -> StrategyResult:
    signals = pd.DataFrame(index=data.index, columns=list(RISK_COLUMNS), dtype=float)
    for i in range(cfg.warmup_days, len(data)):
        hist = data.iloc[: i + 1]
        vols = []
        for col in RISK_COLUMNS:
            v = max(_annual_vol(hist[col].tail(n)) for n in (20, 60, 120))
            vols.append(max(v, 1e-6))
        raw = 1.0 / np.asarray(vols)
        raw /= raw.sum()
        signals.iloc[i] = bounded_simplex(raw, 0.20, 0.50, 1.0)
    executed = signals.shift(cfg.delay).dropna()
    executed.columns = list(RISK_COLUMNS)
    oos_idx = common_oos(data, cfg).index.intersection(executed.index)
    executed = executed.reindex(oos_idx)
    weights = pd.DataFrame({
        "V10": executed["V10"],
        "EQUITY_TREND": executed["EQUITY_TREND"],
        "GOLD_TREND": executed["GOLD_TREND"],
        "CASH": 0.0,
    }, index=oos_idx)
    risky = weights[list(RISK_COLUMNS)]
    turnover = risky.diff().abs().sum(axis=1)
    turnover.iloc[0] = float(risky.iloc[0].abs().sum())
    cost = turnover * cfg.one_way_cost_bps / 10_000.0
    returns_data = data.reindex(oos_idx)
    r = (risky * returns_data[list(RISK_COLUMNS)]).sum(axis=1) - cost
    financing = pd.Series(0.0, index=oos_idx)
    equity = (1 + r).cumprod()
    contributions = pd.DataFrame({
        "V10_CORE": risky["V10"] * returns_data["V10"],
        "EQUITY_OVERLAY": risky["EQUITY_TREND"] * returns_data["EQUITY_TREND"],
        "GOLD_OVERLAY": risky["GOLD_TREND"] * returns_data["GOLD_TREND"],
        "FINANCING": 0.0,
        "TURNOVER_COST": -cost,
        "TOTAL": r,
    }, index=oos_idx)
    ledger = _make_ledger(oos_idx, weights, turnover, financing, r)
    return StrategyResult("INVERSE_VOL_DILUTED_1X", r, weights, turnover, financing, equity, ledger, contributions)


def _capacity_for_split(history: pd.DataFrame, current_drawdown: float, split: float, cfg: Config) -> tuple[float, dict[str, float]]:
    allowed = 0.0
    selected_diag: dict[str, float] = {}
    for q in OVERLAY_STATES:
        if q > cfg.max_overlay + 1e-12:
            continue
        eq = q * split
        gold = q * (1.0 - split)
        risk = _robust_risk(history, eq, gold, cfg)
        shock_loss, maintenance = _gap_maintenance(eq, gold)
        vol_ok = risk["candidate_vol"] <= risk["baseline_vol"] * cfg.risk_tolerance_ratio + 1e-12
        es_ok = risk["candidate_es"] <= risk["baseline_es"] * cfg.risk_tolerance_ratio + 1e-12
        corr_ok = risk["stress_vol"] <= risk["baseline_stress_vol"] * cfg.risk_tolerance_ratio + 1e-12
        projected_loss = min(max(3.0 * risk["candidate_es"], 0.0), 0.25)
        projected_dd = (1.0 + current_drawdown) * (1.0 - projected_loss) - 1.0
        dd_limit = -(0.37 - cfg.target_mdd_improvement)
        dd_ok = projected_dd >= dd_limit - 1e-12
        margin_ok = maintenance >= cfg.margin_min_ratio
        if all((vol_ok, es_ok, corr_ok, dd_ok, margin_ok)):
            allowed = float(q)
            selected_diag = {
                **risk,
                "shock_loss": shock_loss,
                "maintenance_ratio": maintenance,
                "projected_drawdown": projected_dd,
                "vol_ok": float(vol_ok),
                "es_ok": float(es_ok),
                "corr_ok": float(corr_ok),
                "dd_ok": float(dd_ok),
                "margin_ok": float(margin_ok),
            }
    if not selected_diag:
        risk = _robust_risk(history, 0.0, 0.0, cfg)
        shock_loss, maintenance = _gap_maintenance(0.0, 0.0)
        selected_diag = {**risk, "shock_loss": shock_loss, "maintenance_ratio": maintenance, "projected_drawdown": current_drawdown, "vol_ok": 1.0, "es_ok": 1.0, "corr_ok": 1.0, "dd_ok": 1.0, "margin_ok": 1.0}
    selected_diag["raw_allowed_overlay"] = allowed
    return allowed, selected_diag


def _hysteresis_step(current: float, allowed: float, pending_up_days: int, cfg: Config) -> tuple[float, int]:
    if allowed < current - 1e-12:
        return allowed, 0
    if allowed <= current + 1e-12:
        return current, 0
    pending = pending_up_days + 1
    if pending < cfg.up_confirm_days:
        return current, pending
    states = [x for x in OVERLAY_STATES if x <= allowed + 1e-12]
    higher = [x for x in states if x > current + 1e-12]
    return (float(min(higher)), 0) if higher else (current, 0)


def run_dynamic_overlay(data: pd.DataFrame, cfg: Config, online: bool = False) -> StrategyResult:
    cfg.validate()
    n = len(data)
    start = cfg.warmup_days
    exec_overlay = np.zeros(n)
    exec_split = np.full(n, 0.5)
    signal_overlay = np.zeros(n)
    signal_split = np.full(n, 0.5)
    scheduled_overlay = np.zeros(n)
    scheduled_split = np.full(n, 0.5)
    pending_up = 0
    grad_sq = 1e-12
    alpha = 0.5
    equity = 1.0
    high_water = 1.0
    previous_eq = 0.0
    previous_gold = 0.0
    returns = np.zeros(n)
    turnover = np.zeros(n)
    financing = np.zeros(n)
    diagnostics: list[dict[str, Any]] = []
    contribution_rows: list[dict[str, float]] = []
    for i in range(n):
        if i >= cfg.delay:
            exec_overlay[i] = scheduled_overlay[i]
            exec_split[i] = scheduled_split[i]
        q = float(exec_overlay[i])
        split = float(exec_split[i])
        eq_w = q * split
        gold_w = q * (1.0 - split)
        traded = abs(eq_w - previous_eq) + abs(gold_w - previous_gold)
        cost = traded * cfg.one_way_cost_bps / 10_000.0
        finance = q * (float(data.iloc[i]["CASH"]) + cfg.borrow_spread_annual / ANNUALIZATION)
        core_c = float(data.iloc[i]["V10"])
        eq_c = eq_w * float(data.iloc[i]["EQUITY_TREND"])
        gold_c = gold_w * float(data.iloc[i]["GOLD_TREND"])
        r = core_c + eq_c + gold_c - finance - cost
        if r <= -1.0:
            raise ValueError("dynamic policy liquidated")
        returns[i] = r
        turnover[i] = traded
        financing[i] = finance
        equity *= 1.0 + r
        high_water = max(high_water, equity)
        current_dd = equity / high_water - 1.0
        contribution_rows.append({"V10_CORE": core_c, "EQUITY_OVERLAY": eq_c, "GOLD_OVERLAY": gold_c, "FINANCING": -finance, "TURNOVER_COST": -cost, "TOTAL": r})
        previous_eq, previous_gold = eq_w, gold_w
        if online and i >= start:
            denom = max(1.0 + r, 1e-8)
            grad = -q * (float(data.iloc[i]["EQUITY_TREND"]) - float(data.iloc[i]["GOLD_TREND"])) / denom
            grad_sq += grad * grad
            eta = cfg.online_eta_scale / math.sqrt(grad_sq)
            alpha = float(np.clip(alpha - eta * grad, cfg.online_split_min, cfg.online_split_max))
        if i >= start and i + cfg.delay < n:
            history = data.iloc[: i + 1]
            split_for_capacity = alpha if online else 0.5
            raw_allowed, diag = _capacity_for_split(history, current_dd, split_for_capacity, cfg)
            next_q, pending_up = _hysteresis_step(float(signal_overlay[i - 1]) if i > 0 else 0.0, raw_allowed, pending_up, cfg)
            signal_overlay[i] = next_q
            signal_split[i] = split_for_capacity
            scheduled_overlay[i + cfg.delay] = next_q
            scheduled_split[i + cfg.delay] = split_for_capacity
            diagnostics.append({"date": data.index[i], "executed_overlay": q, "executed_split": split, "signal_overlay": next_q, "signal_split": split_for_capacity, "current_drawdown": current_dd, **diag})
    oos_index = common_oos(data, cfg).index
    locs = data.index.get_indexer(oos_index)
    weights = pd.DataFrame({
        "V10": 1.0,
        "EQUITY_TREND": exec_overlay[locs] * exec_split[locs],
        "GOLD_TREND": exec_overlay[locs] * (1.0 - exec_split[locs]),
        "CASH": -exec_overlay[locs],
    }, index=oos_index)
    r = pd.Series(returns[locs], index=oos_index, name="return")
    t = pd.Series(turnover[locs], index=oos_index, name="turnover")
    f = pd.Series(financing[locs], index=oos_index, name="financing")
    eq_curve = (1 + r).cumprod()
    contributions = pd.DataFrame([contribution_rows[i] for i in locs], index=oos_index)
    ledger = _make_ledger(oos_index, weights, t, f, r)
    diagnostics_frame = pd.DataFrame(diagnostics).set_index("date") if diagnostics else pd.DataFrame()
    diagnostics_frame = diagnostics_frame.reindex(oos_index)
    name = "DYNAMIC_ONLINE_OVERLAY" if online else "DYNAMIC_NO_TILT_OVERLAY"
    return StrategyResult(name, r, weights, t, f, eq_curve, ledger, contributions, diagnostics_frame)


def run_equal_average_overlay_control(data: pd.DataFrame, cfg: Config, dynamic: StrategyResult, name: str) -> StrategyResult:
    overlay = dynamic.weights["EQUITY_TREND"] + dynamic.weights["GOLD_TREND"]
    q = float(overlay.mean())
    return run_static_portable(data, cfg, q / 2.0, q / 2.0, name)


def annualized_cagr_array(values: np.ndarray) -> float:
    r = np.asarray(values, dtype=float)
    if len(r) == 0 or np.any(r <= -1.0):
        return -1.0
    return float(np.exp(np.log1p(r).sum() * ANNUALIZATION / len(r)) - 1.0)


def sharpe_array(values: np.ndarray) -> float:
    r = np.asarray(values, dtype=float)
    sd = float(r.std(ddof=1)) if len(r) > 1 else 0.0
    return float(r.mean() / sd * math.sqrt(ANNUALIZATION)) if sd > 0 else 0.0


def max_drawdown_array(values: np.ndarray) -> float:
    r = np.asarray(values, dtype=float)
    eq = np.cumprod(1.0 + r)
    peaks = np.maximum.accumulate(eq)
    return float(np.min(eq / peaks - 1.0))


def paired_block_bootstrap(candidate: pd.Series, baseline: pd.Series, block: int, samples: int, seed: int) -> dict[str, float]:
    aligned = pd.concat([candidate.rename("c"), baseline.rename("b")], axis=1).dropna()
    c = aligned["c"].to_numpy()
    b = aligned["b"].to_numpy()
    n = len(aligned)
    if n < block * 2:
        raise ValueError("sample too short for block bootstrap")
    rng = np.random.default_rng(seed)
    d_sharpe = np.empty(samples)
    d_cagr = np.empty(samples)
    wealth_ratio = np.empty(samples)
    starts_per_sample = int(math.ceil(n / block))
    offsets = np.arange(block)
    for s in range(samples):
        starts = rng.integers(0, n, size=starts_per_sample)
        idx = ((starts[:, None] + offsets[None, :]) % n).ravel()[:n]
        cs = c[idx]
        bs = b[idx]
        d_sharpe[s] = sharpe_array(cs) - sharpe_array(bs)
        d_cagr[s] = annualized_cagr_array(cs) - annualized_cagr_array(bs)
        wealth_ratio[s] = float(np.prod(1 + cs) / np.prod(1 + bs))
    return {
        "block": int(block),
        "samples": int(samples),
        "delta_sharpe_mean": float(d_sharpe.mean()),
        "delta_sharpe_p025": float(np.quantile(d_sharpe, 0.025)),
        "delta_sharpe_p975": float(np.quantile(d_sharpe, 0.975)),
        "delta_cagr_mean": float(d_cagr.mean()),
        "delta_cagr_p025": float(np.quantile(d_cagr, 0.025)),
        "delta_cagr_p975": float(np.quantile(d_cagr, 0.975)),
        "wealth_ratio_median": float(np.median(wealth_ratio)),
        "wealth_ratio_p025": float(np.quantile(wealth_ratio, 0.025)),
        "probability_delta_sharpe_positive": float(np.mean(d_sharpe > 0)),
    }


def newey_west_mean_test(diff: pd.Series, lag: int) -> dict[str, float]:
    x = pd.Series(diff, dtype=float).dropna().to_numpy()
    n = len(x)
    if n < lag + 5:
        raise ValueError("sample too short for HAC lag")
    demeaned = x - x.mean()
    gamma0 = float(np.dot(demeaned, demeaned) / n)
    long_var = gamma0
    for k in range(1, lag + 1):
        gamma = float(np.dot(demeaned[k:], demeaned[:-k]) / n)
        weight = 1.0 - k / (lag + 1.0)
        long_var += 2.0 * weight * gamma
    se = math.sqrt(max(long_var, 1e-18) / n)
    t = float(x.mean() / se)
    p = float(2.0 * (1.0 - statistics.NormalDist().cdf(abs(t))))
    return {"lag": int(lag), "mean_daily_difference": float(x.mean()), "hac_se": se, "t_stat": t, "p_value": p}


def deflated_sharpe_probability(returns: pd.Series, trials: int) -> dict[str, float]:
    r = pd.Series(returns, dtype=float).dropna()
    n = len(r)
    sr_daily = float(r.mean() / r.std(ddof=1)) if r.std(ddof=1) > 0 else 0.0
    skew = float(r.skew()) if n > 2 else 0.0
    kurt = float(r.kurtosis() + 3.0) if n > 3 else 3.0
    variance_sr = max((1.0 - skew * sr_daily + ((kurt - 1.0) / 4.0) * sr_daily * sr_daily) / max(n - 1, 1), 1e-18)
    se = math.sqrt(variance_sr)
    normal = statistics.NormalDist()
    if trials <= 1:
        expected_max = 0.0
    else:
        gamma = 0.5772156649
        z1 = normal.inv_cdf(1.0 - 1.0 / trials)
        z2 = normal.inv_cdf(1.0 - 1.0 / (trials * math.e))
        expected_max = se * ((1.0 - gamma) * z1 + gamma * z2)
    z = (sr_daily - expected_max) / se
    probability = float(normal.cdf(z))
    return {"trials": int(trials), "daily_sharpe": sr_daily, "annual_sharpe": sr_daily * math.sqrt(ANNUALIZATION), "expected_max_daily_sharpe": expected_max, "probability": probability, "skew": skew, "kurtosis": kurt}


def feasibility_screen(data: pd.DataFrame, cfg: Config, baseline: StrategyResult) -> dict[str, Any]:
    baseline_metrics = performance_metrics(baseline.returns, pd.Series(1.0, index=baseline.returns.index))
    target_mdd = baseline_metrics["mdd"] + cfg.target_mdd_improvement
    grid = np.linspace(0.0, cfg.max_overlay, 601)
    records = []
    required_q: float | None = None
    risk_q = 0.0
    for q in grid:
        result = run_static_portable(data, cfg, q / 2.0, q / 2.0, f"FEASIBILITY_{q:.3f}")
        gross = 1.0 + result.weights["EQUITY_TREND"] + result.weights["GOLD_TREND"]
        metrics = performance_metrics(result.returns, gross)
        if required_q is None and metrics["cagr"] >= baseline_metrics["cagr"]:
            required_q = float(q)
        if metrics["mdd"] >= target_mdd:
            risk_q = float(q)
        records.append({"overlay": float(q), "cagr": metrics["cagr"], "mdd": metrics["mdd"], "sharpe": metrics["sharpe"], "final_equity": metrics["final_equity"]})
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


def economic_gates(candidate: StrategyResult, baseline: StrategyResult) -> dict[str, Any]:
    c_gross = candidate.weights[["V10", "EQUITY_TREND", "GOLD_TREND"]].abs().sum(axis=1)
    b_gross = baseline.weights[["V10", "EQUITY_TREND", "GOLD_TREND"]].abs().sum(axis=1)
    c = performance_metrics(candidate.returns, c_gross)
    b = performance_metrics(baseline.returns, b_gross)
    tests = {
        "cagr_advantage": c["cagr"] >= b["cagr"],
        "terminal_wealth_ratio": c["final_equity"] / b["final_equity"] >= 1.05,
        "sharpe_advantage": c["sharpe"] - b["sharpe"] >= 0.10,
        "mdd_improvement": c["mdd"] - b["mdd"] >= 0.08,
        "calmar_advantage": c["calmar"] - b["calmar"] >= 0.20,
        "cvar_improvement": abs(c["cvar5"]) <= abs(b["cvar5"]) * 0.85,
        "liquidations": c["liquidations"] == 0,
        "equity_net_contribution_positive": float(candidate.contributions["EQUITY_OVERLAY"].sum() - candidate.financing.sum() / 2.0) > 0,
        "gold_net_contribution_positive": float(candidate.contributions["GOLD_OVERLAY"].sum() - candidate.financing.sum() / 2.0) > 0,
    }
    return {"candidate": c, "baseline": b, "tests": tests, "pass": bool(all(tests.values()))}


def incremental_gate(candidate: StrategyResult, control: StrategyResult, kind: str) -> dict[str, Any]:
    c = performance_metrics(candidate.returns, candidate.weights[["V10", "EQUITY_TREND", "GOLD_TREND"]].abs().sum(axis=1))
    b = performance_metrics(control.returns, control.weights[["V10", "EQUITY_TREND", "GOLD_TREND"]].abs().sum(axis=1))
    if kind == "online":
        tests = {"sharpe_advantage": c["sharpe"] - b["sharpe"] >= 0.05, "wealth_ratio": c["final_equity"] / b["final_equity"] >= 1.02, "mdd_not_worse": c["mdd"] >= b["mdd"]}
    else:
        tests = {"sharpe_advantage": c["sharpe"] - b["sharpe"] >= 0.05, "wealth_ratio": c["final_equity"] / b["final_equity"] >= 0.98, "mdd_not_worse": c["mdd"] >= b["mdd"]}
    return {"candidate": c, "control": b, "tests": tests, "pass": bool(all(tests.values()))}


def start_shift_stress(candidate: StrategyResult, baseline: StrategyResult, shifts: Iterable[int] = (-30, -15, 0, 15, 30)) -> list[dict[str, Any]]:
    aligned = pd.concat([candidate.returns.rename("candidate"), baseline.returns.rename("baseline")], axis=1).dropna()
    rows = []
    for shift in shifts:
        if shift < 0:
            subset = aligned.iloc[:shift]
        else:
            subset = aligned.iloc[shift:]
        if len(subset) < 60:
            continue
        cm = performance_metrics(subset["candidate"])
        bm = performance_metrics(subset["baseline"])
        rows.append({"shift_days": int(shift), "observations": len(subset), "delta_sharpe": cm["sharpe"] - bm["sharpe"], "wealth_ratio": cm["final_equity"] / bm["final_equity"], "delta_mdd": cm["mdd"] - bm["mdd"]})
    return rows


def leave_one_year_out(candidate: StrategyResult, baseline: StrategyResult) -> list[dict[str, Any]]:
    aligned = pd.concat([candidate.returns.rename("candidate"), baseline.returns.rename("baseline")], axis=1).dropna()
    years = sorted(set(aligned.index.year))
    rows = []
    for year in years:
        subset = aligned[aligned.index.year != year]
        if len(subset) < 60:
            continue
        cm = performance_metrics(subset["candidate"])
        bm = performance_metrics(subset["baseline"])
        rows.append({"excluded_year": int(year), "delta_sharpe": cm["sharpe"] - bm["sharpe"], "wealth_ratio": cm["final_equity"] / bm["final_equity"], "delta_mdd": cm["mdd"] - bm["mdd"]})
    return rows


def financing_cost_stress(data: pd.DataFrame, cfg: Config, rates: Iterable[float]) -> list[dict[str, Any]]:
    rows = []
    for rate in rates:
        stressed = run_static_portable(data, replace(cfg, borrow_spread_annual=float(rate)))
        m = performance_metrics(stressed.returns, stressed.weights[["V10", "EQUITY_TREND", "GOLD_TREND"]].abs().sum(axis=1))
        rows.append({"stress": "borrow_spread", "value": float(rate), **m})
    return rows


def transaction_cost_stress(data: pd.DataFrame, cfg: Config, costs: Iterable[float]) -> list[dict[str, Any]]:
    rows = []
    for cost in costs:
        stressed = run_static_portable(data, replace(cfg, one_way_cost_bps=float(cost)))
        m = performance_metrics(stressed.returns, stressed.weights[["V10", "EQUITY_TREND", "GOLD_TREND"]].abs().sum(axis=1))
        rows.append({"stress": "one_way_cost_bps", "value": float(cost), **m})
    return rows


def gap_stress_table() -> list[dict[str, float]]:
    rows = []
    for growth, equity, gold in ((-0.15, -0.07, -0.04), (-0.25, -0.12, -0.08), (-0.35, -0.18, -0.12)):
        portfolio = growth + 0.30 * equity + 0.30 * gold
        post_equity = 1.0 + portfolio
        maintenance = post_equity / 1.60
        rows.append({"growth_gap": growth, "equity_gap": equity, "gold_gap": gold, "portfolio_return": portfolio, "post_equity": post_equity, "maintenance_ratio": maintenance})
    return rows


def baseline_identity(data: pd.DataFrame, cfg: Config, input_path: Path) -> dict[str, Any]:
    baseline = run_v10(data, cfg)
    metrics = performance_metrics(baseline.returns, pd.Series(1.0, index=baseline.returns.index))
    payload = baseline.returns.to_csv(header=True, lineterminator="\n", float_format="%.12g").encode("utf-8")
    return {
        "name": "V10_ALIGNED_COMMON_OOS",
        "not_name": "V10_FULL_HISTORY",
        "aligned_start": baseline.returns.index[0],
        "aligned_end": baseline.returns.index[-1],
        "aligned_observations": len(baseline.returns),
        "input_path": input_path,
        "input_sha256": sha256_file(input_path),
        "aligned_v10_returns_sha256": sha256_bytes(payload),
        "aligned_metrics": metrics,
        "external_full_history_identity_required": True,
    }


def deterministic_zip(source_root: Path, destination: Path, include_results: bool = True) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    excluded_parts = {".git", ".venv", "__pycache__", ".pytest_cache", ".mypy_cache"}
    files: list[Path] = []
    for path in source_root.rglob("*"):
        if not path.is_file() or destination.resolve() == path.resolve():
            continue
        rel = path.relative_to(source_root)
        if any(part in excluded_parts for part in rel.parts):
            continue
        if not include_results and rel.parts and rel.parts[0] == "results":
            continue
        if rel.parts and rel.parts[0] == "runtime":
            continue
        files.append(path)
    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for path in sorted(files, key=lambda p: str(p.relative_to(source_root))):
            rel = str(path.relative_to(source_root)).replace(os.sep, "/")
            info = zipfile.ZipInfo(rel, date_time=(2026, 7, 19, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = (0o755 if path.suffix == ".command" else 0o644) << 16
            zf.writestr(info, path.read_bytes())


def output_manifest(root: Path, exclude: set[str] | None = None) -> dict[str, Any]:
    exclude = exclude or set()
    rows = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        rel = str(path.relative_to(root)).replace(os.sep, "/")
        if rel in exclude:
            continue
        rows.append({"path": rel, "size": path.stat().st_size, "sha256": sha256_file(path)})
    return {"version": VERSION, "files": rows, "tree_sha256": sha256_bytes(json.dumps(rows, sort_keys=True, separators=(",", ":")).encode("utf-8"))}

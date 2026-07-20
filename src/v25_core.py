#!/usr/bin/env python3
"""V25 Dual Causal Defense research core.

Primary path A: causal reduction of the aligned V10 core using a drawdown-floor
risk budget. Primary path B: replacement of reduced core exposure with only
point-in-time, tradable tail engines that pass expanding negative-tail-beta and
crisis-return qualification. The official combined policy never borrows: net
and risky gross remain exactly one or less.

This code proves protocol invariants and falsifies historical hypotheses. It
does not prove future returns or an unconditional drawdown bound outside the
registered stress set.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import shutil
import statistics
import zipfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import numpy as np
import pandas as pd

VERSION = "25.0.0"
ANNUALIZATION = 365.25
CORE_STATES = np.asarray([0.00, 0.25, 0.50, 0.75, 1.00], dtype=float)


@dataclass(frozen=True)
class Config:
    delay: int = 2
    warmup_days: int = 756
    target_drawdown: float = 0.29
    stress_lookback: int = 756
    empirical_horizon: int = 3
    gap_loss_floor: float = 0.25
    gaussian_z: float = 2.326347874
    core_up_confirm_days: int = 20
    tail_quantile: float = 0.05
    minimum_tail_observations: int = 30
    tail_beta_max: float = 0.0
    tail_crisis_mean_min: float = 0.0
    tail_worst20_mean_min: float = 0.0
    tail_cagr_min: float = 0.0
    tail_vol_window: int = 120
    per_engine_tail_cap: float = 0.60
    one_way_cost_bps: float = 17.0
    allow_unverified_tail: bool = False
    bootstrap_samples: int = 5000
    random_seed: int = 20260720

    def validate(self) -> None:
        if self.delay < 0:
            raise ValueError("delay must be non-negative")
        if self.warmup_days < 252:
            raise ValueError("warmup_days must be at least 252")
        if not 0 < self.target_drawdown < 1:
            raise ValueError("target_drawdown must be in (0,1)")
        if not 0 < self.gap_loss_floor < 1:
            raise ValueError("gap_loss_floor must be in (0,1)")
        if self.empirical_horizon < self.delay + 1:
            raise ValueError("empirical_horizon must cover delay+1")
        if not 0 < self.tail_quantile < 0.5:
            raise ValueError("tail_quantile must be in (0,0.5)")
        if not 0 < self.per_engine_tail_cap <= 1:
            raise ValueError("invalid per_engine_tail_cap")


@dataclass
class StrategyResult:
    name: str
    returns: pd.Series
    weights: pd.DataFrame
    turnover: pd.Series
    costs: pd.Series
    equity: pd.Series
    ledger: pd.DataFrame
    diagnostics: pd.DataFrame
    qualification: pd.DataFrame


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
    path.write_text(json.dumps(_json_safe(payload), indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def _read_table(path: Path) -> pd.DataFrame:
    lower = path.name.lower()
    if lower.endswith(".csv.gz"):
        return pd.read_csv(path, compression="gzip", low_memory=False)
    if lower.endswith(".csv"):
        return pd.read_csv(path, low_memory=False)
    if lower.endswith(".parquet"):
        return pd.read_parquet(path)
    raise ValueError(f"unsupported input format: {path}")


def _find_column(frame: pd.DataFrame, aliases: Sequence[str]) -> str | None:
    lookup = {str(c).strip().lower(): str(c) for c in frame.columns}
    for alias in aliases:
        if alias.lower() in lookup:
            return lookup[alias.lower()]
    return None


def normalize_date_frame(frame: pd.DataFrame) -> pd.DataFrame:
    output = frame.copy()
    date_col = _find_column(output, ("date", "datetime", "timestamp", "time", "open_time", "day"))
    if date_col is None:
        if not isinstance(output.index, pd.DatetimeIndex):
            raise ValueError("no date column")
        output.index = pd.to_datetime(output.index, utc=True, errors="coerce").normalize()
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
    return output[~output.index.duplicated(keep="last")].sort_index()


def canonicalize_input(path: Path) -> pd.DataFrame:
    raw = normalize_date_frame(_read_table(path))
    v10_col = _find_column(raw, ("v10", "baseline_v10", "crypto_v10", "baseline"))
    if v10_col is None:
        raise ValueError("missing required V10 column")
    cash_col = _find_column(raw, ("cash", "cash_return", "risk_free", "bil", "sgov"))
    out = pd.DataFrame(index=raw.index)
    out["V10"] = pd.to_numeric(raw[v10_col], errors="coerce")
    out["CASH"] = 0.0 if cash_col is None else pd.to_numeric(raw[cash_col], errors="coerce").fillna(0.0)
    for col in raw.columns:
        canonical = str(col).strip().upper()
        if canonical.startswith("TAIL_"):
            out[canonical] = pd.to_numeric(raw[col], errors="coerce")
    out = out.replace([np.inf, -np.inf], np.nan).dropna(subset=["V10"])
    if len(out) < 900:
        raise ValueError(f"need at least 900 rows; got {len(out)}")
    if (out[["V10"] + tail_columns(out)].abs() > 0.95).any().any():
        raise ValueError("returns appear to be prices or whole percentages")
    return out.astype(float)


def tail_columns(frame: pd.DataFrame) -> list[str]:
    return sorted(str(c) for c in frame.columns if str(c).upper().startswith("TAIL_"))


def discover_input(root: Path, explicit: Path | None = None) -> Path:
    if explicit is not None:
        path = explicit.expanduser().resolve()
        if not path.exists():
            raise FileNotFoundError(path)
        return path
    env = os.getenv("V25_ENGINE_RETURNS_FILE") or os.getenv("ENGINE_RETURNS_FILE")
    if env and Path(env).expanduser().exists():
        return Path(env).expanduser().resolve()
    patterns = ("v25_engine_returns.csv.gz", "engine_returns.csv.gz", "engine_returns.csv", "daily_engine_returns.csv.gz")
    roots = [root, Path.home() / "Downloads", Path.home() / "Documents/ZCode/Autotrade"]
    candidates: list[Path] = []
    for base in roots:
        if not base.exists():
            continue
        for pattern in patterns:
            candidates.extend(base.rglob(pattern))
    if candidates:
        return max(candidates, key=lambda p: p.stat().st_mtime).resolve()
    raise FileNotFoundError("set V25_ENGINE_RETURNS_FILE or pass --input")


def load_provenance(path: Path | None) -> dict[str, Any]:
    if path is None:
        env = os.getenv("TAIL_PROVENANCE_FILE")
        path = Path(env).expanduser() if env else None
    if path is None or not path.exists():
        return {"engines": {}, "source": None}
    payload = json.loads(path.read_text(encoding="utf-8"))
    engines = payload.get("engines", payload)
    if not isinstance(engines, dict):
        raise ValueError("tail provenance must contain an engines mapping")
    return {"engines": engines, "source": str(path.resolve()), "sha256": sha256_file(path)}


def provenance_pass(meta: Mapping[str, Any] | None) -> bool:
    if not meta:
        return False
    required_truth = bool(meta.get("tradable")) and bool(meta.get("point_in_time"))
    required_text = all(bool(str(meta.get(k, "")).strip()) for k in ("source_sha256", "retrieved_at", "cost_model"))
    return required_truth and required_text


def performance_metrics(returns: pd.Series, gross: pd.Series | None = None) -> dict[str, Any]:
    r = pd.Series(returns, dtype=float).dropna()
    if r.empty:
        raise ValueError("empty return series")
    if (r <= -1.0).any():
        raise ValueError("liquidation")
    equity = (1.0 + r).cumprod()
    drawdown = equity / equity.cummax() - 1.0
    sd = float(r.std(ddof=1))
    sharpe = float(r.mean() / sd * math.sqrt(ANNUALIZATION)) if sd > 0 else 0.0
    years = max((r.index[-1] - r.index[0]).days / ANNUALIZATION, len(r) / ANNUALIZATION, 1 / ANNUALIZATION)
    final = float(equity.iloc[-1])
    cagr = float(final ** (1.0 / years) - 1.0)
    mdd = float(drawdown.min())
    q = float(r.quantile(0.05))
    cvar = float(r[r <= q].mean())
    g = pd.Series(1.0, index=r.index) if gross is None else pd.Series(gross, dtype=float).reindex(r.index).ffill().fillna(0.0)
    return {
        "observations": int(len(r)), "start": r.index[0], "end": r.index[-1],
        "sharpe": sharpe, "cagr": cagr, "mdd": mdd,
        "calmar": float(cagr / abs(mdd)) if mdd < 0 else 0.0,
        "cvar5": cvar, "final_equity": final,
        "annual_volatility": sd * math.sqrt(ANNUALIZATION),
        "average_gross": float(g.mean()), "maximum_gross": float(g.max()),
        "liquidations": int((r <= -1.0).sum()),
    }


def annualized_cagr(returns: pd.Series) -> float:
    return float(performance_metrics(returns)["cagr"])


def horizon_returns(series: pd.Series, horizon: int) -> pd.Series:
    return (1.0 + pd.Series(series, dtype=float)).rolling(horizon).apply(np.prod, raw=True) - 1.0


def stress_loss(history: pd.Series, cfg: Config) -> dict[str, float]:
    cfg.validate()
    s = pd.Series(history, dtype=float).dropna().tail(cfg.stress_lookback + cfg.empirical_horizon)
    if len(s) < 60:
        return {"stress_loss": cfg.gap_loss_floor, "empirical": 0.0, "cvar": 0.0, "gaussian": 0.0}
    h = horizon_returns(s, cfg.empirical_horizon).dropna()
    empirical = abs(min(float(h.min()), 0.0)) if len(h) else 0.0
    if len(h):
        cutoff = float(h.quantile(0.05))
        cvar = abs(float(h[h <= cutoff].mean()))
    else:
        cvar = 0.0
    sigma = float(s.tail(60).std(ddof=1)) * math.sqrt(cfg.empirical_horizon)
    gaussian = cfg.gaussian_z * sigma
    loss = min(max(cfg.gap_loss_floor, empirical, cvar, gaussian), 0.95)
    return {"stress_loss": float(loss), "empirical": empirical, "cvar": cvar, "gaussian": gaussian}


def core_capacity(equity: float, high_water: float, history: pd.Series, cfg: Config) -> dict[str, float]:
    stress = stress_loss(history, cfg)
    floor = high_water * (1.0 - cfg.target_drawdown)
    cushion = max(equity - floor, 0.0)
    raw = 0.0 if equity <= 0 else min(1.0, cushion / max(equity * stress["stress_loss"], 1e-12))
    allowed = max(float(x) for x in CORE_STATES if x <= raw + 1e-12)
    return {"floor": floor, "cushion": cushion, "raw_capacity": raw, "allowed_state": allowed, **stress}


def hysteresis_step(current: float, allowed: float, pending: int, cfg: Config) -> tuple[float, int]:
    current = float(current)
    allowed = float(allowed)
    if allowed < current - 1e-12:
        return allowed, 0
    if allowed <= current + 1e-12:
        return current, 0
    idx = int(np.where(np.isclose(CORE_STATES, current))[0][0])
    if idx >= len(CORE_STATES) - 1:
        return current, 0
    next_state = float(CORE_STATES[idx + 1])
    if allowed + 1e-12 < next_state:
        return current, 0
    pending += 1
    if pending >= cfg.core_up_confirm_days:
        return next_state, 0
    return current, pending


def tail_engine_statistics(history: pd.DataFrame, column: str, provenance: Mapping[str, Any], cfg: Config) -> dict[str, Any]:
    aligned = history[["V10", column]].dropna()
    result: dict[str, Any] = {"engine": column, "observations": int(len(aligned))}
    if len(aligned) < max(252, cfg.minimum_tail_observations * 10):
        return {**result, "qualified": False, "reason": "insufficient_history", "provenance_pass": provenance_pass(provenance)}
    cutoff = float(aligned["V10"].quantile(cfg.tail_quantile))
    tail = aligned[aligned["V10"] <= cutoff]
    var = float(tail["V10"].var(ddof=1)) if len(tail) > 1 else 0.0
    beta = float(tail[["V10", column]].cov().iloc[0, 1] / var) if var > 0 else float("inf")
    tail_mean = float(tail[column].mean()) if len(tail) else float("nan")
    worst20 = aligned.nsmallest(min(20, len(aligned)), "V10")
    worst20_mean = float(worst20[column].mean())
    cagr = annualized_cagr(aligned[column])
    prov = provenance_pass(provenance)
    tests = {
        "tail_observations": len(tail) >= cfg.minimum_tail_observations,
        "negative_tail_beta": beta <= cfg.tail_beta_max,
        "positive_tail_mean": tail_mean > cfg.tail_crisis_mean_min,
        "positive_worst20_mean": worst20_mean > cfg.tail_worst20_mean_min,
        "positive_cagr": cagr > cfg.tail_cagr_min,
        "provenance": prov or cfg.allow_unverified_tail,
    }
    return {
        **result, "tail_observations": int(len(tail)), "tail_cutoff": cutoff,
        "tail_beta": beta, "tail_mean": tail_mean, "worst20_mean": worst20_mean,
        "cagr": cagr, "provenance_pass": prov, "tests": tests,
        "qualified": bool(all(tests.values())),
        "reason": "PASS" if all(tests.values()) else ",".join(k for k, v in tests.items() if not v),
    }


def bounded_weights(raw: np.ndarray, cap: float) -> np.ndarray:
    x = np.asarray(raw, dtype=float)
    if len(x) == 1:
        return np.asarray([1.0])
    if cap * len(x) < 1.0 - 1e-12:
        cap = 1.0
    x = np.maximum(x, 0.0)
    x = np.ones_like(x) / len(x) if x.sum() <= 0 else x / x.sum()
    for _ in range(20):
        over = x > cap
        if not over.any():
            break
        excess = float((x[over] - cap).sum())
        x[over] = cap
        under = ~over
        if not under.any():
            break
        room = np.maximum(cap - x[under], 0.0)
        if room.sum() <= 0:
            break
        x[under] += excess * room / room.sum()
    return x / x.sum()


def qualify_tail_engines(history: pd.DataFrame, provenance_payload: Mapping[str, Any], cfg: Config) -> tuple[dict[str, float], list[dict[str, Any]]]:
    cols = tail_columns(history)
    engines_meta = provenance_payload.get("engines", {}) if isinstance(provenance_payload, Mapping) else {}
    rows = [tail_engine_statistics(history, col, engines_meta.get(col, {}), cfg) for col in cols]
    qualified = [row["engine"] for row in rows if row.get("qualified")]
    if not qualified:
        return {}, rows
    vols = []
    for col in qualified:
        vol = float(history[col].tail(cfg.tail_vol_window).std(ddof=1))
        vols.append(max(vol, 1e-8))
    weights = bounded_weights(1.0 / np.asarray(vols), cfg.per_engine_tail_cap)
    return {col: float(w) for col, w in zip(qualified, weights)}, rows


def _exact_ppm(weights: Mapping[str, float], columns: Sequence[str]) -> dict[str, int]:
    raw = np.asarray([float(weights.get(c, 0.0)) for c in columns]) * 1_000_000.0
    rounded = np.floor(raw).astype(np.int64)
    residual = int(1_000_000 - rounded.sum())
    fractions = raw - np.floor(raw)
    if residual > 0:
        for i in np.argsort(-fractions)[:residual]:
            rounded[i] += 1
    elif residual < 0:
        for i in np.argsort(fractions)[:abs(residual)]:
            rounded[i] -= 1
    if int(rounded.sum()) != 1_000_000:
        rounded[0] += 1_000_000 - int(rounded.sum())
    return {c: int(v) for c, v in zip(columns, rounded)}


def _make_ledger(index: pd.Index, weights: pd.DataFrame, turnover: pd.Series, costs: pd.Series, returns: pd.Series) -> pd.DataFrame:
    columns = list(weights.columns)
    rows: list[dict[str, Any]] = []
    for date in index:
        ppm = _exact_ppm(weights.loc[date].to_dict(), columns)
        row: dict[str, Any] = {"date": date}
        for col in columns:
            row[f"{col.lower()}_ppm"] = ppm[col]
        risky = abs(ppm.get("V10", 0)) + sum(abs(ppm.get(c, 0)) for c in columns if c.startswith("TAIL_"))
        row.update({
            "net_ppm": int(sum(ppm.values())), "risky_gross_ppm": int(risky),
            "turnover_ppm": int(round(float(turnover.loc[date]) * 1_000_000)),
            "cost_nano": int(round(float(costs.loc[date]) * 1_000_000_000)),
            "return_nano": int(round(float(returns.loc[date]) * 1_000_000_000)),
        })
        rows.append(row)
    ledger = pd.DataFrame(rows)
    ledger.attrs["sha256"] = sha256_bytes(ledger.to_csv(index=False, lineterminator="\n").encode("utf-8"))
    return ledger


def _monthly_decision(index: pd.DatetimeIndex, i: int) -> bool:
    if i == 0 or i == len(index) - 1:
        return True
    return index[i].to_period("M") != index[i + 1].to_period("M")


def run_policy(data: pd.DataFrame, cfg: Config, provenance_payload: Mapping[str, Any], use_tail: bool, name: str) -> StrategyResult:
    cfg.validate()
    n = len(data)
    tails = tail_columns(data)
    all_columns = ["V10"] + tails + ["CASH"]
    delay = cfg.delay
    core_queue = [1.0] * max(delay, 1)
    split_queue: list[dict[str, float]] = [{} for _ in range(max(delay, 1))]
    signal_core = 1.0
    signal_split: dict[str, float] = {}
    pending_up = 0
    previous_risky = {"V10": 1.0, **{c: 0.0 for c in tails}}
    equity = 1.0
    high_water = 1.0
    returns = np.zeros(n)
    turnover = np.zeros(n)
    costs = np.zeros(n)
    weight_rows: list[dict[str, float]] = []
    diag_rows: list[dict[str, Any]] = []
    qualification_rows: list[dict[str, Any]] = []

    for i, date in enumerate(data.index):
        if delay > 0:
            exec_core = float(core_queue.pop(0))
            exec_split = dict(split_queue.pop(0))
        else:
            exec_core = signal_core
            exec_split = dict(signal_split)
        tail_total = (1.0 - exec_core) if (use_tail and exec_split) else 0.0
        row_weights = {"V10": exec_core, **{c: tail_total * float(exec_split.get(c, 0.0)) for c in tails}}
        row_weights["CASH"] = 1.0 - sum(row_weights.values())
        if abs(sum(row_weights.values()) - 1.0) > 1e-10:
            raise RuntimeError("net weights invariant failed")
        risky_gross = abs(row_weights["V10"]) + sum(abs(row_weights[c]) for c in tails)
        if risky_gross > 1.0 + 1e-10:
            raise RuntimeError("official V25 policy must not borrow")
        traded = abs(row_weights["V10"] - previous_risky["V10"]) + sum(abs(row_weights[c] - previous_risky[c]) for c in tails)
        cost = traded * cfg.one_way_cost_bps / 10_000.0
        r = row_weights["V10"] * float(data.iloc[i]["V10"]) + row_weights["CASH"] * float(data.iloc[i]["CASH"])
        for col in tails:
            value = data.iloc[i][col]
            if pd.notna(value):
                r += row_weights[col] * float(value)
        r -= cost
        if r <= -1.0:
            raise ValueError(f"{name} liquidated")
        returns[i] = r
        turnover[i] = traded
        costs[i] = cost
        equity *= 1.0 + r
        high_water = max(high_water, equity)
        current_dd = equity / high_water - 1.0
        weight_rows.append(row_weights)
        previous_risky = {"V10": row_weights["V10"], **{c: row_weights[c] for c in tails}}

        if i >= cfg.warmup_days and i + delay < n:
            history = data.iloc[: i + 1]
            cap = core_capacity(equity, high_water, history["V10"], cfg)
            signal_core, pending_up = hysteresis_step(signal_core, cap["allowed_state"], pending_up, cfg)
            if use_tail and _monthly_decision(data.index, i):
                signal_split, qrows = qualify_tail_engines(history, provenance_payload, cfg)
                for qrow in qrows:
                    qualification_rows.append({"date": date, **qrow})
            diag_rows.append({
                "date": date, "executed_core": exec_core, "signal_core": signal_core,
                "executed_tail_total": tail_total, "qualified_tail_count": len(signal_split),
                "current_drawdown": current_dd, "equity": equity, "high_water": high_water,
                **cap,
            })
        if delay > 0:
            core_queue.append(signal_core)
            split_queue.append(dict(signal_split))

    start = cfg.warmup_days + cfg.delay
    idx = data.index[start:]
    weights = pd.DataFrame(weight_rows, index=data.index)[all_columns].iloc[start:].copy()
    rseries = pd.Series(returns[start:], index=idx, name="return")
    tseries = pd.Series(turnover[start:], index=idx, name="turnover")
    cseries = pd.Series(costs[start:], index=idx, name="cost")
    eqseries = (1.0 + rseries).cumprod()
    ledger = _make_ledger(idx, weights, tseries, cseries, rseries)
    diagnostics = pd.DataFrame(diag_rows).set_index("date").reindex(idx) if diag_rows else pd.DataFrame(index=idx)
    qualification = pd.DataFrame(qualification_rows)
    return StrategyResult(name, rseries, weights, tseries, cseries, eqseries, ledger, diagnostics, qualification)


def run_v10(data: pd.DataFrame, cfg: Config) -> StrategyResult:
    start = cfg.warmup_days + cfg.delay
    idx = data.index[start:]
    tails = tail_columns(data)
    weights = pd.DataFrame({"V10": 1.0, **{c: 0.0 for c in tails}, "CASH": 0.0}, index=idx)
    returns = data.loc[idx, "V10"].astype(float)
    turnover = pd.Series(0.0, index=idx)
    costs = pd.Series(0.0, index=idx)
    equity = (1.0 + returns).cumprod()
    ledger = _make_ledger(idx, weights, turnover, costs, returns)
    return StrategyResult("V10_ALIGNED_COMMON_OOS", returns, weights, turnover, costs, equity, ledger, pd.DataFrame(index=idx), pd.DataFrame())


def run_core_derisk(data: pd.DataFrame, cfg: Config) -> StrategyResult:
    return run_policy(data, cfg, {"engines": {}}, False, "CORE_DERISK_ONLY")


def run_dual_defense(data: pd.DataFrame, cfg: Config, provenance_payload: Mapping[str, Any]) -> StrategyResult:
    return run_policy(data, cfg, provenance_payload, True, "CORE_DERISK_PLUS_TAIL")


def run_equal_average_control(data: pd.DataFrame, cfg: Config, source: StrategyResult, name: str) -> StrategyResult:
    idx = source.weights.index
    tails = tail_columns(data)
    average = source.weights[["V10"] + tails + ["CASH"]].mean()
    weights = pd.DataFrame({col: float(average[col]) for col in average.index}, index=idx)
    risky = ["V10"] + tails
    turnover = weights[risky].diff().abs().sum(axis=1)
    turnover.iloc[0] = weights.iloc[0][risky].abs().sum()
    costs = turnover * cfg.one_way_cost_bps / 10_000.0
    returns = weights["V10"] * data.loc[idx, "V10"] + weights["CASH"] * data.loc[idx, "CASH"]
    for col in tails:
        returns += weights[col] * data.loc[idx, col].fillna(0.0)
    returns -= costs
    equity = (1.0 + returns).cumprod()
    ledger = _make_ledger(idx, weights, turnover, costs, returns)
    return StrategyResult(name, returns, weights, turnover, costs, equity, ledger, pd.DataFrame(index=idx), pd.DataFrame())


def paired_block_bootstrap(candidate: pd.Series, baseline: pd.Series, block: int, samples: int, seed: int) -> dict[str, float]:
    aligned = pd.concat([candidate.rename("c"), baseline.rename("b")], axis=1).dropna()
    c = aligned["c"].to_numpy()
    b = aligned["b"].to_numpy()
    n = len(aligned)
    if n < block * 2:
        raise ValueError("sample too short")
    rng = np.random.default_rng(seed)
    d_sharpe = np.empty(samples)
    wealth = np.empty(samples)
    blocks = int(math.ceil(n / block))
    offsets = np.arange(block)
    for s in range(samples):
        starts = rng.integers(0, n, size=blocks)
        pick = ((starts[:, None] + offsets[None, :]) % n).ravel()[:n]
        cs, bs = c[pick], b[pick]
        csd, bsd = cs.std(ddof=1), bs.std(ddof=1)
        csr = cs.mean() / csd * math.sqrt(ANNUALIZATION) if csd > 0 else 0.0
        bsr = bs.mean() / bsd * math.sqrt(ANNUALIZATION) if bsd > 0 else 0.0
        d_sharpe[s] = csr - bsr
        wealth[s] = np.prod(1.0 + cs) / np.prod(1.0 + bs)
    return {
        "block": block, "samples": samples,
        "delta_sharpe_mean": float(d_sharpe.mean()),
        "delta_sharpe_p025": float(np.quantile(d_sharpe, 0.025)),
        "delta_sharpe_p975": float(np.quantile(d_sharpe, 0.975)),
        "wealth_ratio_median": float(np.median(wealth)),
        "wealth_ratio_p025": float(np.quantile(wealth, 0.025)),
    }


def strategy_gate(candidate: StrategyResult, baseline: StrategyResult) -> dict[str, Any]:
    c = performance_metrics(candidate.returns, candidate.weights.drop(columns=["CASH"]).abs().sum(axis=1))
    b = performance_metrics(baseline.returns, baseline.weights.drop(columns=["CASH"]).abs().sum(axis=1))
    tests = {
        "cagr_advantage": c["cagr"] >= b["cagr"],
        "wealth_ratio": c["final_equity"] / b["final_equity"] >= 1.05,
        "sharpe_advantage": c["sharpe"] - b["sharpe"] >= 0.10,
        "mdd_improvement": c["mdd"] - b["mdd"] >= 0.08,
        "calmar_advantage": c["calmar"] - b["calmar"] >= 0.20,
        "cvar_improvement": abs(c["cvar5"]) <= abs(b["cvar5"]) * 0.85,
        "liquidations": c["liquidations"] == 0,
    }
    return {"candidate": c, "baseline": b, "tests": tests, "pass": bool(all(tests.values()))}


def incremental_gate(candidate: StrategyResult, control: StrategyResult) -> dict[str, Any]:
    c = performance_metrics(candidate.returns, candidate.weights.drop(columns=["CASH"]).abs().sum(axis=1))
    b = performance_metrics(control.returns, control.weights.drop(columns=["CASH"]).abs().sum(axis=1))
    tests = {
        "sharpe_advantage": c["sharpe"] - b["sharpe"] >= 0.05,
        "wealth_ratio": c["final_equity"] / b["final_equity"] >= 1.02,
        "mdd_not_worse": c["mdd"] >= b["mdd"],
    }
    return {"candidate": c, "control": b, "tests": tests, "pass": bool(all(tests.values()))}


def output_manifest(root: Path, exclude: set[str] | None = None) -> dict[str, Any]:
    exclude = exclude or set()
    files = []
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        rel = path.relative_to(root).as_posix()
        if rel in exclude:
            continue
        files.append({"path": rel, "size": path.stat().st_size, "sha256": sha256_file(path)})
    tree = sha256_bytes("\n".join(f"{x['path']}\0{x['size']}\0{x['sha256']}" for x in files).encode("utf-8"))
    return {"version": VERSION, "files": files, "tree_sha256": tree}


def deterministic_zip(root: Path, destination: Path, exclusions: Iterable[str] = ()) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    excluded = set(exclusions)
    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for path in sorted(p for p in root.rglob("*") if p.is_file()):
            rel = path.relative_to(root).as_posix()
            if rel in excluded or rel.startswith((".git/", ".venv/", "__pycache__/", ".pytest_cache/")) or "/__pycache__/" in rel:
                continue
            if path.resolve() == destination.resolve():
                continue
            info = zipfile.ZipInfo(rel, (1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = (0o755 if path.suffix == ".command" else 0o644) << 16
            zf.writestr(info, path.read_bytes())


def baseline_identity(data: pd.DataFrame, cfg: Config, input_path: Path) -> dict[str, Any]:
    baseline = run_v10(data, cfg)
    payload = baseline.returns.to_csv(header=True, lineterminator="\n", float_format="%.12g").encode("utf-8")
    return {
        "name": "V10_ALIGNED_COMMON_OOS", "not_name": "V10_FULL_HISTORY",
        "aligned_start": baseline.returns.index[0], "aligned_end": baseline.returns.index[-1],
        "aligned_observations": len(baseline.returns), "input_path": input_path,
        "input_sha256": sha256_file(input_path), "aligned_v10_returns_sha256": sha256_bytes(payload),
        "aligned_metrics": performance_metrics(baseline.returns),
        "external_full_history_identity_required": True,
    }

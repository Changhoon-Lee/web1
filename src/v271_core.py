from __future__ import annotations

import hashlib
import json
import math
import os
import random
import statistics
import zipfile
from dataclasses import asdict, dataclass, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd

TRADING_DAYS = 365.25
NANO = 1_000_000_000


@dataclass(frozen=True)
class LabConfig:
    horizon_days: int = 30
    roll_days: int = 7
    target_dte_days: int = 30
    premium_budget: float = 0.05
    delta_band: float = 0.10
    option_half_spread: float = 0.025
    hedge_cost_bps: float = 7.0
    option_fee_rate: float = 0.0003
    option_fee_premium_cap: float = 0.125
    bootstrap_samples: int = 5000
    bootstrap_seed: int = 27101
    min_calendar_days: int = 365
    min_monthly_anchors: int = 12
    max_daily_gap_days: int = 3


@dataclass
class Position:
    opened_at: pd.Timestamp
    strike: float
    expiry: pd.Timestamp
    quantity: float
    hedge_units: float
    last_spot: float
    last_mid: float


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _json_default(value: Any) -> Any:
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        v = float(value)
        return None if not math.isfinite(v) else v
    if isinstance(value, (np.bool_,)):
        return bool(value)
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, float) and not math.isfinite(value):
        return None
    raise TypeError(type(value).__name__)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True, default=_json_default, allow_nan=False)
    path.write_text(text + "\n", encoding="utf-8")


def normal_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def normal_pdf(x: float) -> float:
    return math.exp(-0.5 * x * x) / math.sqrt(2.0 * math.pi)


def bs_straddle(spot: float, strike: float, years: float, sigma: float, rate: float = 0.0) -> dict[str, float]:
    if spot <= 0 or strike <= 0:
        raise ValueError("spot and strike must be positive")
    years = max(float(years), 1.0 / (TRADING_DAYS * 24.0))
    sigma = max(float(sigma), 1e-6)
    root_t = math.sqrt(years)
    d1 = (math.log(spot / strike) + (rate + 0.5 * sigma * sigma) * years) / (sigma * root_t)
    d2 = d1 - sigma * root_t
    disc = math.exp(-rate * years)
    call = spot * normal_cdf(d1) - strike * disc * normal_cdf(d2)
    put = strike * disc * normal_cdf(-d2) - spot * normal_cdf(-d1)
    call_delta = normal_cdf(d1)
    put_delta = call_delta - 1.0
    gamma = normal_pdf(d1) / (spot * sigma * root_t)
    return {
        "call": call,
        "put": put,
        "mid": call + put,
        "delta": call_delta + put_delta,
        "gamma": 2.0 * gamma,
    }


def deribit_option_fee_usd(spot: float, leg_premium_usd: float, quantity: float, cfg: LabConfig) -> float:
    per_contract = min(cfg.option_fee_rate * spot, cfg.option_fee_premium_cap * max(leg_premium_usd, 0.0))
    return max(quantity, 0.0) * per_contract


def _canonical_datetime_index(values: Iterable[Any]) -> pd.DatetimeIndex:
    idx = pd.to_datetime(values, utc=True, errors="coerce")
    if idx.isna().any():
        raise ValueError("invalid timestamp")
    return pd.DatetimeIndex(idx)


def normalize_index_frame(frame: pd.DataFrame) -> pd.DataFrame:
    required = {"timestamp", "index_price"}
    if not required.issubset(frame.columns):
        raise ValueError(f"missing columns: {sorted(required - set(frame.columns))}")
    out = frame.loc[:, ["timestamp", "index_price"]].copy()
    out["timestamp"] = _canonical_datetime_index(out["timestamp"])
    out["index_price"] = pd.to_numeric(out["index_price"], errors="coerce")
    out = out.dropna().drop_duplicates("timestamp", keep="last").sort_values("timestamp")
    out = out[out["index_price"] > 0]
    return out.set_index("timestamp")


def normalize_dvol_frame(frame: pd.DataFrame) -> pd.DataFrame:
    required = {"timestamp", "dvol"}
    if not required.issubset(frame.columns):
        raise ValueError(f"missing columns: {sorted(required - set(frame.columns))}")
    out = frame.loc[:, ["timestamp", "dvol"]].copy()
    out["timestamp"] = _canonical_datetime_index(out["timestamp"])
    out["dvol"] = pd.to_numeric(out["dvol"], errors="coerce")
    out = out.dropna().drop_duplicates("timestamp", keep="last").sort_values("timestamp")
    out = out[(out["dvol"] > 0) & (out["dvol"] < 500)]
    return out.set_index("timestamp")


def daily_market(index_frame: pd.DataFrame, dvol_frame: pd.DataFrame, cfg: LabConfig) -> pd.DataFrame:
    px = normalize_index_frame(index_frame)["index_price"].resample("1D").last().dropna()
    dv = normalize_dvol_frame(dvol_frame)["dvol"].resample("1D").last().dropna()
    merged = pd.concat([px, dv], axis=1).sort_index()
    merged["index_price"] = merged["index_price"].ffill(limit=cfg.max_daily_gap_days)
    merged["dvol"] = merged["dvol"].ffill(limit=cfg.max_daily_gap_days)
    merged = merged.dropna()
    if merged.empty:
        raise ValueError("no overlapping index and DVOL observations")
    merged["log_return"] = np.log(merged["index_price"]).diff().fillna(0.0)
    return merged


def monthly_variance_anchors(market: pd.DataFrame, cfg: LabConfig) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    grouped = market.groupby([market.index.year, market.index.month], sort=True)
    for (_, _), grp in grouped:
        anchor = grp.index[0]
        end_target = anchor + pd.Timedelta(days=cfg.horizon_days)
        future = market.loc[(market.index > anchor) & (market.index <= end_target)]
        if len(future) < max(15, int(cfg.horizon_days * 0.60)):
            continue
        lr = future["log_return"].to_numpy(dtype=float)
        rv_var = float(np.mean(lr * lr) * TRADING_DAYS)
        iv = float(market.loc[anchor, "dvol"]) / 100.0
        iv_var = iv * iv
        payoff = rv_var - iv_var
        rows.append({
            "anchor": anchor,
            "horizon_end": future.index[-1],
            "spot": float(market.loc[anchor, "index_price"]),
            "implied_vol": iv,
            "realized_vol": math.sqrt(max(rv_var, 0.0)),
            "implied_variance": iv_var,
            "realized_variance": rv_var,
            "long_variance_payoff": payoff,
            "scaled_30d_payoff": 0.5 * payoff * cfg.horizon_days / TRADING_DAYS,
            "observations": int(len(future)),
        })
    return pd.DataFrame(rows)


def newey_west_mean(values: np.ndarray, max_lag: int = 3) -> dict[str, float]:
    x = np.asarray(values, dtype=float)
    x = x[np.isfinite(x)]
    n = len(x)
    if n < 3:
        return {"mean": float(np.mean(x)) if n else float("nan"), "se": float("nan"), "t": float("nan")}
    centered = x - x.mean()
    gamma0 = float(np.dot(centered, centered) / n)
    variance = gamma0
    lag = min(max_lag, n - 1)
    for k in range(1, lag + 1):
        gamma = float(np.dot(centered[k:], centered[:-k]) / n)
        weight = 1.0 - k / (lag + 1.0)
        variance += 2.0 * weight * gamma
    se = math.sqrt(max(variance, 0.0) / n)
    return {"mean": float(x.mean()), "se": se, "t": float(x.mean() / se) if se > 0 else float("nan")}


def bootstrap_mean(values: np.ndarray, cfg: LabConfig) -> dict[str, float]:
    x = np.asarray(values, dtype=float)
    x = x[np.isfinite(x)]
    if len(x) < 2:
        return {"mean": float(np.mean(x)) if len(x) else float("nan"), "lower": float("nan"), "upper": float("nan"), "p_positive": float("nan")}
    rng = np.random.default_rng(cfg.bootstrap_seed)
    draws = rng.choice(x, size=(cfg.bootstrap_samples, len(x)), replace=True).mean(axis=1)
    return {
        "mean": float(x.mean()),
        "lower": float(np.quantile(draws, 0.025)),
        "upper": float(np.quantile(draws, 0.975)),
        "p_positive": float(np.mean(draws > 0)),
    }


def _option_fee_pair(spot: float, valuation: dict[str, float], quantity: float, cfg: LabConfig) -> float:
    return deribit_option_fee_usd(spot, valuation["call"], quantity, cfg) + deribit_option_fee_usd(spot, valuation["put"], quantity, cfg)


def simulate_synthetic_straddle(market: pd.DataFrame, cfg: LabConfig, *, hedged: bool = True) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, float]]:
    if len(market) < 60:
        raise ValueError("at least 60 daily observations required")
    cash = 1.0
    pos: Position | None = None
    rows: list[dict[str, Any]] = []
    trades: list[dict[str, Any]] = []
    attribution = {
        "option_mtm": 0.0,
        "hedge_pnl": 0.0,
        "option_spread": 0.0,
        "option_fees": 0.0,
        "hedge_cost": 0.0,
    }

    def close_position(ts: pd.Timestamp, spot: float, sigma: float, reason: str) -> None:
        nonlocal cash, pos
        if pos is None:
            return
        years = max((pos.expiry - ts).total_seconds() / (365.25 * 86400.0), 1.0 / (365.25 * 24.0))
        val = bs_straddle(spot, pos.strike, years, sigma)
        bid = val["mid"] * (1.0 - cfg.option_half_spread)
        spread_loss = pos.quantity * (val["mid"] - bid)
        fee = _option_fee_pair(spot, val, pos.quantity, cfg)
        cash += pos.quantity * bid - fee
        attribution["option_spread"] -= spread_loss
        attribution["option_fees"] -= fee
        if hedged and pos.hedge_units != 0.0:
            hcost = abs(pos.hedge_units) * spot * cfg.hedge_cost_bps / 10000.0
            cash -= hcost
            attribution["hedge_cost"] -= hcost
        trades.append({"timestamp": ts, "event": "close", "reason": reason, "spot": spot, "strike": pos.strike, "quantity": pos.quantity, "option_mid": val["mid"], "option_exec": bid, "fee": fee, "hedge_units": pos.hedge_units})
        pos = None

    for i, (ts, row) in enumerate(market.iterrows()):
        spot = float(row["index_price"])
        sigma = float(row["dvol"]) / 100.0
        if pos is not None:
            hedge_pnl = pos.hedge_units * (spot - pos.last_spot)
            cash += hedge_pnl
            attribution["hedge_pnl"] += hedge_pnl
            years = max((pos.expiry - ts).total_seconds() / (365.25 * 86400.0), 1.0 / (365.25 * 24.0))
            val = bs_straddle(spot, pos.strike, years, sigma)
            attribution["option_mtm"] += pos.quantity * (val["mid"] - pos.last_mid)
            desired = -pos.quantity * val["delta"] if hedged else 0.0
            if hedged and abs(desired - pos.hedge_units) > cfg.delta_band * max(pos.quantity, 1e-12):
                change = desired - pos.hedge_units
                hcost = abs(change) * spot * cfg.hedge_cost_bps / 10000.0
                cash -= hcost
                attribution["hedge_cost"] -= hcost
                trades.append({"timestamp": ts, "event": "hedge", "reason": "delta_band", "spot": spot, "strike": pos.strike, "quantity": pos.quantity, "option_mid": val["mid"], "option_exec": val["mid"], "fee": hcost, "hedge_units": desired})
                pos.hedge_units = desired
            pos.last_spot = spot
            pos.last_mid = val["mid"]
            age = (ts - pos.opened_at).days
            dte = (pos.expiry - ts).days
            if age >= cfg.roll_days or dte <= cfg.target_dte_days - cfg.roll_days:
                close_position(ts, spot, sigma, "scheduled_roll")

        if pos is None and i < len(market) - 1:
            expiry = ts + pd.Timedelta(days=cfg.target_dte_days)
            strike = spot
            val = bs_straddle(spot, strike, cfg.target_dte_days / 365.25, sigma)
            ask = val["mid"] * (1.0 + cfg.option_half_spread)
            equity_pre = max(cash, 1e-9)
            quantity = cfg.premium_budget * equity_pre / max(ask, 1e-12)
            fee = _option_fee_pair(spot, val, quantity, cfg)
            cash -= quantity * ask + fee
            attribution["option_spread"] -= quantity * (ask - val["mid"])
            attribution["option_fees"] -= fee
            hedge_units = -quantity * val["delta"] if hedged else 0.0
            if hedged and hedge_units != 0.0:
                hcost = abs(hedge_units) * spot * cfg.hedge_cost_bps / 10000.0
                cash -= hcost
                attribution["hedge_cost"] -= hcost
            pos = Position(ts, strike, expiry, quantity, hedge_units, spot, val["mid"])
            trades.append({"timestamp": ts, "event": "open", "reason": "scheduled_open", "spot": spot, "strike": strike, "quantity": quantity, "option_mid": val["mid"], "option_exec": ask, "fee": fee, "hedge_units": hedge_units})

        option_mark = 0.0
        hedge_units = 0.0
        if pos is not None:
            years = max((pos.expiry - ts).total_seconds() / (365.25 * 86400.0), 1.0 / (365.25 * 24.0))
            option_mark = pos.quantity * bs_straddle(spot, pos.strike, years, sigma)["mid"]
            hedge_units = pos.hedge_units
        equity = cash + option_mark
        rows.append({"timestamp": ts, "equity": equity, "cash": cash, "option_mark": option_mark, "spot": spot, "dvol": sigma * 100.0, "hedge_units": hedge_units, "position_open": int(pos is not None)})

    last_ts = market.index[-1]
    last_spot = float(market.iloc[-1]["index_price"])
    last_sigma = float(market.iloc[-1]["dvol"]) / 100.0
    close_position(last_ts, last_spot, last_sigma, "final_close")
    rows.append({"timestamp": last_ts + pd.Timedelta(microseconds=1), "equity": cash, "cash": cash, "option_mark": 0.0, "spot": last_spot, "dvol": last_sigma * 100.0, "hedge_units": 0.0, "position_open": 0})
    curve = pd.DataFrame(rows).set_index("timestamp")
    ledger = pd.DataFrame(trades)
    return curve, ledger, attribution


def performance_metrics(equity: pd.Series) -> dict[str, float]:
    eq = pd.Series(equity, dtype=float).dropna()
    if len(eq) < 2 or (eq <= 0).any():
        return {"wealth": float(eq.iloc[-1]) if len(eq) else float("nan"), "cagr": float("nan"), "sharpe": float("nan"), "mdd": float("nan")}
    returns = eq.pct_change().dropna()
    span_days = max((eq.index[-1] - eq.index[0]).total_seconds() / 86400.0, 1.0)
    cagr = float((eq.iloc[-1] / eq.iloc[0]) ** (365.25 / span_days) - 1.0)
    vol = float(returns.std(ddof=1))
    sharpe = float(returns.mean() / vol * math.sqrt(TRADING_DAYS)) if vol > 0 else float("nan")
    dd = eq / eq.cummax() - 1.0
    return {"wealth": float(eq.iloc[-1] / eq.iloc[0]), "cagr": cagr, "sharpe": sharpe, "mdd": float(dd.min())}


def continuity_metrics(market: pd.DataFrame) -> dict[str, float]:
    if market.empty:
        return {"calendar_days": 0, "active_days": 0, "coverage": 0.0, "max_gap_days": float("inf")}
    idx = pd.DatetimeIndex(market.index).sort_values()
    calendar = int((idx[-1].normalize() - idx[0].normalize()).days + 1)
    unique_days = len(idx.normalize().unique())
    gaps = idx.to_series().diff().dropna().dt.total_seconds() / 86400.0
    return {"calendar_days": calendar, "active_days": unique_days, "coverage": float(unique_days / max(calendar, 1)), "max_gap_days": float(gaps.max()) if len(gaps) else 0.0}


def _strict_result_status(market: pd.DataFrame, anchors: pd.DataFrame, hedged_metrics: dict[str, float], cost2_metrics: dict[str, float], cfg: LabConfig) -> dict[str, str]:
    continuity = continuity_metrics(market)
    sufficient = continuity["calendar_days"] >= cfg.min_calendar_days and len(anchors) >= cfg.min_monthly_anchors
    if not sufficient:
        model_status = "OPEN_FREE_DATA_INSUFFICIENT"
    else:
        mean_payoff = float(anchors["long_variance_payoff"].mean()) if len(anchors) else float("nan")
        if mean_payoff > 0 and hedged_metrics.get("wealth", 0) > 1.0 and cost2_metrics.get("wealth", 0) > 1.0:
            model_status = "OPEN_FREE_MODEL_FEASIBILITY_POSITIVE_EXECUTION_UNVERIFIED"
        else:
            model_status = "OPEN_FREE_LONG_GAMMA_MODEL_REJECTED"
    return {
        "model_status": model_status,
        "deployable_status": "BLOCKED_NO_HISTORICAL_OPTION_BID_ASK_CHAIN",
        "historical_claim": "MODEL_BASED_DIAGNOSTIC_ONLY",
    }


def run_open_free_lab(index_frame: pd.DataFrame, dvol_frame: pd.DataFrame, cfg: LabConfig | None = None) -> dict[str, Any]:
    cfg = cfg or LabConfig()
    market = daily_market(index_frame, dvol_frame, cfg)
    anchors = monthly_variance_anchors(market, cfg)
    vrp = anchors["long_variance_payoff"].to_numpy(dtype=float) if len(anchors) else np.array([], dtype=float)
    base_curve, base_ledger, base_attr = simulate_synthetic_straddle(market, cfg, hedged=True)
    unhedged_curve, unhedged_ledger, unhedged_attr = simulate_synthetic_straddle(market, cfg, hedged=False)
    cost2_cfg = replace(cfg, option_half_spread=cfg.option_half_spread * 2.0, hedge_cost_bps=cfg.hedge_cost_bps * 2.0)
    cost3_cfg = replace(cfg, option_half_spread=cfg.option_half_spread * 3.0, hedge_cost_bps=cfg.hedge_cost_bps * 3.0)
    cost2_curve, cost2_ledger, cost2_attr = simulate_synthetic_straddle(market, cost2_cfg, hedged=True)
    cost3_curve, cost3_ledger, cost3_attr = simulate_synthetic_straddle(market, cost3_cfg, hedged=True)
    base_metrics = performance_metrics(base_curve["equity"])
    unhedged_metrics = performance_metrics(unhedged_curve["equity"])
    cost2_metrics = performance_metrics(cost2_curve["equity"])
    cost3_metrics = performance_metrics(cost3_curve["equity"])
    result = {
        "protocol": "27.1.0",
        "config": asdict(cfg),
        "continuity": continuity_metrics(market),
        "anchors": int(len(anchors)),
        "variance_risk_premium": {
            "newey_west": newey_west_mean(vrp),
            "bootstrap": bootstrap_mean(vrp, cfg),
            "positive_fraction": float(np.mean(vrp > 0)) if len(vrp) else float("nan"),
        },
        "strategies": {
            "synthetic_delta_hedged": base_metrics,
            "synthetic_unhedged": unhedged_metrics,
            "synthetic_delta_hedged_cost_2x": cost2_metrics,
            "synthetic_delta_hedged_cost_3x": cost3_metrics,
        },
        "attribution": {
            "synthetic_delta_hedged": base_attr,
            "synthetic_unhedged": unhedged_attr,
            "synthetic_delta_hedged_cost_2x": cost2_attr,
            "synthetic_delta_hedged_cost_3x": cost3_attr,
        },
    }
    result["status"] = _strict_result_status(market, anchors, base_metrics, cost2_metrics, cfg)
    result["frames"] = {
        "market": market,
        "anchors": anchors,
        "base_curve": base_curve,
        "base_ledger": base_ledger,
        "unhedged_curve": unhedged_curve,
        "unhedged_ledger": unhedged_ledger,
        "cost2_curve": cost2_curve,
        "cost2_ledger": cost2_ledger,
        "cost3_curve": cost3_curve,
        "cost3_ledger": cost3_ledger,
    }
    return result


def exact_ledger(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy().reset_index()
    for col in out.columns:
        if pd.api.types.is_datetime64_any_dtype(out[col]):
            out[col] = pd.to_datetime(out[col], utc=True).dt.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        elif pd.api.types.is_float_dtype(out[col]):
            out[col] = out[col].map(lambda x: int(round(float(x) * NANO)) if pd.notna(x) and math.isfinite(float(x)) else None)
        elif pd.api.types.is_bool_dtype(out[col]):
            out[col] = out[col].astype(int)
    return out


def build_manifest(root: Path, exclude: set[str] | None = None) -> dict[str, Any]:
    exclude = exclude or set()
    files = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(root).as_posix()
        if rel in exclude or rel.startswith("runtime/") or "__pycache__" in rel or rel.startswith(".venv/"):
            continue
        files.append({"path": rel, "size": path.stat().st_size, "sha256": sha256_file(path)})
    return {"file_count": len(files), "files": files}


def verify_manifest(root: Path, manifest: dict[str, Any]) -> tuple[bool, list[str]]:
    errors: list[str] = []
    for item in manifest.get("files", []):
        path = root / item["path"]
        if not path.exists():
            errors.append(f"missing:{item['path']}")
            continue
        if path.stat().st_size != item["size"]:
            errors.append(f"size:{item['path']}")
        if sha256_file(path) != item["sha256"]:
            errors.append(f"sha:{item['path']}")
    return not errors, errors


def deterministic_zip(source_root: Path, destination: Path, exclude_prefixes: tuple[str, ...] = (".venv/", "runtime/", "__pycache__/")) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_STORED) as zf:
        for path in sorted(source_root.rglob("*")):
            if not path.is_file():
                continue
            rel = path.relative_to(source_root).as_posix()
            if any(rel.startswith(prefix) or prefix in rel for prefix in exclude_prefixes):
                continue
            info = zipfile.ZipInfo(rel)
            info.date_time = (2020, 1, 1, 0, 0, 0)
            info.compress_type = zipfile.ZIP_STORED
            info.external_attr = 0o100644 << 16
            zf.writestr(info, path.read_bytes())

#!/usr/bin/env python3
"""V27 Deribit long-gamma and delta-hedging research core.

The module is deliberately fail-closed. It never manufactures historical option
quotes, never substitutes marks for executable entry/exit prices, and never
turns sparse monthly samples into a continuous backtest.
"""
from __future__ import annotations

import hashlib
import json
import math
import shutil
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Iterator, Sequence

import numpy as np
import pandas as pd

VERSION = "27.0.0"
YEAR_SECONDS = 365.25 * 24.0 * 3600.0
NANO = 1_000_000_000


@dataclass(frozen=True)
class Config:
    currency: str = "BTC"
    initial_equity: float = 100_000.0
    snapshot_minutes: int = 30
    target_dte: float = 30.0
    minimum_dte: float = 21.0
    maximum_dte: float = 45.0
    exit_dte: float = 7.0
    roll_days: int = 7
    entry_hour_utc: int = 8
    premium_budget_fraction: float = 0.05
    maximum_spread_fraction: float = 0.25
    maximum_moneyness_error: float = 0.025
    maximum_quote_age_minutes: int = 90
    minimum_contract_amount: float = 0.1
    delta_band_per_contract: float = 0.10
    maximum_hedge_minutes: int = 30
    hedge_latency_bars: int = 1
    option_fee_rate_underlying: float = 0.0003
    option_fee_premium_cap: float = 0.125
    option_delivery_fee_rate_underlying: float = 0.00015
    perp_taker_fee_bps: float = 5.0
    perp_half_spread_bps: float = 1.0
    funding_annual_assumption: float = 0.03
    minimum_backtest_days: int = 90
    minimum_rolls: int = 8
    concentration_limit: float = 0.50
    random_seed: int = 20260720

    def validate(self) -> None:
        if self.currency not in {"BTC", "ETH"}:
            raise ValueError("currency must be BTC or ETH")
        if self.initial_equity <= 0:
            raise ValueError("initial_equity must be positive")
        if self.snapshot_minutes <= 0 or 1440 % self.snapshot_minutes:
            raise ValueError("snapshot_minutes must divide one day")
        if not 0 < self.exit_dte < self.minimum_dte <= self.target_dte <= self.maximum_dte:
            raise ValueError("invalid DTE ordering")
        if not 0 < self.premium_budget_fraction < 1:
            raise ValueError("invalid premium budget")
        if not 0 < self.maximum_spread_fraction < 1:
            raise ValueError("invalid spread bound")
        if self.hedge_latency_bars < 0:
            raise ValueError("negative latency")
        if self.minimum_contract_amount <= 0:
            raise ValueError("invalid minimum amount")


@dataclass
class Position:
    call_symbol: str
    put_symbol: str
    expiry: pd.Timestamp
    strike: float
    quantity: float
    opened_at: pd.Timestamp
    next_roll_at: pd.Timestamp


@dataclass
class BacktestResult:
    name: str
    ledger: pd.DataFrame
    trades: pd.DataFrame
    diagnostics: pd.DataFrame
    metrics: dict[str, Any]
    status: str


ALIASES = {
    "timestamp": ("timestamp", "time", "datetime", "local_timestamp"),
    "symbol": ("symbol", "instrument", "instrument_name"),
    "type": ("type", "option_type", "side_type"),
    "strike_price": ("strike_price", "strike"),
    "expiration": ("expiration", "expiration_timestamp", "expiry"),
    "bid_price": ("bid_price", "best_bid_price", "bid"),
    "ask_price": ("ask_price", "best_ask_price", "ask"),
    "bid_amount": ("bid_amount", "best_bid_amount"),
    "ask_amount": ("ask_amount", "best_ask_amount"),
    "mark_price": ("mark_price", "mark"),
    "mark_iv": ("mark_iv", "iv", "implied_volatility"),
    "bid_iv": ("bid_iv",),
    "ask_iv": ("ask_iv",),
    "underlying_price": ("underlying_price", "index_price", "forward_price", "spot"),
    "underlying_index": ("underlying_index",),
    "open_interest": ("open_interest", "oi"),
    "delta": ("delta",),
    "gamma": ("gamma",),
    "vega": ("vega",),
    "theta": ("theta",),
}


def _find_column(frame: pd.DataFrame, names: Sequence[str]) -> str | None:
    lookup = {str(c).strip().lower(): str(c) for c in frame.columns}
    for name in names:
        if name.lower() in lookup:
            return lookup[name.lower()]
    return None


def _datetime_from_any(values: pd.Series) -> pd.Series:
    if pd.api.types.is_numeric_dtype(values):
        x = pd.to_numeric(values, errors="coerce")
        valid = x.dropna().abs()
        median = float(valid.median()) if len(valid) else 0.0
        if median > 1e17:
            unit = "ns"
        elif median > 1e14:
            unit = "us"
        elif median > 1e11:
            unit = "ms"
        elif median > 1e8:
            unit = "s"
        else:
            return pd.to_datetime(x.astype("Int64").astype(str), utc=True, errors="coerce")
        return pd.to_datetime(x, unit=unit, utc=True, errors="coerce")
    return pd.to_datetime(values, utc=True, errors="coerce")


def canonicalize_chain(frame: pd.DataFrame, currency: str = "BTC") -> pd.DataFrame:
    out = pd.DataFrame(index=frame.index)
    for canonical, names in ALIASES.items():
        col = _find_column(frame, names)
        if col is not None:
            out[canonical] = frame[col]
    required = {"timestamp", "symbol", "type", "strike_price", "expiration", "bid_price", "ask_price", "underlying_price"}
    missing = required.difference(out.columns)
    if missing:
        raise ValueError(f"missing option-chain fields: {sorted(missing)}")
    out["timestamp"] = _datetime_from_any(out["timestamp"])
    out["expiration"] = _datetime_from_any(out["expiration"])
    out["symbol"] = out["symbol"].astype(str).str.upper().str.strip()
    out["type"] = out["type"].astype(str).str.lower().replace({"c": "call", "p": "put"})
    numeric = [c for c in ALIASES if c in out.columns and c not in {"timestamp", "symbol", "type", "expiration", "underlying_index"}]
    for col in numeric:
        out[col] = pd.to_numeric(out[col], errors="coerce")
    for col in ("bid_amount", "ask_amount", "mark_price", "mark_iv", "bid_iv", "ask_iv", "open_interest", "delta", "gamma", "vega", "theta"):
        if col not in out:
            out[col] = np.nan
    prefix = currency.upper()
    out = out[out["symbol"].str.startswith(prefix)]
    out = out[out["type"].isin(["call", "put"])]
    out = out.dropna(subset=["timestamp", "expiration", "strike_price", "bid_price", "ask_price", "underlying_price"])
    out = out[(out["strike_price"] > 0) & (out["underlying_price"] > 0)]
    out = out[(out["bid_price"] >= 0) & (out["ask_price"] > 0) & (out["ask_price"] >= out["bid_price"])]
    out["settlement_type"] = np.where(out["symbol"].str.contains("_USDC-", regex=False), "linear", "inverse")
    out["dte"] = (out["expiration"] - out["timestamp"]).dt.total_seconds() / 86400.0
    out["moneyness_error"] = (out["strike_price"] / out["underlying_price"] - 1.0).abs()
    out = out.sort_values(["timestamp", "symbol"]).drop_duplicates(["timestamp", "symbol"], keep="last")
    return out.reset_index(drop=True)


def normal_cdf(x: float | np.ndarray) -> float | np.ndarray:
    arr = np.asarray(x, dtype=float)
    result = 0.5 * (1.0 + np.vectorize(math.erf)(arr / math.sqrt(2.0)))
    return float(result) if np.ndim(x) == 0 else result


def black_scholes_usd(spot: float, strike: float, years: float, volatility: float, rate: float, option_type: str) -> tuple[float, float, float]:
    if spot <= 0 or strike <= 0:
        raise ValueError("spot and strike must be positive")
    if years <= 0 or volatility <= 0:
        intrinsic = max(spot - strike, 0.0) if option_type == "call" else max(strike - spot, 0.0)
        delta = 1.0 if option_type == "call" and spot > strike else -1.0 if option_type == "put" and spot < strike else 0.0
        return intrinsic, delta, 0.0
    root_t = math.sqrt(years)
    d1 = (math.log(spot / strike) + (rate + 0.5 * volatility * volatility) * years) / (volatility * root_t)
    d2 = d1 - volatility * root_t
    nd1 = float(normal_cdf(d1))
    nd2 = float(normal_cdf(d2))
    discount = math.exp(-rate * years)
    if option_type == "call":
        price = spot * nd1 - strike * discount * nd2
        delta = nd1
    elif option_type == "put":
        price = strike * discount * float(normal_cdf(-d2)) - spot * float(normal_cdf(-d1))
        delta = nd1 - 1.0
    else:
        raise ValueError("option_type must be call or put")
    density = math.exp(-0.5 * d1 * d1) / math.sqrt(2.0 * math.pi)
    gamma = density / (spot * volatility * root_t)
    return max(price, 0.0), delta, gamma


def option_price_usd(row: pd.Series | dict[str, Any], price: float) -> float:
    settlement = str(row["settlement_type"])
    spot = float(row["underlying_price"])
    return float(price) if settlement == "linear" else float(price) * spot


def option_fee_usd(row: pd.Series | dict[str, Any], price: float, quantity: float, cfg: Config, multiplier: float = 1.0, delivery: bool = False) -> float:
    spot = float(row["underlying_price"])
    settlement = str(row["settlement_type"])
    rate = cfg.option_delivery_fee_rate_underlying if delivery else cfg.option_fee_rate_underlying
    if settlement == "inverse":
        fee_coin = min(rate, cfg.option_fee_premium_cap * max(float(price), 0.0)) * abs(quantity)
        return fee_coin * spot * multiplier
    premium_usd = max(float(price), 0.0)
    return min(rate * spot, cfg.option_fee_premium_cap * premium_usd) * abs(quantity) * multiplier


def intrinsic_usd(option_type: str, spot: float, strike: float) -> float:
    return max(spot - strike, 0.0) if option_type == "call" else max(strike - spot, 0.0)


def quote_mid(row: pd.Series | dict[str, Any]) -> float:
    bid, ask = float(row["bid_price"]), float(row["ask_price"])
    return (bid + ask) / 2.0


def spread_fraction(row: pd.Series | dict[str, Any]) -> float:
    mid = quote_mid(row)
    return (float(row["ask_price"]) - float(row["bid_price"])) / mid if mid > 0 else math.inf


def select_atm_straddle(snapshot: pd.DataFrame, cfg: Config) -> dict[str, Any] | None:
    if snapshot.empty:
        return None
    x = snapshot.copy()
    x = x[(x["dte"] >= cfg.minimum_dte) & (x["dte"] <= cfg.maximum_dte)]
    x = x[x["moneyness_error"] <= cfg.maximum_moneyness_error]
    x = x[x.apply(spread_fraction, axis=1) <= cfg.maximum_spread_fraction]
    if x.empty:
        return None
    calls = x[x["type"] == "call"]
    puts = x[x["type"] == "put"]
    pair = calls.merge(puts, on=["timestamp", "expiration", "strike_price", "settlement_type"], suffixes=("_call", "_put"))
    if pair.empty:
        return None
    pair["dte_score"] = (pair["dte_call"] - cfg.target_dte).abs()
    pair["money_score"] = pair[["moneyness_error_call", "moneyness_error_put"]].max(axis=1)
    pair["spread_score"] = (
        (pair["ask_price_call"] - pair["bid_price_call"]) / ((pair["ask_price_call"] + pair["bid_price_call"]) / 2.0)
        + (pair["ask_price_put"] - pair["bid_price_put"]) / ((pair["ask_price_put"] + pair["bid_price_put"]) / 2.0)
    )
    pair = pair.sort_values(["dte_score", "money_score", "spread_score", "expiration", "strike_price"])
    row = pair.iloc[0]
    return {
        "timestamp": row["timestamp"],
        "expiration": row["expiration"],
        "strike": float(row["strike_price"]),
        "call_symbol": str(row["symbol_call"]),
        "put_symbol": str(row["symbol_put"]),
    }


def _read_csv_chunks(path: Path, chunksize: int = 200_000) -> Iterator[pd.DataFrame]:
    if path.suffix == ".parquet":
        yield pd.read_parquet(path)
        return
    yield from pd.read_csv(path, compression="infer", chunksize=chunksize, low_memory=False)


def prepare_compact_file(source: Path, destination: Path, cfg: Config) -> dict[str, Any]:
    pieces: list[pd.DataFrame] = []
    raw_rows = 0
    for chunk in _read_csv_chunks(source):
        raw_rows += len(chunk)
        frame = canonicalize_chain(chunk, cfg.currency)
        frame = frame[(frame["dte"] >= max(cfg.exit_dte - 2.0, 0.0)) & (frame["dte"] <= cfg.maximum_dte + 5.0)]
        frame = frame[frame["moneyness_error"] <= 0.30]
        if frame.empty:
            continue
        frame["timestamp"] = frame["timestamp"].dt.floor(f"{cfg.snapshot_minutes}min")
        keep = frame.sort_values("timestamp").groupby(["timestamp", "symbol"], as_index=False).tail(1)
        pieces.append(keep)
    if not pieces:
        raise ValueError(f"no usable option rows in {source}")
    compact = pd.concat(pieces, ignore_index=True)
    compact = compact.sort_values(["timestamp", "symbol"]).drop_duplicates(["timestamp", "symbol"], keep="last")
    destination.parent.mkdir(parents=True, exist_ok=True)
    compact.to_csv(destination, index=False, compression={"method": "gzip", "mtime": 0}, float_format="%.12g")
    return {"source": str(source), "destination": str(destination), "raw_rows": raw_rows, "compact_rows": len(compact), "sha256": sha256_file(destination)}


def discover_chain_files(root: Path) -> list[Path]:
    root = root.expanduser().resolve()
    if root.is_file():
        return [root]
    patterns = ("*options_chain*.csv.gz", "*OPTIONS*.csv.gz", "*.compact.csv.gz", "*.parquet", "*.csv")
    files: list[Path] = []
    for pattern in patterns:
        files.extend(root.rglob(pattern))
    return sorted({p.resolve() for p in files if p.is_file()})


def load_compact_data(paths: Iterable[Path], cfg: Config) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    for path in paths:
        frame = pd.read_parquet(path) if path.suffix == ".parquet" else pd.read_csv(path, compression="infer", low_memory=False)
        frames.append(canonicalize_chain(frame, cfg.currency))
    if not frames:
        raise FileNotFoundError("no option-chain files")
    out = pd.concat(frames, ignore_index=True)
    out["timestamp"] = out["timestamp"].dt.floor(f"{cfg.snapshot_minutes}min")
    out = out.sort_values(["timestamp", "symbol"]).drop_duplicates(["timestamp", "symbol"], keep="last")
    return out.reset_index(drop=True)


def _row_dict(row: pd.Series) -> dict[str, Any]:
    return {str(k): row[k] for k in row.index}


def _safe_quote(last_quotes: dict[str, dict[str, Any]], symbol: str, timestamp: pd.Timestamp, cfg: Config) -> dict[str, Any] | None:
    row = last_quotes.get(symbol)
    if row is None:
        return None
    age = (timestamp - pd.Timestamp(row["timestamp"])).total_seconds() / 60.0
    return row if 0 <= age <= cfg.maximum_quote_age_minutes else None


def _option_value_usd(position: Position | None, last_quotes: dict[str, dict[str, Any]], timestamp: pd.Timestamp, cfg: Config, side: str = "mid", fallback_spot: float | None = None) -> float:
    if position is None:
        return 0.0
    total = 0.0
    for option_type, symbol in (("call", position.call_symbol), ("put", position.put_symbol)):
        row = _safe_quote(last_quotes, symbol, timestamp, cfg)
        if row is None:
            if timestamp >= position.expiry and fallback_spot is not None:
                total += intrinsic_usd(option_type, fallback_spot, position.strike) * position.quantity
                continue
            return float("nan")
        price = quote_mid(row) if side == "mid" else float(row["bid_price"] if side == "bid" else row["ask_price"])
        total += option_price_usd(row, price) * position.quantity
    return total


def _position_delta(position: Position | None, last_quotes: dict[str, dict[str, Any]], timestamp: pd.Timestamp, cfg: Config) -> float:
    if position is None:
        return 0.0
    delta = 0.0
    for symbol in (position.call_symbol, position.put_symbol):
        row = _safe_quote(last_quotes, symbol, timestamp, cfg)
        if row is None:
            return float("nan")
        value = row.get("delta")
        if value is None or not math.isfinite(float(value)):
            iv = row.get("mark_iv")
            if iv is None or not math.isfinite(float(iv)) or float(iv) <= 0:
                return float("nan")
            years = max((position.expiry - timestamp).total_seconds() / YEAR_SECONDS, 1e-9)
            _, value, _ = black_scholes_usd(float(row["underlying_price"]), position.strike, years, float(iv) / 100.0, 0.0, str(row["type"]))
        delta += float(value) * position.quantity
    return delta


def _performance_metrics(ledger: pd.DataFrame) -> dict[str, Any]:
    if ledger.empty:
        return {"observations": 0, "final_equity": 1.0, "cagr": 0.0, "sharpe": 0.0, "mdd": 0.0}
    equity = ledger.set_index("timestamp")["equity"].astype(float)
    returns = equity.pct_change().fillna(0.0)
    years = max((equity.index[-1] - equity.index[0]).total_seconds() / YEAR_SECONDS, 1.0 / 365.25)
    final_ratio = float(equity.iloc[-1] / equity.iloc[0])
    cagr = final_ratio ** (1.0 / years) - 1.0 if final_ratio > 0 else -1.0
    seconds = returns.index.to_series().diff().dt.total_seconds().dropna()
    period_seconds = float(seconds.median()) if len(seconds) else 1800.0
    periods_year = YEAR_SECONDS / max(period_seconds, 1.0)
    sd = float(returns.std(ddof=1))
    sharpe = float(returns.mean() / sd * math.sqrt(periods_year)) if sd > 0 else 0.0
    dd = equity / equity.cummax() - 1.0
    daily = equity.resample("1D").last().dropna().pct_change().dropna()
    concentration = 0.0
    if len(daily) and float(daily[daily > 0].sum()) > 0:
        k = max(1, int(math.ceil(len(daily) * 0.05)))
        concentration = float(daily.nlargest(k).sum() / daily[daily > 0].sum())
    return {
        "observations": int(len(ledger)),
        "start": equity.index[0],
        "end": equity.index[-1],
        "calendar_days": float((equity.index[-1] - equity.index[0]).total_seconds() / 86400.0),
        "final_equity": float(equity.iloc[-1]),
        "final_wealth_ratio": final_ratio,
        "cagr": float(cagr),
        "sharpe": sharpe,
        "mdd": float(dd.min()),
        "top_5pct_positive_day_concentration": concentration,
    }


def run_long_gamma(data: pd.DataFrame, cfg: Config, name: str = "V27_PRIMARY", cost_multiplier: float = 1.0, latency_bars: int | None = None, hedge_enabled: bool = True) -> BacktestResult:
    cfg.validate()
    if data.empty:
        return BacktestResult(name, pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), _performance_metrics(pd.DataFrame()), "INSUFFICIENT_HISTORICAL_OPTIONS_DATA")
    latency = cfg.hedge_latency_bars if latency_bars is None else int(latency_bars)
    grouped = list(data.sort_values(["timestamp", "symbol"]).groupby("timestamp", sort=True))
    cash = cfg.initial_equity
    position: Position | None = None
    hedge_qty = 0.0
    pending_hedges: list[tuple[int, float, str]] = []
    last_quotes: dict[str, dict[str, Any]] = {}
    prev_spot: float | None = None
    prev_ts: pd.Timestamp | None = None
    last_hedge_ts: pd.Timestamp | None = None
    last_entry_day: Any = None
    ledger_rows: list[dict[str, Any]] = []
    trade_rows: list[dict[str, Any]] = []
    diagnostic_rows: list[dict[str, Any]] = []
    cumulative_fees = 0.0
    cumulative_funding = 0.0
    roll_count = 0
    skipped_entries = 0

    def trade_hedge(ts: pd.Timestamp, spot: float, target: float, reason: str) -> None:
        nonlocal cash, hedge_qty, cumulative_fees, last_hedge_ts
        change = target - hedge_qty
        if abs(change) <= 1e-14:
            return
        rate = (cfg.perp_taker_fee_bps + cfg.perp_half_spread_bps) / 10_000.0 * cost_multiplier
        cost = abs(change) * spot * rate
        cash -= cost
        cumulative_fees += cost
        hedge_qty = target
        last_hedge_ts = ts
        trade_rows.append({"timestamp": ts, "kind": "HEDGE", "symbol": f"{cfg.currency}-PERPETUAL", "quantity": change, "price_usd": spot, "cash_flow": -cost, "fee_usd": cost, "reason": reason})

    def close_options(ts: pd.Timestamp, spot: float, reason: str) -> bool:
        nonlocal cash, position, cumulative_fees
        if position is None:
            return True
        proceeds = 0.0
        fees = 0.0
        staged: list[dict[str, Any]] = []
        for option_type, symbol in (("call", position.call_symbol), ("put", position.put_symbol)):
            row = _safe_quote(last_quotes, symbol, ts, cfg)
            if row is None:
                if ts >= position.expiry:
                    px_usd = intrinsic_usd(option_type, spot, position.strike)
                    fee = min(cfg.option_delivery_fee_rate_underlying * spot, cfg.option_fee_premium_cap * px_usd) * position.quantity * cost_multiplier
                    proceeds += px_usd * position.quantity
                    fees += fee
                    staged.append({"timestamp": ts, "kind": "DELIVERY", "symbol": symbol, "quantity": -position.quantity, "price_usd": px_usd, "cash_flow": px_usd * position.quantity - fee, "fee_usd": fee, "reason": reason})
                    continue
                return False
            price = float(row["bid_price"])
            px_usd = option_price_usd(row, price)
            fee = option_fee_usd(row, price, position.quantity, cfg, cost_multiplier)
            proceeds += px_usd * position.quantity
            fees += fee
            staged.append({"timestamp": ts, "kind": "OPTION_CLOSE", "symbol": symbol, "quantity": -position.quantity, "price_usd": px_usd, "cash_flow": px_usd * position.quantity - fee, "fee_usd": fee, "reason": reason})
        trade_rows.extend(staged)
        cash += proceeds - fees
        cumulative_fees += fees
        position = None
        return True

    for bar_index, (timestamp, snapshot) in enumerate(grouped):
        ts = pd.Timestamp(timestamp)
        for _, row in snapshot.iterrows():
            last_quotes[str(row["symbol"])] = _row_dict(row)
        spots = pd.to_numeric(snapshot["underlying_price"], errors="coerce").dropna()
        spot = float(spots.median()) if len(spots) else prev_spot
        if spot is None or not math.isfinite(spot) or spot <= 0:
            continue
        if prev_spot is not None:
            cash += hedge_qty * (spot - prev_spot)
        if prev_ts is not None:
            dt_year = max((ts - prev_ts).total_seconds(), 0.0) / YEAR_SECONDS
            funding = abs(hedge_qty) * spot * cfg.funding_annual_assumption * dt_year
            cash -= funding
            cumulative_funding += funding
        due = [p for p in pending_hedges if p[0] <= bar_index]
        pending_hedges = [p for p in pending_hedges if p[0] > bar_index]
        for _, target, reason in due:
            trade_hedge(ts, spot, target, reason)

        day = ts.date()
        entry_check = day != last_entry_day and ts.hour >= cfg.entry_hour_utc
        if entry_check:
            last_entry_day = day
        must_roll = position is not None and (ts >= position.next_roll_at or (position.expiry - ts).total_seconds() / 86400.0 <= cfg.exit_dte)
        if must_roll:
            if close_options(ts, spot, "SCHEDULED_ROLL"):
                if hedge_enabled:
                    pending_hedges.append((bar_index + latency, 0.0, "ROLL_FLATTEN"))
        if position is None and entry_check:
            selected = select_atm_straddle(snapshot, cfg)
            if selected is None:
                skipped_entries += 1
            else:
                call_row = _safe_quote(last_quotes, selected["call_symbol"], ts, cfg)
                put_row = _safe_quote(last_quotes, selected["put_symbol"], ts, cfg)
                if call_row is None or put_row is None:
                    skipped_entries += 1
                else:
                    premium = option_price_usd(call_row, float(call_row["ask_price"])) + option_price_usd(put_row, float(put_row["ask_price"]))
                    raw_quantity = cash * cfg.premium_budget_fraction / max(premium, 1e-12)
                    quantity = math.floor(raw_quantity / cfg.minimum_contract_amount + 1e-12) * cfg.minimum_contract_amount
                    if quantity < cfg.minimum_contract_amount:
                        skipped_entries += 1
                    else:
                        total_cost = 0.0
                        total_fee = 0.0
                        staged: list[dict[str, Any]] = []
                        for row, symbol in ((call_row, selected["call_symbol"]), (put_row, selected["put_symbol"])):
                            price = float(row["ask_price"])
                            px_usd = option_price_usd(row, price)
                            fee = option_fee_usd(row, price, quantity, cfg, cost_multiplier)
                            total_cost += px_usd * quantity
                            total_fee += fee
                            staged.append({"timestamp": ts, "kind": "OPTION_OPEN", "symbol": symbol, "quantity": quantity, "price_usd": px_usd, "cash_flow": -(px_usd * quantity + fee), "fee_usd": fee, "reason": "ATM_STRADDLE_ENTRY"})
                        if total_cost + total_fee >= cash:
                            skipped_entries += 1
                        else:
                            trade_rows.extend(staged)
                            cash -= total_cost + total_fee
                            cumulative_fees += total_fee
                            position = Position(selected["call_symbol"], selected["put_symbol"], pd.Timestamp(selected["expiration"]), float(selected["strike"]), quantity, ts, ts + pd.Timedelta(days=cfg.roll_days))
                            roll_count += 1

        option_delta = _position_delta(position, last_quotes, ts, cfg)
        if hedge_enabled and math.isfinite(option_delta):
            desired = -option_delta
            band = cfg.delta_band_per_contract * (position.quantity if position is not None else 1.0)
            elapsed = math.inf if last_hedge_ts is None else (ts - last_hedge_ts).total_seconds() / 60.0
            if abs(desired - hedge_qty) >= band or elapsed >= cfg.maximum_hedge_minutes:
                pending_hedges.append((bar_index + latency, desired, "DELTA_BAND_OR_CLOCK"))
        elif not hedge_enabled and abs(hedge_qty) > 0:
            trade_hedge(ts, spot, 0.0, "HEDGE_DISABLED")

        option_value = _option_value_usd(position, last_quotes, ts, cfg, "mid", spot)
        if not math.isfinite(option_value):
            diagnostic_rows.append({"timestamp": ts, "event": "STALE_OPTION_QUOTE", "call": position.call_symbol if position else None, "put": position.put_symbol if position else None})
            option_value = 0.0 if position is None else _option_value_usd(position, last_quotes, ts, cfg, "bid", spot)
        equity = cash + option_value
        if equity <= 0:
            diagnostic_rows.append({"timestamp": ts, "event": "LIQUIDATION", "equity": equity})
            break
        ledger_rows.append({
            "timestamp": ts,
            "spot": spot,
            "cash": cash,
            "option_value": option_value,
            "equity": equity,
            "hedge_quantity": hedge_qty,
            "option_delta": option_delta if math.isfinite(option_delta) else np.nan,
            "net_delta": (option_delta + hedge_qty) if math.isfinite(option_delta) else np.nan,
            "option_quantity": position.quantity if position else 0.0,
            "call_symbol": position.call_symbol if position else "",
            "put_symbol": position.put_symbol if position else "",
            "cumulative_fees": cumulative_fees,
            "cumulative_funding": cumulative_funding,
            "cash_nano": int(round(cash * NANO)),
            "option_value_nano": int(round(option_value * NANO)),
            "equity_nano": int(round(equity * NANO)),
        })
        prev_spot, prev_ts = spot, ts

    if position is not None and prev_ts is not None and prev_spot is not None:
        close_options(prev_ts, prev_spot, "END_OF_SAMPLE")
        trade_hedge(prev_ts, prev_spot, 0.0, "END_OF_SAMPLE")
    ledger = pd.DataFrame(ledger_rows)
    trades = pd.DataFrame(trade_rows)
    diagnostics = pd.DataFrame(diagnostic_rows)
    metrics = _performance_metrics(ledger)
    metrics.update({
        "roll_count": int(roll_count),
        "skipped_entries": int(skipped_entries),
        "total_fees": float(cumulative_fees),
        "total_funding": float(cumulative_funding),
        "maximum_abs_hedge": float(ledger["hedge_quantity"].abs().max()) if len(ledger) else 0.0,
    })
    days = metrics.get("calendar_days", 0.0)
    if days < cfg.minimum_backtest_days or roll_count < cfg.minimum_rolls:
        status = "INSUFFICIENT_HISTORICAL_OPTIONS_DATA"
    elif metrics["final_wealth_ratio"] > 1.0 and metrics["cagr"] > 0 and metrics["top_5pct_positive_day_concentration"] <= cfg.concentration_limit:
        status = "HISTORICAL_LONG_GAMMA_PASS_NEEDS_NEW_OOS"
    else:
        status = "HISTORICAL_LONG_GAMMA_REJECTED"
    return BacktestResult(name, ledger, trades, diagnostics, metrics, status)


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
    gate = {"version": VERSION, "primary_status": primary.status, "overall_status": overall, "tests": tests, "variant_metrics": {k: v.metrics for k, v in variants.items()}}
    return variants, gate


def verify_ledger(ledger: pd.DataFrame) -> list[str]:
    failures: list[str] = []
    if ledger.empty:
        return ["empty_ledger"]
    expected = ledger["cash_nano"].astype(np.int64) + ledger["option_value_nano"].astype(np.int64)
    if (expected - ledger["equity_nano"].astype(np.int64)).abs().max() > 1:
        failures.append("equity_identity")
    if (ledger["equity"] <= 0).any():
        failures.append("nonpositive_equity")
    if ledger["timestamp"].duplicated().any():
        failures.append("duplicate_timestamp")
    return failures


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
    raise TypeError(type(value).__name__)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, default=json_default, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def output_manifest(root: Path, exclude: set[str] | None = None) -> dict[str, Any]:
    exclude = exclude or set()
    files = []
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        rel = path.relative_to(root).as_posix()
        if rel in exclude:
            continue
        files.append({"path": rel, "size": path.stat().st_size, "sha256": sha256_file(path)})
    payload = "\n".join(f"{x['path']}\0{x['size']}\0{x['sha256']}" for x in files).encode()
    return {"version": VERSION, "files": files, "tree_sha256": hashlib.sha256(payload).hexdigest()}


def deterministic_zip(root: Path, destination: Path, include_results: bool = True) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination_abs = destination.resolve()
    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for path in sorted(p for p in root.rglob("*") if p.is_file()):
            if path.resolve() == destination_abs:
                continue
            rel = path.relative_to(root).as_posix()
            if any(part in {".git", ".venv", "__pycache__", ".pytest_cache"} for part in path.parts):
                continue
            if not include_results and (rel.startswith("v27_results/") or rel.startswith("runtime/")):
                continue
            info = zipfile.ZipInfo(rel)
            info.date_time = (2026, 7, 20, 0, 0, 0)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            zf.writestr(info, path.read_bytes())


def copy_clean_tree(source: Path, destination: Path) -> None:
    if destination.exists():
        shutil.rmtree(destination)
    shutil.copytree(source, destination, ignore=shutil.ignore_patterns(".git", ".venv", "__pycache__", ".pytest_cache", "runtime", "v27_results"))

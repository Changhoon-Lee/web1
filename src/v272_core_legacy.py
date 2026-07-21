#!/usr/bin/env python3
"""V27.2 authoritative Deribit inverse long-gamma accounting core.

The ledger is USD-equivalent, but every inverse option and BTC-PERPETUAL cash
flow is first calculated in BTC using Deribit's contract rules and converted at
the contemporaneous index price. The module is fail-closed: it requires
executable option and perpetual quotes, actual public funding fields, held
option quote continuity, and deterministic nano-dollar ledger identities.
"""
from __future__ import annotations

import hashlib
import json
import math
import zipfile
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Iterable, Sequence

import numpy as np
import pandas as pd

VERSION = "27.2.0-inverse-actual"
YEAR_SECONDS = 365.25 * 24 * 3600
NANO = 1_000_000_000


@dataclass(frozen=True)
class Config:
    currency: str = "BTC"
    initial_equity_usd: float = 100_000.0
    snapshot_minutes: int = 5
    target_dte: float = 30.0
    minimum_dte: float = 21.0
    maximum_dte: float = 45.0
    exit_dte: float = 7.0
    roll_days: int = 7
    entry_hour_utc: int = 8
    premium_budget_fraction: float = 0.05
    maximum_spread_fraction: float = 0.25
    maximum_moneyness_error: float = 0.025
    maximum_quote_age_minutes: int = 15
    minimum_contract_amount: float = 0.1
    delta_band_btc_per_contract: float = 0.10
    maximum_hedge_minutes: int = 30
    hedge_latency_bars: int = 1
    option_fee_rate_coin: float = 0.0003
    option_fee_premium_cap: float = 0.125
    option_delivery_fee_rate_coin: float = 0.00015
    perp_contract_size_usd: float = 10.0
    perp_taker_fee_rate: float = 0.0005
    minimum_backtest_days: int = 90
    minimum_rolls: int = 8
    concentration_limit: float = 0.50
    minimum_held_quote_coverage: float = 0.95
    minimum_perp_quote_coverage: float = 0.95
    minimum_funding_coverage: float = 0.95
    maximum_maintenance_margin_fraction: float = 0.80

    def validate(self) -> None:
        if self.currency != "BTC":
            raise ValueError("V27.2 inverse core currently supports BTC only")
        if self.initial_equity_usd <= 0:
            raise ValueError("initial equity must be positive")
        if self.snapshot_minutes <= 0 or 1440 % self.snapshot_minutes:
            raise ValueError("snapshot_minutes must divide one day")
        if not 0 < self.exit_dte < self.minimum_dte <= self.target_dte <= self.maximum_dte:
            raise ValueError("invalid DTE ordering")
        if not 0 < self.premium_budget_fraction < 1:
            raise ValueError("invalid premium budget")
        if not 0 < self.maximum_spread_fraction < 1:
            raise ValueError("invalid spread fraction")
        if self.perp_contract_size_usd <= 0:
            raise ValueError("invalid perpetual contract size")
        if self.hedge_latency_bars < 0:
            raise ValueError("negative hedge latency")


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


ALIASES: dict[str, tuple[str, ...]] = {
    "timestamp": ("timestamp", "time", "datetime", "local_timestamp"),
    "symbol": ("symbol", "instrument", "instrument_name"),
    "type": ("type", "option_type", "kind"),
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
    "underlying_price": ("underlying_price", "forward_price", "spot"),
    "index_price": ("index_price", "estimated_delivery_price"),
    "underlying_index": ("underlying_index", "index_name"),
    "open_interest": ("open_interest", "oi"),
    "delta": ("delta",),
    "gamma": ("gamma",),
    "vega": ("vega",),
    "theta": ("theta",),
    "funding_8h": ("funding_8h", "interest_8h"),
    "current_funding": ("current_funding", "current_interest"),
    "contract_size_usd": ("contract_size_usd",),
}


def _find_column(frame: pd.DataFrame, aliases: Sequence[str]) -> str | None:
    lookup = {str(c).strip().lower(): str(c) for c in frame.columns}
    for alias in aliases:
        if alias.lower() in lookup:
            return lookup[alias.lower()]
    return None


def _datetime(values: pd.Series) -> pd.Series:
    if pd.api.types.is_numeric_dtype(values):
        x = pd.to_numeric(values, errors="coerce")
        valid = x.dropna().abs()
        median = float(valid.median()) if len(valid) else 0.0
        unit = "ns" if median > 1e17 else "us" if median > 1e14 else "ms" if median > 1e11 else "s"
        return pd.to_datetime(x, unit=unit, utc=True, errors="coerce")
    return pd.to_datetime(values, utc=True, errors="coerce")


def canonicalize_market(frame: pd.DataFrame, cfg: Config) -> pd.DataFrame:
    out = pd.DataFrame(index=frame.index)
    for canonical, aliases in ALIASES.items():
        col = _find_column(frame, aliases)
        if col is not None:
            out[canonical] = frame[col]
    required = {"timestamp", "symbol", "type", "bid_price", "ask_price"}
    missing = required.difference(out.columns)
    if missing:
        raise ValueError(f"missing market fields: {sorted(missing)}")
    out["timestamp"] = _datetime(out["timestamp"])
    if "expiration" in out:
        out["expiration"] = _datetime(out["expiration"])
    else:
        out["expiration"] = pd.NaT
    out["symbol"] = out["symbol"].astype(str).str.upper().str.strip()
    out["type"] = out["type"].astype(str).str.lower().replace({"c": "call", "p": "put", "future": "perpetual"})
    for col in ALIASES:
        if col in {"timestamp", "symbol", "type", "expiration", "underlying_index"}:
            continue
        if col not in out:
            out[col] = np.nan
        out[col] = pd.to_numeric(out[col], errors="coerce")
    out["strike_price"] = out["strike_price"].fillna(0.0)
    out["contract_size_usd"] = out["contract_size_usd"].fillna(cfg.perp_contract_size_usd)
    out = out[out["type"].isin(["call", "put", "perpetual"])]
    out = out.dropna(subset=["timestamp", "bid_price", "ask_price"])
    out = out[(out["bid_price"] >= 0) & (out["ask_price"] > 0) & (out["ask_price"] >= out["bid_price"])]
    option_mask = out["type"].isin(["call", "put"])
    out = out[(~option_mask) | (out["symbol"].str.startswith(cfg.currency))]
    out = out[(~option_mask) | (out["strike_price"] > 0)]
    out = out[(~option_mask) | out["expiration"].notna()]
    out = out[(~option_mask) | out["underlying_price"].notna()]
    out.loc[option_mask, "index_price"] = out.loc[option_mask, "index_price"].fillna(out.loc[option_mask, "underlying_price"])
    perp_mask = out["type"].eq("perpetual")
    out = out[(~perp_mask) | out["symbol"].eq(f"{cfg.currency}-PERPETUAL")]
    out.loc[perp_mask, "index_price"] = out.loc[perp_mask, "index_price"].fillna(out.loc[perp_mask, "underlying_price"])
    out.loc[perp_mask, "underlying_price"] = out.loc[perp_mask, "underlying_price"].fillna(out.loc[perp_mask, "index_price"])
    out.loc[perp_mask, "mark_price"] = out.loc[perp_mask, "mark_price"].fillna((out.loc[perp_mask, "bid_price"] + out.loc[perp_mask, "ask_price"]) / 2.0)
    out = out.dropna(subset=["index_price", "underlying_price"])
    out = out[(out["index_price"] > 0) & (out["underlying_price"] > 0)]
    out["dte"] = (out["expiration"] - out["timestamp"]).dt.total_seconds() / 86400.0
    out["moneyness_error"] = np.where(option_mask, (out["strike_price"] / out["underlying_price"] - 1.0).abs(), np.nan)
    out = out.sort_values(["timestamp", "symbol"]).drop_duplicates(["timestamp", "symbol"], keep="last")
    return out.reset_index(drop=True)


def discover_market_files(root: Path) -> list[Path]:
    root = root.expanduser().resolve()
    if root.is_file():
        return [root]
    files: list[Path] = []
    for pattern in ("*.free.compact.csv.gz", "*.compact.csv.gz", "*.csv.gz", "*.csv", "*.parquet"):
        files.extend(root.rglob(pattern))
    return sorted({p.resolve() for p in files if p.is_file() and "MANIFEST" not in p.name})


def load_market_data(paths: Iterable[Path], cfg: Config) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    for path in paths:
        frame = pd.read_parquet(path) if path.suffix == ".parquet" else pd.read_csv(path, compression="infer", low_memory=False)
        frames.append(canonicalize_market(frame, cfg))
    if not frames:
        raise FileNotFoundError("no market files")
    out = pd.concat(frames, ignore_index=True)
    out["timestamp"] = out["timestamp"].dt.floor(f"{cfg.snapshot_minutes}min")
    out = out.sort_values(["timestamp", "symbol"]).drop_duplicates(["timestamp", "symbol"], keep="last")
    return out.reset_index(drop=True)


def normal_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def bs_delta(spot: float, strike: float, years: float, volatility: float, option_type: str) -> float:
    if years <= 0 or volatility <= 0:
        if option_type == "call":
            return 1.0 if spot > strike else 0.0
        return -1.0 if spot < strike else 0.0
    d1 = (math.log(spot / strike) + 0.5 * volatility * volatility * years) / (volatility * math.sqrt(years))
    nd1 = normal_cdf(d1)
    return nd1 if option_type == "call" else nd1 - 1.0


def spread_fraction(row: pd.Series | dict[str, Any]) -> float:
    bid, ask = float(row["bid_price"]), float(row["ask_price"])
    mid = (bid + ask) / 2.0
    return (ask - bid) / mid if mid > 0 else math.inf


def option_fee_btc(premium_btc: float, quantity: float, cfg: Config, delivery: bool = False) -> float:
    rate = cfg.option_delivery_fee_rate_coin if delivery else cfg.option_fee_rate_coin
    return min(rate, cfg.option_fee_premium_cap * max(premium_btc, 0.0)) * abs(quantity)


def inverse_pnl_btc(signed_notional_usd: float, price_from: float, price_to: float) -> float:
    if price_from <= 0 or price_to <= 0:
        raise ValueError("inverse prices must be positive")
    return signed_notional_usd * (1.0 / price_from - 1.0 / price_to)


def funding_payment_btc(signed_notional_usd: float, index_price: float, funding_8h: float, seconds: float) -> float:
    """Cash change: positive rate makes longs pay and shorts receive."""
    if index_price <= 0 or seconds < 0:
        raise ValueError("invalid funding inputs")
    position_btc = signed_notional_usd / index_price
    return -funding_8h * position_btc * (seconds / (8.0 * 3600.0))


def _round_contract_notional(value_usd: float, contract_size: float) -> float:
    scaled = value_usd / contract_size
    contracts = math.floor(scaled + 0.5) if scaled >= 0 else math.ceil(scaled - 0.5)
    return contracts * contract_size


def select_atm_straddle(snapshot: pd.DataFrame, cfg: Config) -> dict[str, Any] | None:
    x = snapshot[snapshot["type"].isin(["call", "put"])].copy()
    x = x[(x["dte"] >= cfg.minimum_dte) & (x["dte"] <= cfg.maximum_dte)]
    x = x[x["moneyness_error"] <= cfg.maximum_moneyness_error]
    x = x[x.apply(spread_fraction, axis=1) <= cfg.maximum_spread_fraction]
    if x.empty:
        return None
    calls = x[x["type"] == "call"]
    puts = x[x["type"] == "put"]
    pair = calls.merge(puts, on=["timestamp", "expiration", "strike_price"], suffixes=("_call", "_put"))
    if pair.empty:
        return None
    pair["dte_score"] = (pair["dte_call"] - cfg.target_dte).abs()
    pair["money_score"] = pair[["moneyness_error_call", "moneyness_error_put"]].max(axis=1)
    pair["spread_score"] = (
        (pair["ask_price_call"] - pair["bid_price_call"]) / ((pair["ask_price_call"] + pair["bid_price_call"]) / 2.0)
        + (pair["ask_price_put"] - pair["bid_price_put"]) / ((pair["ask_price_put"] + pair["bid_price_put"]) / 2.0)
    )
    row = pair.sort_values(["dte_score", "money_score", "spread_score", "expiration", "strike_price"]).iloc[0]
    return {
        "timestamp": row["timestamp"],
        "expiration": row["expiration"],
        "strike": float(row["strike_price"]),
        "call_symbol": str(row["symbol_call"]),
        "put_symbol": str(row["symbol_put"]),
    }


def _option_delta(position: Position | None, quotes: dict[str, dict[str, Any]], ts: pd.Timestamp, cfg: Config) -> float:
    if position is None:
        return 0.0
    total = 0.0
    for symbol in (position.call_symbol, position.put_symbol):
        row = quotes.get(symbol)
        if row is None or (ts - pd.Timestamp(row["timestamp"])).total_seconds() / 60.0 > cfg.maximum_quote_age_minutes:
            return float("nan")
        delta = row.get("delta")
        if delta is None or not math.isfinite(float(delta)):
            iv = row.get("mark_iv")
            if iv is None or not math.isfinite(float(iv)) or float(iv) <= 0:
                return float("nan")
            years = max((position.expiry - ts).total_seconds() / YEAR_SECONDS, 1e-9)
            delta = bs_delta(float(row["underlying_price"]), position.strike, years, float(iv) / 100.0, str(row["type"]))
        total += float(delta) * position.quantity
    return total


def _option_value_btc(position: Position | None, quotes: dict[str, dict[str, Any]], ts: pd.Timestamp, cfg: Config, side: str = "mid") -> float:
    if position is None:
        return 0.0
    total = 0.0
    for symbol in (position.call_symbol, position.put_symbol):
        row = quotes.get(symbol)
        if row is None or (ts - pd.Timestamp(row["timestamp"])).total_seconds() / 60.0 > cfg.maximum_quote_age_minutes:
            return float("nan")
        bid, ask = float(row["bid_price"]), float(row["ask_price"])
        price = bid if side == "bid" else ask if side == "ask" else (bid + ask) / 2.0
        total += price * position.quantity
    return total


def _write_held_state(path: Path | None, symbols: Sequence[str], ts: pd.Timestamp, event: str) -> None:
    if path is None:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"version": VERSION, "held_symbols": sorted(set(symbols)), "updated_at": ts.isoformat(), "event": event}
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(path)


def _performance_metrics(ledger: pd.DataFrame) -> dict[str, Any]:
    if ledger.empty:
        return {"observations": 0, "final_equity": 0.0, "final_wealth_ratio": 0.0, "cagr": 0.0, "sharpe": 0.0, "mdd": 0.0}
    equity = ledger.set_index("timestamp")["equity_usd"].astype(float)
    returns = equity.pct_change().fillna(0.0)
    years = max((equity.index[-1] - equity.index[0]).total_seconds() / YEAR_SECONDS, 1.0 / 365.25)
    ratio = float(equity.iloc[-1] / equity.iloc[0])
    cagr = ratio ** (1.0 / years) - 1.0 if ratio > 0 else -1.0
    diffs = returns.index.to_series().diff().dt.total_seconds().dropna()
    period = float(diffs.median()) if len(diffs) else 300.0
    sd = float(returns.std(ddof=1))
    sharpe = float(returns.mean() / sd * math.sqrt(YEAR_SECONDS / max(period, 1.0))) if sd > 0 else 0.0
    dd = equity / equity.cummax() - 1.0
    daily = equity.resample("1D").last().dropna().pct_change().dropna()
    concentration = 0.0
    positives = daily[daily > 0]
    if len(positives) and positives.sum() > 0:
        k = max(1, math.ceil(len(daily) * 0.05))
        concentration = float(daily.nlargest(k).sum() / positives.sum())
    return {
        "observations": int(len(ledger)),
        "start": equity.index[0],
        "end": equity.index[-1],
        "calendar_days": float((equity.index[-1] - equity.index[0]).total_seconds() / 86400.0),
        "final_equity": float(equity.iloc[-1]),
        "final_wealth_ratio": ratio,
        "cagr": cagr,
        "sharpe": sharpe,
        "mdd": float(dd.min()),
        "top_5pct_positive_day_concentration": concentration,
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
    cfg.validate()
    if data.empty:
        return BacktestResult(name, pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), _performance_metrics(pd.DataFrame()), "INSUFFICIENT_HISTORICAL_OPTIONS_DATA")
    latency = cfg.hedge_latency_bars if latency_bars is None else int(latency_bars)
    grouped = list(data.sort_values(["timestamp", "symbol"]).groupby("timestamp", sort=True))
    cash_usd = cfg.initial_equity_usd
    position: Position | None = None
    perp_notional_usd = 0.0
    pending_hedges: list[tuple[int, float, str]] = []
    option_quotes: dict[str, dict[str, Any]] = {}
    previous_perp: dict[str, Any] | None = None
    last_hedge_ts: pd.Timestamp | None = None
    last_entry_day: Any = None
    ledger_rows: list[dict[str, Any]] = []
    trade_rows: list[dict[str, Any]] = []
    diagnostic_rows: list[dict[str, Any]] = []
    cumulative_option_fees_usd = 0.0
    cumulative_perp_fees_usd = 0.0
    cumulative_funding_usd = 0.0
    cumulative_perp_pnl_usd = 0.0
    roll_count = 0
    skipped_entries = 0
    held_required = 0
    held_available = 0
    close_attempts = 0
    close_with_bid = 0
    perp_required = 0
    perp_available = 0
    funding_required = 0
    funding_available = 0
    final_live_symbols: list[str] = []

    def execute_hedge(ts: pd.Timestamp, target_notional: float, perp: dict[str, Any], reason: str) -> None:
        nonlocal cash_usd, perp_notional_usd, cumulative_perp_fees_usd, last_hedge_ts
        change = target_notional - perp_notional_usd
        if abs(change) < cfg.perp_contract_size_usd / 2:
            return
        bid, ask, mark, index = (float(perp[k]) for k in ("bid_price", "ask_price", "mark_price", "index_price"))
        execution = ask if change > 0 else bid
        slippage_btc = inverse_pnl_btc(change, execution, mark)
        slippage_usd = slippage_btc * index
        fee_btc = abs(change) / execution * cfg.perp_taker_fee_rate * cost_multiplier
        fee_usd = fee_btc * index
        cash_usd += slippage_usd - fee_usd
        cumulative_perp_fees_usd += fee_usd
        trade_rows.append({
            "timestamp": ts, "kind": "PERP_HEDGE", "symbol": f"{cfg.currency}-PERPETUAL",
            "change_notional_usd": change, "target_notional_usd": target_notional,
            "execution_price": execution, "mark_price": mark, "slippage_usd": slippage_usd,
            "fee_usd": fee_usd, "cash_flow_usd": slippage_usd - fee_usd, "reason": reason,
        })
        perp_notional_usd = target_notional
        last_hedge_ts = ts

    def close_options(ts: pd.Timestamp, index: float, reason: str) -> bool:
        nonlocal cash_usd, position, cumulative_option_fees_usd, close_attempts, close_with_bid
        if position is None:
            return True
        close_attempts += 1
        staged: list[dict[str, Any]] = []
        proceeds_btc = 0.0
        fees_btc = 0.0
        for option_type, symbol in (("call", position.call_symbol), ("put", position.put_symbol)):
            row = option_quotes.get(symbol)
            fresh = row is not None and (ts - pd.Timestamp(row["timestamp"])).total_seconds() / 60.0 <= cfg.maximum_quote_age_minutes
            if not fresh:
                if ts >= position.expiry:
                    intrinsic_usd = max(index - position.strike, 0.0) if option_type == "call" else max(position.strike - index, 0.0)
                    premium_btc = intrinsic_usd / index
                    fee_btc = option_fee_btc(premium_btc, position.quantity, cfg, delivery=True) * cost_multiplier
                    proceeds_btc += premium_btc * position.quantity
                    fees_btc += fee_btc
                    staged.append({"timestamp": ts, "kind": "OPTION_DELIVERY", "symbol": symbol, "quantity": -position.quantity, "premium_btc": premium_btc, "index_price": index, "fee_btc": fee_btc, "reason": reason})
                    continue
                diagnostic_rows.append({"timestamp": ts, "event": "MISSING_EXECUTABLE_CLOSE_BID", "symbol": symbol, "reason": reason})
                return False
            bid = float(row["bid_price"])
            fee_btc = option_fee_btc(bid, position.quantity, cfg) * cost_multiplier
            proceeds_btc += bid * position.quantity
            fees_btc += fee_btc
            staged.append({"timestamp": ts, "kind": "OPTION_CLOSE", "symbol": symbol, "quantity": -position.quantity, "premium_btc": bid, "index_price": index, "fee_btc": fee_btc, "reason": reason})
        close_with_bid += 1
        cash_flow_usd = (proceeds_btc - fees_btc) * index
        cash_usd += cash_flow_usd
        fee_usd = fees_btc * index
        cumulative_option_fees_usd += fee_usd
        for row in staged:
            row["fee_usd"] = float(row["fee_btc"]) * index
            row["cash_flow_usd"] = cash_flow_usd / max(len(staged), 1)
        trade_rows.extend(staged)
        position = None
        return True

    for bar_index, (timestamp, snapshot) in enumerate(grouped):
        ts = pd.Timestamp(timestamp)
        for _, row in snapshot[snapshot["type"].isin(["call", "put"])].iterrows():
            option_quotes[str(row["symbol"])] = {str(k): row[k] for k in row.index}
        perp_rows = snapshot[snapshot["type"] == "perpetual"]
        perp_required += 1
        if perp_rows.empty:
            diagnostic_rows.append({"timestamp": ts, "event": "MISSING_PERPETUAL_QUOTE"})
            continue
        perp_row = perp_rows.sort_values("symbol").iloc[-1]
        perp = {str(k): perp_row[k] for k in perp_row.index}
        perp_available += 1
        index = float(perp["index_price"])
        mark = float(perp["mark_price"])
        funding_required += 1
        funding = perp.get("funding_8h")
        funding_ok = funding is not None and math.isfinite(float(funding))
        if funding_ok:
            funding_available += 1
        else:
            diagnostic_rows.append({"timestamp": ts, "event": "MISSING_ACTUAL_FUNDING"})

        if previous_perp is not None:
            previous_mark = float(previous_perp["mark_price"])
            pnl_btc = inverse_pnl_btc(perp_notional_usd, previous_mark, mark)
            pnl_usd = pnl_btc * index
            cash_usd += pnl_usd
            cumulative_perp_pnl_usd += pnl_usd
            seconds = max((ts - pd.Timestamp(previous_perp["timestamp"])).total_seconds(), 0.0)
            if funding_ok:
                f_btc = funding_payment_btc(perp_notional_usd, index, float(funding), seconds)
                f_usd = f_btc * index
                cash_usd += f_usd
                cumulative_funding_usd += f_usd
        previous_perp = perp

        due = [item for item in pending_hedges if item[0] <= bar_index]
        pending_hedges = [item for item in pending_hedges if item[0] > bar_index]
        for _, target, reason in due:
            execute_hedge(ts, target, perp, reason)

        if position is not None:
            held_required += 2
            fresh_count = 0
            for symbol in (position.call_symbol, position.put_symbol):
                row = option_quotes.get(symbol)
                if row is not None and (ts - pd.Timestamp(row["timestamp"])).total_seconds() / 60.0 <= cfg.maximum_quote_age_minutes:
                    fresh_count += 1
            held_available += fresh_count
            if fresh_count < 2:
                diagnostic_rows.append({"timestamp": ts, "event": "HELD_OPTION_QUOTE_GAP", "fresh_legs": fresh_count})

        day = ts.date()
        entry_check = day != last_entry_day and ts.hour >= cfg.entry_hour_utc
        if entry_check:
            last_entry_day = day
        must_roll = position is not None and (ts >= position.next_roll_at or (position.expiry - ts).total_seconds() / 86400.0 <= cfg.exit_dte)
        if must_roll and close_options(ts, index, "SCHEDULED_ROLL") and hedge_enabled:
            pending_hedges.append((bar_index + latency, 0.0, "ROLL_FLATTEN"))

        if position is None and entry_check:
            selected = select_atm_straddle(snapshot, cfg)
            if selected is None:
                skipped_entries += 1
            else:
                call = option_quotes.get(selected["call_symbol"])
                put = option_quotes.get(selected["put_symbol"])
                if call is None or put is None:
                    skipped_entries += 1
                else:
                    premium_btc = float(call["ask_price"]) + float(put["ask_price"])
                    budget_usd = max(cash_usd, 0.0) * cfg.premium_budget_fraction
                    raw_qty = budget_usd / max(premium_btc * index, 1e-12)
                    qty = math.floor(raw_qty / cfg.minimum_contract_amount + 1e-12) * cfg.minimum_contract_amount
                    fees_btc = (option_fee_btc(float(call["ask_price"]), qty, cfg) + option_fee_btc(float(put["ask_price"]), qty, cfg)) * cost_multiplier
                    total_usd = (premium_btc * qty + fees_btc) * index
                    if qty < cfg.minimum_contract_amount or total_usd >= cash_usd:
                        skipped_entries += 1
                    else:
                        cash_usd -= total_usd
                        cumulative_option_fees_usd += fees_btc * index
                        for row in (call, put):
                            p = float(row["ask_price"])
                            fee_btc = option_fee_btc(p, qty, cfg) * cost_multiplier
                            trade_rows.append({"timestamp": ts, "kind": "OPTION_OPEN", "symbol": row["symbol"], "quantity": qty, "premium_btc": p, "index_price": index, "fee_btc": fee_btc, "fee_usd": fee_btc * index, "cash_flow_usd": -(p * qty + fee_btc) * index, "reason": "ATM_STRADDLE_ENTRY"})
                        position = Position(selected["call_symbol"], selected["put_symbol"], pd.Timestamp(selected["expiration"]), float(selected["strike"]), qty, ts, ts + pd.Timedelta(days=cfg.roll_days))
                        roll_count += 1

        option_delta = _option_delta(position, option_quotes, ts, cfg)
        if hedge_enabled and math.isfinite(option_delta):
            raw_target = -option_delta * index
            target = _round_contract_notional(raw_target, cfg.perp_contract_size_usd)
            band_usd = cfg.delta_band_btc_per_contract * (position.quantity if position else 1.0) * index
            elapsed = math.inf if last_hedge_ts is None else (ts - last_hedge_ts).total_seconds() / 60.0
            if abs(target - perp_notional_usd) >= max(band_usd, cfg.perp_contract_size_usd) or elapsed >= cfg.maximum_hedge_minutes:
                pending_hedges.append((bar_index + latency, target, "DELTA_BAND_OR_CLOCK"))
        elif not hedge_enabled and abs(perp_notional_usd) > 0:
            execute_hedge(ts, 0.0, perp, "HEDGE_DISABLED")

        option_value_btc = _option_value_btc(position, option_quotes, ts, cfg, "mid")
        if not math.isfinite(option_value_btc):
            option_value_btc = 0.0
        option_value_usd = option_value_btc * index
        equity_usd = cash_usd + option_value_usd
        position_btc = abs(perp_notional_usd) / index
        maintenance_fraction = 0.01 + position_btc * 0.00005
        maintenance_margin_usd = abs(perp_notional_usd) * maintenance_fraction
        margin_ratio = maintenance_margin_usd / max(equity_usd, 1e-12)
        if equity_usd <= 0 or margin_ratio > cfg.maximum_maintenance_margin_fraction:
            diagnostic_rows.append({"timestamp": ts, "event": "LIQUIDATION_OR_MARGIN_BREACH", "equity_usd": equity_usd, "maintenance_margin_usd": maintenance_margin_usd, "margin_ratio": margin_ratio})
            break
        ledger_rows.append({
            "timestamp": ts, "index_price": index, "perp_mark": mark,
            "cash_usd": cash_usd, "option_value_usd": option_value_usd, "equity_usd": equity_usd,
            "perp_notional_usd": perp_notional_usd, "option_delta_btc": option_delta if math.isfinite(option_delta) else np.nan,
            "net_delta_btc": (option_delta + perp_notional_usd / index) if math.isfinite(option_delta) else np.nan,
            "maintenance_margin_usd": maintenance_margin_usd, "margin_ratio": margin_ratio,
            "option_quantity": position.quantity if position else 0.0,
            "call_symbol": position.call_symbol if position else "", "put_symbol": position.put_symbol if position else "",
            "cumulative_option_fees_usd": cumulative_option_fees_usd,
            "cumulative_perp_fees_usd": cumulative_perp_fees_usd,
            "cumulative_funding_usd": cumulative_funding_usd,
            "cumulative_perp_pnl_usd": cumulative_perp_pnl_usd,
            "cash_nano": int(round(cash_usd * NANO)),
            "option_value_nano": int(round(option_value_usd * NANO)),
            "equity_nano": int(round(equity_usd * NANO)),
        })

    if position is not None:
        final_live_symbols = [position.call_symbol, position.put_symbol]
    if grouped:
        final_ts = pd.Timestamp(grouped[-1][0])
        _write_held_state(held_state_file, final_live_symbols, final_ts, "END_OF_BACKTEST_LIVE_STATE")
        if previous_perp is not None:
            index = float(previous_perp["index_price"])
            close_options(final_ts, index, "END_OF_SAMPLE")
            if abs(perp_notional_usd) > 0:
                execute_hedge(final_ts, 0.0, previous_perp, "END_OF_SAMPLE")
            if ledger_rows:
                equity_usd = cash_usd
                ledger_rows.append({**ledger_rows[-1], "timestamp": final_ts + pd.Timedelta(nanoseconds=1), "cash_usd": cash_usd, "option_value_usd": 0.0, "equity_usd": equity_usd, "perp_notional_usd": 0.0, "option_delta_btc": 0.0, "net_delta_btc": 0.0, "option_quantity": 0.0, "call_symbol": "", "put_symbol": "", "cash_nano": int(round(cash_usd * NANO)), "option_value_nano": 0, "equity_nano": int(round(equity_usd * NANO))})

    ledger = pd.DataFrame(ledger_rows)
    trades = pd.DataFrame(trade_rows)
    diagnostics = pd.DataFrame(diagnostic_rows)
    metrics = _performance_metrics(ledger)
    held_coverage = held_available / held_required if held_required else 1.0
    close_coverage = close_with_bid / close_attempts if close_attempts else 1.0
    perp_coverage = perp_available / perp_required if perp_required else 0.0
    funding_coverage = funding_available / funding_required if funding_required else 0.0
    metrics.update({
        "roll_count": int(roll_count), "skipped_entries": int(skipped_entries),
        "total_option_fees_usd": cumulative_option_fees_usd,
        "total_perp_fees_usd": cumulative_perp_fees_usd,
        "total_funding_usd": cumulative_funding_usd,
        "total_perp_pnl_usd": cumulative_perp_pnl_usd,
        "held_option_quote_coverage": held_coverage,
        "executable_close_coverage": close_coverage,
        "perpetual_quote_coverage": perp_coverage,
        "funding_coverage": funding_coverage,
        "missing_close_bid_count": int(close_attempts - close_with_bid),
        "live_held_symbols": final_live_symbols,
    })
    sufficient = metrics.get("calendar_days", 0.0) >= cfg.minimum_backtest_days and roll_count >= cfg.minimum_rolls
    continuity = (
        held_coverage >= cfg.minimum_held_quote_coverage
        and close_coverage >= 1.0
        and perp_coverage >= cfg.minimum_perp_quote_coverage
        and funding_coverage >= cfg.minimum_funding_coverage
    )
    if not sufficient:
        status = "INSUFFICIENT_HISTORICAL_OPTIONS_DATA"
    elif not continuity:
        status = "MARKET_DATA_CONTINUITY_GATE_FAILED"
    elif metrics["final_wealth_ratio"] > 1.0 and metrics["cagr"] > 0 and metrics["top_5pct_positive_day_concentration"] <= cfg.concentration_limit:
        status = "HISTORICAL_LONG_GAMMA_PASS_NEEDS_NEW_OOS"
    else:
        status = "HISTORICAL_LONG_GAMMA_REJECTED"
    return BacktestResult(name, ledger, trades, diagnostics, metrics, status)


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
        "no_liquidation": not (len(primary.diagnostics) and primary.diagnostics.get("event", pd.Series(dtype=str)).astype(str).str.contains("LIQUIDATION").any()),
    }
    if primary.status == "INSUFFICIENT_HISTORICAL_OPTIONS_DATA":
        overall = "INSUFFICIENT_CONTIGUOUS_OPTIONS_DATA"
    elif primary.status == "MARKET_DATA_CONTINUITY_GATE_FAILED":
        overall = "MARKET_DATA_CONTINUITY_GATE_FAILED"
    elif all(tests.values()):
        overall = "HISTORICAL_DERIBIT_LONG_GAMMA_PASS_NEEDS_NEW_OOS"
    else:
        overall = "HISTORICAL_DERIBIT_LONG_GAMMA_REJECTED"
    return variants, {"version": VERSION, "primary_status": primary.status, "overall_status": overall, "tests": tests, "variant_metrics": {k: v.metrics for k, v in variants.items()}}


def verify_ledger(ledger: pd.DataFrame) -> list[str]:
    if ledger.empty:
        return ["empty_ledger"]
    failures: list[str] = []
    expected = ledger["cash_nano"].astype(np.int64) + ledger["option_value_nano"].astype(np.int64)
    if (expected - ledger["equity_nano"].astype(np.int64)).abs().max() > 1:
        failures.append("equity_identity")
    if (ledger["equity_usd"] <= 0).any():
        failures.append("nonpositive_equity")
    if ledger["timestamp"].duplicated().any():
        failures.append("duplicate_timestamp")
    return failures


def json_default(value: Any) -> Any:
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        x = float(value)
        return x if math.isfinite(x) else None
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
    path.write_text(json.dumps(payload, default=json_default, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
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


def deterministic_zip(root: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    dest = destination.resolve()
    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for path in sorted(p for p in root.rglob("*") if p.is_file()):
            if path.resolve() == dest:
                continue
            if any(part in {".git", ".venv", "__pycache__", ".pytest_cache"} for part in path.parts):
                continue
            rel = path.relative_to(root).as_posix()
            info = zipfile.ZipInfo(rel)
            info.date_time = (1980, 1, 1, 0, 0, 0)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = (0o755 if path.suffix == ".command" or path.suffix == ".sh" else 0o644) << 16
            zf.writestr(info, path.read_bytes())

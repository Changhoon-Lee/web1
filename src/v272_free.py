#!/usr/bin/env python3
"""V27.2 official-free Deribit recorder and continuity gate."""
from __future__ import annotations

import gzip
import hashlib
import json
import math
import os
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import pandas as pd

from v272_core import Config, VERSION, json_default, sha256_file, write_json

DERIBIT_RPC = "https://www.deribit.com/api/v2"
FORBIDDEN_ENV_VARS = {"TARDIS_API_KEY", "DERIBIT_CLIENT_ID", "DERIBIT_CLIENT_SECRET"}
COLUMNS = [
    "timestamp", "symbol", "type", "strike_price", "expiration",
    "bid_price", "ask_price", "bid_amount", "ask_amount", "mark_price",
    "mark_iv", "bid_iv", "ask_iv", "underlying_price", "index_price",
    "underlying_index", "open_interest", "delta", "gamma", "vega", "theta",
    "funding_8h", "current_funding", "contract_size_usd",
]


@dataclass(frozen=True)
class FreeConfig:
    currency: str = "BTC"
    target_dte: float = 30.0
    minimum_dte: float = 21.0
    maximum_dte: float = 45.0
    max_strikes_per_expiry: int = 11
    interval_seconds: int = 300
    record_minutes: int = 0
    minimum_active_days: int = 90
    minimum_active_day_ratio: float = 0.80
    maximum_day_gap_hours: float = 48.0
    expected_snapshots_per_complete_day: int = 288
    minimum_intraday_ratio: float = 0.80
    maximum_median_gap_minutes: float = 10.0
    maximum_operational_gap_minutes: float = 30.0
    request_timeout_seconds: int = 20
    instrument_cache_seconds: int = 3600

    def validate(self) -> None:
        if self.currency != "BTC":
            raise ValueError("V27.2 free runtime currently supports BTC only")
        if not 0 < self.minimum_dte <= self.target_dte <= self.maximum_dte:
            raise ValueError("invalid DTE ordering")
        if self.max_strikes_per_expiry < 1:
            raise ValueError("max strikes must be positive")
        if self.interval_seconds < 30:
            raise ValueError("interval must be at least 30 seconds")
        if self.record_minutes < 0:
            raise ValueError("negative record duration")
        if self.minimum_active_days < 1:
            raise ValueError("invalid minimum active days")


def public_rpc(method: str, params: dict[str, Any] | None = None, timeout: int = 20) -> Any:
    if any(os.getenv(name) for name in FORBIDDEN_ENV_VARS):
        raise RuntimeError("free-only mode refuses paid/private credentials")
    query = urllib.parse.urlencode(params or {})
    url = f"{DERIBIT_RPC}/public/{method}" + (f"?{query}" if query else "")
    req = urllib.request.Request(url, headers={"User-Agent": "V27.2-Free-Open/27.2"})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        payload = json.loads(response.read().decode("utf-8"))
    if "error" in payload:
        raise RuntimeError(json.dumps(payload["error"], sort_keys=True))
    return payload.get("result")


def _utc_ms(value: Any) -> pd.Timestamp:
    if isinstance(value, pd.Timestamp):
        ts = value
    elif isinstance(value, (int, float)):
        ts = pd.to_datetime(value, unit="ms", utc=True)
    else:
        ts = pd.to_datetime(value, utc=True)
    return ts.tz_convert("UTC") if ts.tzinfo else ts.tz_localize("UTC")


def load_held_symbols(state_file: Path | None) -> set[str]:
    if state_file is None or not state_file.exists():
        return set()
    try:
        payload = json.loads(state_file.read_text(encoding="utf-8"))
        return {str(x).upper() for x in payload.get("held_symbols", [])}
    except Exception:
        return set()


def choose_neighborhood(instruments: list[dict[str, Any]], index: float, now: pd.Timestamp, cfg: FreeConfig) -> list[dict[str, Any]]:
    by_expiry: dict[pd.Timestamp, list[tuple[float, float, str, dict[str, Any]]]] = {}
    for item in instruments:
        try:
            expiry = _utc_ms(item["expiration_timestamp"])
            dte = (expiry - now).total_seconds() / 86400.0
            strike = float(item["strike"])
            option_type = str(item["option_type"]).lower()
            if cfg.minimum_dte <= dte <= cfg.maximum_dte and option_type in {"call", "put"}:
                by_expiry.setdefault(expiry, []).append((abs(strike / index - 1.0), strike, option_type, item))
        except (KeyError, TypeError, ValueError, ZeroDivisionError):
            continue
    selected: list[dict[str, Any]] = []
    for _, items in sorted(by_expiry.items()):
        strikes = sorted({row[1] for row in items}, key=lambda x: (abs(x / index - 1.0), x))[: cfg.max_strikes_per_expiry]
        selected.extend(row[3] for row in items if row[1] in set(strikes))
    if not selected:
        raise RuntimeError("no options in pre-registered DTE neighborhood")
    return selected


def option_row(instrument: dict[str, Any], ticker: dict[str, Any], now: pd.Timestamp, index_name: str, index: float) -> dict[str, Any]:
    bid, ask = ticker.get("best_bid_price"), ticker.get("best_ask_price")
    if bid is None or ask is None or float(bid) < 0 or float(ask) <= 0 or float(ask) < float(bid):
        raise RuntimeError(f"non-executable option quote: {instrument.get('instrument_name')}")
    greeks = ticker.get("greeks") or {}
    underlying = ticker.get("underlying_price") or ticker.get("index_price") or index
    return {
        "timestamp": now.isoformat(), "symbol": instrument["instrument_name"],
        "type": str(instrument["option_type"]).lower(), "strike_price": float(instrument["strike"]),
        "expiration": _utc_ms(instrument["expiration_timestamp"]).isoformat(),
        "bid_price": float(bid), "ask_price": float(ask),
        "bid_amount": ticker.get("best_bid_amount"), "ask_amount": ticker.get("best_ask_amount"),
        "mark_price": ticker.get("mark_price"), "mark_iv": ticker.get("mark_iv"),
        "bid_iv": ticker.get("bid_iv"), "ask_iv": ticker.get("ask_iv"),
        "underlying_price": float(underlying), "index_price": float(index),
        "underlying_index": index_name, "open_interest": ticker.get("open_interest"),
        "delta": greeks.get("delta"), "gamma": greeks.get("gamma"),
        "vega": greeks.get("vega"), "theta": greeks.get("theta"),
        "funding_8h": None, "current_funding": None, "contract_size_usd": None,
    }


def perpetual_row(ticker: dict[str, Any], now: pd.Timestamp, currency: str) -> dict[str, Any]:
    bid, ask = ticker.get("best_bid_price"), ticker.get("best_ask_price")
    mark, index = ticker.get("mark_price"), ticker.get("index_price")
    funding = ticker.get("funding_8h")
    current = ticker.get("current_funding")
    if any(value is None for value in (bid, ask, mark, index, funding)):
        raise RuntimeError("perpetual ticker missing bid/ask/mark/index/funding_8h")
    if float(bid) <= 0 or float(ask) < float(bid) or float(mark) <= 0 or float(index) <= 0:
        raise RuntimeError("invalid perpetual quote")
    return {
        "timestamp": now.isoformat(), "symbol": f"{currency}-PERPETUAL", "type": "perpetual",
        "strike_price": 0.0, "expiration": "", "bid_price": float(bid), "ask_price": float(ask),
        "bid_amount": ticker.get("best_bid_amount"), "ask_amount": ticker.get("best_ask_amount"),
        "mark_price": float(mark), "mark_iv": None, "bid_iv": None, "ask_iv": None,
        "underlying_price": float(index), "index_price": float(index), "underlying_index": f"{currency.lower()}_usd",
        "open_interest": ticker.get("open_interest"), "delta": None, "gamma": None, "vega": None, "theta": None,
        "funding_8h": float(funding), "current_funding": float(current) if current is not None else None,
        "contract_size_usd": 10.0,
    }


def fetch_snapshot(
    cfg: FreeConfig,
    rpc: Callable[..., Any] = public_rpc,
    now: pd.Timestamp | None = None,
    held_symbols: set[str] | None = None,
    instruments_cache: list[dict[str, Any]] | None = None,
) -> pd.DataFrame:
    cfg.validate()
    now = now or pd.Timestamp.now(tz="UTC").floor("s")
    index_name = f"{cfg.currency.lower()}_usd"
    index = float(rpc("get_index_price", {"index_name": index_name}, cfg.request_timeout_seconds)["index_price"])
    instruments = instruments_cache if instruments_cache is not None else rpc(
        "get_instruments", {"currency": cfg.currency, "kind": "option", "expired": "false"}, cfg.request_timeout_seconds
    )
    selected = choose_neighborhood(instruments, index, now, cfg)
    by_name = {str(item["instrument_name"]).upper(): item for item in instruments}
    selected_names = {str(item["instrument_name"]).upper() for item in selected}
    for symbol in held_symbols or set():
        if symbol in by_name and symbol not in selected_names:
            selected.append(by_name[symbol])
            selected_names.add(symbol)
    rows: list[dict[str, Any]] = []
    for instrument in selected:
        try:
            ticker = rpc("ticker", {"instrument_name": instrument["instrument_name"]}, cfg.request_timeout_seconds)
            rows.append(option_row(instrument, ticker, now, index_name, index))
        except Exception:
            continue
    perp = rpc("ticker", {"instrument_name": f"{cfg.currency}-PERPETUAL"}, cfg.request_timeout_seconds)
    rows.append(perpetual_row(perp, now, cfg.currency))
    frame = pd.DataFrame(rows, columns=COLUMNS)
    options = frame[frame["type"].isin(["call", "put"])]
    pair_counts = options.groupby(["expiration", "strike_price"])["type"].nunique()
    if not (pair_counts >= 2).any():
        raise RuntimeError("snapshot has no executable common-strike call/put pair")
    if len(frame[frame["type"] == "perpetual"]) != 1:
        raise RuntimeError("snapshot requires one BTC-PERPETUAL row")
    return frame.sort_values(["type", "expiration", "strike_price", "symbol"]).reset_index(drop=True)


def deterministic_gzip_csv(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = frame.to_csv(index=False, lineterminator="\n", float_format="%.12g").encode("utf-8")
    with path.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as gz:
            gz.write(payload)


def append_snapshot(frame: pd.DataFrame, root: Path) -> Path:
    ts = pd.to_datetime(frame["timestamp"].iloc[0], utc=True)
    path = root / f"{ts:%Y-%m-%d}.free.compact.csv.gz"
    existing = pd.read_csv(path, compression="gzip") if path.exists() else pd.DataFrame(columns=COLUMNS)
    combined = pd.concat([existing, frame], ignore_index=True)
    combined["timestamp"] = pd.to_datetime(combined["timestamp"], utc=True)
    combined = combined.sort_values(["timestamp", "symbol"]).drop_duplicates(["timestamp", "symbol"], keep="last")
    combined["timestamp"] = combined["timestamp"].map(lambda x: x.isoformat())
    deterministic_gzip_csv(combined[COLUMNS], path)
    return path


def discover_files(root: Path) -> list[Path]:
    return sorted(root.rglob("*.free.compact.csv.gz"))


def load_free_data(root: Path) -> pd.DataFrame:
    files = discover_files(root)
    if not files:
        return pd.DataFrame(columns=COLUMNS)
    data = pd.concat([pd.read_csv(path, compression="gzip") for path in files], ignore_index=True)
    data["timestamp"] = pd.to_datetime(data["timestamp"], utc=True, errors="coerce")
    return data.dropna(subset=["timestamp"]).sort_values(["timestamp", "symbol"]).drop_duplicates(["timestamp", "symbol"], keep="last").reset_index(drop=True)


def _window_stats(timestamps: pd.DatetimeIndex, cfg: FreeConfig) -> dict[str, Any]:
    if len(timestamps) < 2:
        return {"active_days": len(set(timestamps.date)) if len(timestamps) else 0, "span_days": 0.0, "active_day_ratio": 0.0, "maximum_gap_hours": None, "ready": False}
    active = len(set(timestamps.date))
    span = (timestamps[-1] - timestamps[0]).total_seconds() / 86400.0 + 1.0
    gaps = pd.Series(timestamps).diff().dt.total_seconds().dropna() / 3600.0
    max_gap = float(gaps.max()) if len(gaps) else math.inf
    ratio = active / max(span, 1.0)
    return {"active_days": active, "span_days": span, "active_day_ratio": ratio, "maximum_gap_hours": max_gap, "ready": active >= cfg.minimum_active_days and ratio >= cfg.minimum_active_day_ratio and max_gap <= cfg.maximum_day_gap_hours}


def free_coverage(data: pd.DataFrame, cfg: FreeConfig) -> dict[str, Any]:
    timestamps = pd.DatetimeIndex(sorted(data.get("timestamp", pd.Series(dtype="datetime64[ns, UTC]")).dropna().unique()))
    if len(timestamps) < 2:
        return {"snapshot_count": int(len(timestamps)), "active_days": 0, "ready": False, "gate_mode": "trailing_or_suffix_AND_intraday", "intraday_gate": {"ready": False, "reason": "insufficient_data"}}
    cutoff = timestamps[-1] - pd.Timedelta(days=cfg.minimum_active_days)
    trailing = timestamps[timestamps >= cutoff]
    suffix_start = len(timestamps) - 1
    for i in range(len(timestamps) - 1, 0, -1):
        if (timestamps[i] - timestamps[i - 1]).total_seconds() / 3600.0 <= cfg.maximum_day_gap_hours:
            suffix_start = i - 1
        else:
            break
    suffix = timestamps[suffix_start:]
    trailing_stats, suffix_stats = _window_stats(trailing, cfg), _window_stats(suffix, cfg)

    current_day = timestamps[-1].floor("D")
    complete = timestamps[timestamps.floor("D") < current_day]
    intraday: dict[str, Any] = {
        "evaluation_mode": "complete_utc_days_only", "complete_days_evaluated": 0,
        "expected_snapshots_per_day": cfg.expected_snapshots_per_complete_day,
        "intraday_ratio": 0.0, "density_p50": 0.0, "density_p10": 0.0,
        "median_gap_minutes": None, "max_operational_gap_minutes": None, "ready": False,
    }
    if len(complete) >= 2:
        by_day = pd.Series(complete).groupby(complete.floor("D")).size()
        within_day_gaps: list[float] = []
        for _, group in pd.Series(complete).groupby(complete.floor("D")):
            gap = group.sort_values().diff().dt.total_seconds().dropna() / 60.0
            within_day_gaps.extend(gap.tolist())
        if within_day_gaps:
            median_gap = float(pd.Series(within_day_gaps).median())
            max_gap = float(max(within_day_gaps))
            density = by_day / cfg.expected_snapshots_per_complete_day
            intraday.update({
                "complete_days_evaluated": int(len(by_day)),
                "intraday_ratio": float(by_day.sum() / (len(by_day) * cfg.expected_snapshots_per_complete_day)),
                "density_p50": float(density.median()), "density_p10": float(density.quantile(0.10)),
                "median_gap_minutes": median_gap, "max_operational_gap_minutes": max_gap,
                "ready": median_gap <= cfg.maximum_median_gap_minutes and max_gap <= cfg.maximum_operational_gap_minutes and float(density.quantile(0.10)) >= cfg.minimum_intraday_ratio,
            })
    ready = (trailing_stats["ready"] or suffix_stats["ready"]) and intraday["ready"]
    return {
        "snapshot_count": int(len(timestamps)), "active_days": int(len(set(timestamps.date))),
        "span_days": float((timestamps[-1] - timestamps[0]).total_seconds() / 86400.0 + 1.0),
        "ready": bool(ready), "gate_mode": "trailing_or_suffix_AND_intraday",
        "trailing_window": trailing_stats, "contiguous_suffix": suffix_stats, "intraday_gate": intraday,
    }


def input_manifest(root: Path) -> dict[str, Any]:
    rows = [{"path": str(path.relative_to(root)), "size": path.stat().st_size, "sha256": sha256_file(path)} for path in discover_files(root)]
    payload = json.dumps(rows, sort_keys=True, separators=(",", ":")).encode()
    return {"version": VERSION, "source": "Deribit public JSON-RPC", "authentication": "none", "historical_backfill": "forbidden", "files": rows, "tree_sha256": hashlib.sha256(payload).hexdigest()}


def record(root: Path, cfg: FreeConfig, held_state_file: Path | None = None, rpc: Callable[..., Any] = public_rpc, sleep: Callable[[float], None] = time.sleep) -> dict[str, Any]:
    cfg.validate()
    root.mkdir(parents=True, exist_ok=True)
    deadline = time.monotonic() + cfg.record_minutes * 60
    captured, errors = 0, []
    cache: list[dict[str, Any]] | None = None
    cache_time = 0.0
    first = True
    while first or time.monotonic() < deadline:
        first = False
        started = time.monotonic()
        try:
            if cache is None or started - cache_time >= cfg.instrument_cache_seconds:
                cache = rpc("get_instruments", {"currency": cfg.currency, "kind": "option", "expired": "false"}, cfg.request_timeout_seconds)
                cache_time = started
            frame = fetch_snapshot(cfg, rpc=rpc, held_symbols=load_held_symbols(held_state_file), instruments_cache=cache)
            append_snapshot(frame, root)
            captured += 1
        except Exception as exc:
            errors.append(f"{datetime.now(timezone.utc).isoformat()} {type(exc).__name__}: {exc}")
        if cfg.record_minutes <= 0:
            break
        now_epoch = time.time()
        next_tick = (int(now_epoch) // cfg.interval_seconds + 1) * cfg.interval_seconds
        wait = min(max(next_tick - now_epoch, 0.0), max(deadline - time.monotonic(), 0.0))
        if wait > 0:
            sleep(wait)
    (root / "RECORDER_ERRORS.log").write_text("\n".join(errors) + ("\n" if errors else ""), encoding="utf-8")
    data = load_free_data(root)
    coverage = free_coverage(data, cfg)
    write_json(root / "FREE_INPUT_MANIFEST.json", input_manifest(root))
    write_json(root / "FREE_COVERAGE.json", coverage)
    return {"captured_snapshots": captured, "errors": len(errors), "coverage": coverage}

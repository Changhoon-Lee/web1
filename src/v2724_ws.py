#!/usr/bin/env python3
"""V27.2.4 public Deribit WebSocket authority recorder.

Only unauthenticated public market-data paths are permitted. REST is used only
for infrequent instrument-universe reconciliation. All real-time option and
BTC-PERPETUAL data comes from ticker.<instrument>.agg2 subscriptions.
"""
from __future__ import annotations

import asyncio
import gzip
import hashlib
import json
import math
import os
import time
import urllib.parse
import urllib.request
from collections import defaultdict, deque
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Awaitable, Callable, Iterable, Sequence

import pandas as pd
import websockets

VERSION = "27.2.4-websocket-authority"
DERIBIT_REST = "https://www.deribit.com/api/v2"
DERIBIT_WS = "wss://www.deribit.com/ws/api/v2"
FORBIDDEN_ENV_VARS = {"TARDIS_API_KEY", "DERIBIT_CLIENT_ID", "DERIBIT_CLIENT_SECRET"}
CONTINUOUS_REST_ALLOWLIST = {"get_instruments"}

COLUMNS = [
    "timestamp", "symbol", "type", "strike_price", "expiration",
    "bid_price", "ask_price", "bid_amount", "ask_amount", "mark_price",
    "mark_iv", "bid_iv", "ask_iv", "underlying_price", "index_price",
    "underlying_index", "open_interest", "delta", "gamma", "vega", "theta",
    "funding_8h", "current_funding", "contract_size_usd",
    "snapshot_target_timestamp", "snapshot_frozen_at", "source_timestamp",
    "source_age_seconds", "connection_epoch", "subscription_epoch",
    "authority", "eligible", "quote_available", "delta_available",
    "failure_reason", "instrument_state",
]


@dataclass(frozen=True)
class WSConfig:
    currency: str = "BTC"
    entry_minimum_dte: float = 21.0
    entry_maximum_dte: float = 45.0
    collection_minimum_dte: float = 7.0
    collection_maximum_dte: float = 45.0
    snapshot_interval_seconds: int = 300
    freeze_settle_seconds: float = 3.0
    universe_refresh_seconds: int = 3600
    subscription_batch_size: int = 500
    reconnect_delay_seconds: float = 5.0
    heartbeat_seconds: float = 30.0
    heartbeat_timeout_seconds: float = 30.0
    minimum_active_days: int = 90
    minimum_active_day_ratio: float = 0.80
    maximum_day_gap_hours: float = 48.0
    expected_snapshots_per_complete_day: int = 288
    minimum_intraday_ratio: float = 0.80
    maximum_median_gap_minutes: float = 10.0
    maximum_operational_gap_minutes: float = 30.0
    minimum_snapshot_authority_ratio: float = 0.99
    minimum_option_symbol_coverage: float = 0.99
    minimum_option_quote_coverage: float = 0.99
    minimum_option_delta_coverage: float = 0.99
    minimum_perpetual_quote_coverage: float = 1.0
    minimum_funding_coverage: float = 1.0
    maximum_median_source_age_seconds: float = 5.0
    maximum_p99_source_age_seconds: float = 30.0
    maximum_source_age_seconds: float = 60.0
    maximum_connection_gap_seconds: float = 30.0
    request_timeout_seconds: int = 10
    websocket_url: str = DERIBIT_WS

    def validate(self) -> None:
        if self.currency != "BTC":
            raise ValueError("V27.2.4 supports BTC only")
        if not 0 <= self.collection_minimum_dte <= self.entry_minimum_dte:
            raise ValueError("collection universe must include the entry lower bound")
        if not self.entry_minimum_dte <= self.entry_maximum_dte <= self.collection_maximum_dte:
            raise ValueError("collection universe must include the entry upper bound")
        if self.snapshot_interval_seconds <= 0 or 86400 % self.snapshot_interval_seconds:
            raise ValueError("snapshot interval must divide one UTC day")
        if not 1 <= self.subscription_batch_size <= 500:
            raise ValueError("subscription batches must be between 1 and 500 channels")
        if self.freeze_settle_seconds < 0:
            raise ValueError("negative freeze settle delay")
        for value in (
            self.minimum_snapshot_authority_ratio,
            self.minimum_option_symbol_coverage,
            self.minimum_option_quote_coverage,
            self.minimum_option_delta_coverage,
            self.minimum_perpetual_quote_coverage,
            self.minimum_funding_coverage,
        ):
            if not 0 < value <= 1:
                raise ValueError("coverage thresholds must be in (0, 1]")


def _utc(value: Any) -> pd.Timestamp:
    if isinstance(value, pd.Timestamp):
        ts = value
    elif isinstance(value, (int, float)):
        ts = pd.to_datetime(value, unit="ms", utc=True)
    else:
        ts = pd.to_datetime(value, utc=True)
    return ts.tz_convert("UTC") if ts.tzinfo else ts.tz_localize("UTC")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    tmp.replace(path)


def public_rest(method: str, params: dict[str, Any] | None = None, timeout: int = 10) -> Any:
    if any(os.getenv(name) for name in FORBIDDEN_ENV_VARS):
        raise RuntimeError("free-only mode refuses paid/private credentials")
    if method not in CONTINUOUS_REST_ALLOWLIST:
        raise RuntimeError(f"continuous authority mode forbids REST method: {method}")
    query = urllib.parse.urlencode(params or {})
    request = urllib.request.Request(
        f"{DERIBIT_REST}/public/{method}?{query}",
        headers={"User-Agent": "V27.2.4-WebSocket-Authority"},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        payload = json.loads(response.read().decode("utf-8"))
    if "error" in payload:
        raise RuntimeError(json.dumps(payload["error"], sort_keys=True))
    return payload.get("result")


def choose_collection_universe(
    instruments: Iterable[dict[str, Any]], now: pd.Timestamp, cfg: WSConfig
) -> dict[str, dict[str, Any]]:
    selected: dict[str, dict[str, Any]] = {}
    for item in instruments:
        try:
            expiry = _utc(item["expiration_timestamp"])
            dte = (expiry - now).total_seconds() / 86400.0
            option_type = str(item.get("option_type", "")).lower()
            if cfg.collection_minimum_dte <= dte <= cfg.collection_maximum_dte and option_type in {"call", "put"}:
                selected[str(item["instrument_name"]).upper()] = dict(item)
        except (KeyError, TypeError, ValueError, ZeroDivisionError):
            continue
    if not selected:
        raise RuntimeError("no options in the frozen collection universe")
    return selected


def choose_entry_universe(
    instruments: Iterable[dict[str, Any]], now: pd.Timestamp, cfg: WSConfig
) -> dict[str, dict[str, Any]]:
    all_items = choose_collection_universe(instruments, now, cfg)
    selected: dict[str, dict[str, Any]] = {}
    for symbol, item in all_items.items():
        expiry = _utc(item["expiration_timestamp"])
        dte = (expiry - now).total_seconds() / 86400.0
        if cfg.entry_minimum_dte <= dte <= cfg.entry_maximum_dte:
            selected[symbol] = item
    return selected


def ticker_channel(symbol: str) -> str:
    return f"ticker.{symbol}.agg2"


def subscription_channels(option_symbols: Iterable[str], currency: str = "BTC") -> list[str]:
    channels = [ticker_channel(symbol) for symbol in sorted(set(option_symbols))]
    channels.append(ticker_channel(f"{currency}-PERPETUAL"))
    channels.append(f"instrument.state.option.{currency}")
    return channels


def batch_channels(channels: Sequence[str], batch_size: int = 500) -> list[list[str]]:
    if not 1 <= batch_size <= 500:
        raise ValueError("Deribit public subscription batch limit is 500")
    return [list(channels[i:i + batch_size]) for i in range(0, len(channels), batch_size)]


@dataclass(frozen=True)
class TickerRecord:
    source_timestamp: pd.Timestamp
    received_at: pd.Timestamp
    data: dict[str, Any]
    connection_epoch: int
    subscription_epoch: int


class TickerStateStore:
    """Point-in-time ticker state with reconnect and cutoff semantics."""

    def __init__(self, history_size: int = 4096) -> None:
        self.history_size = history_size
        self.history: dict[str, deque[TickerRecord]] = defaultdict(lambda: deque(maxlen=history_size))
        self.expected_symbols: set[str] = set()
        self.hydrated_symbols: set[str] = set()
        self.connection_epoch = 0
        self.subscription_epoch = 0
        self.connection_started_at: pd.Timestamp | None = None
        self.last_disconnect_at: pd.Timestamp | None = None
        self.last_connection_gap_seconds: float | None = None
        self.data_gap_open = True
        self.universe_refresh_requested = False

    def begin_connection(self, expected_symbols: Iterable[str], now: pd.Timestamp | None = None) -> None:
        now = now or pd.Timestamp.now(tz="UTC")
        self.connection_epoch += 1
        self.subscription_epoch += 1
        self.connection_started_at = now
        self.expected_symbols = {str(symbol).upper() for symbol in expected_symbols}
        self.hydrated_symbols = set()
        self.data_gap_open = True
        if self.last_disconnect_at is not None:
            self.last_connection_gap_seconds = max((now - self.last_disconnect_at).total_seconds(), 0.0)

    def update_expected_symbols(self, expected_symbols: Iterable[str]) -> tuple[set[str], set[str]]:
        new = {str(symbol).upper() for symbol in expected_symbols}
        additions = new - self.expected_symbols
        removals = self.expected_symbols - new
        self.expected_symbols = new
        self.hydrated_symbols.intersection_update(new)
        if additions or removals:
            self.subscription_epoch += 1
            self.data_gap_open = True
        return additions, removals

    def mark_disconnect(self, now: pd.Timestamp | None = None) -> None:
        self.last_disconnect_at = now or pd.Timestamp.now(tz="UTC")
        self.data_gap_open = True
        self.hydrated_symbols = set()

    def ingest_message(self, payload: dict[str, Any], received_at: pd.Timestamp | None = None) -> str | None:
        received_at = received_at or pd.Timestamp.now(tz="UTC")
        params = payload.get("params") or {}
        channel = str(params.get("channel", ""))
        data = params.get("data")
        if channel.startswith("instrument.state.option."):
            self.universe_refresh_requested = True
            return "instrument_state"
        if not channel.startswith("ticker.") or not isinstance(data, dict):
            return None
        symbol = str(data.get("instrument_name") or channel.split(".", 2)[1]).upper()
        timestamp = data.get("timestamp")
        if timestamp is None:
            return None
        source_timestamp = _utc(timestamp)
        existing = self.history[symbol]
        if existing and source_timestamp < existing[-1].source_timestamp:
            return "out_of_order_ignored"
        if existing and source_timestamp == existing[-1].source_timestamp and data == existing[-1].data:
            return "duplicate_ignored"
        existing.append(TickerRecord(
            source_timestamp=source_timestamp,
            received_at=received_at,
            data=dict(data),
            connection_epoch=self.connection_epoch,
            subscription_epoch=self.subscription_epoch,
        ))
        if symbol in self.expected_symbols:
            self.hydrated_symbols.add(symbol)
        if self.expected_symbols and self.expected_symbols.issubset(self.hydrated_symbols):
            self.data_gap_open = False
        return symbol

    @property
    def fully_hydrated(self) -> bool:
        return bool(self.expected_symbols) and self.expected_symbols.issubset(self.hydrated_symbols) and not self.data_gap_open

    def latest_at_or_before(self, symbol: str, cutoff: pd.Timestamp) -> TickerRecord | None:
        for record in reversed(self.history.get(symbol.upper(), ())):
            if record.source_timestamp <= cutoff:
                return record
        return None


def _base_row(
    symbol: str,
    option_meta: dict[str, Any] | None,
    cutoff: pd.Timestamp,
    frozen_at: pd.Timestamp,
    record: TickerRecord | None,
    store: TickerStateStore,
    failure_reason: str = "",
) -> dict[str, Any]:
    is_perp = symbol == "BTC-PERPETUAL"
    option_type = str((option_meta or {}).get("option_type", "")).lower()
    row: dict[str, Any] = {column: None for column in COLUMNS}
    row.update({
        "timestamp": cutoff.isoformat(),
        "symbol": symbol,
        "type": "perpetual" if is_perp else option_type,
        "strike_price": 0.0 if is_perp else (option_meta or {}).get("strike"),
        "expiration": "" if is_perp else _utc((option_meta or {})["expiration_timestamp"]).isoformat(),
        "snapshot_target_timestamp": cutoff.isoformat(),
        "snapshot_frozen_at": frozen_at.isoformat(),
        "connection_epoch": store.connection_epoch,
        "subscription_epoch": store.subscription_epoch,
        "eligible": True,
        "authority": False,
        "quote_available": False,
        "delta_available": False if not is_perp else None,
        "failure_reason": failure_reason,
        "contract_size_usd": 10.0 if is_perp else None,
    })
    if record is None:
        row["failure_reason"] = failure_reason or "NO_TICKER_AT_OR_BEFORE_CUTOFF"
        return row
    data = record.data
    age = max((cutoff - record.source_timestamp).total_seconds(), 0.0)
    bid, ask = data.get("best_bid_price"), data.get("best_ask_price")
    quote_ok = bid is not None and ask is not None and float(bid) >= 0 and float(ask) > 0 and float(ask) >= float(bid)
    greeks = data.get("greeks") or {}
    delta = greeks.get("delta")
    delta_ok = is_perp or (delta is not None and math.isfinite(float(delta)))
    current_epoch = record.connection_epoch == store.connection_epoch
    row.update({
        "bid_price": float(bid) if bid is not None else None,
        "ask_price": float(ask) if ask is not None else None,
        "bid_amount": data.get("best_bid_amount"),
        "ask_amount": data.get("best_ask_amount"),
        "mark_price": data.get("mark_price"),
        "mark_iv": data.get("mark_iv"),
        "bid_iv": data.get("bid_iv"),
        "ask_iv": data.get("ask_iv"),
        "underlying_price": data.get("underlying_price") or data.get("index_price"),
        "index_price": data.get("index_price") or data.get("underlying_price"),
        "underlying_index": "btc_usd",
        "open_interest": data.get("open_interest"),
        "delta": delta,
        "gamma": greeks.get("gamma"),
        "vega": greeks.get("vega"),
        "theta": greeks.get("theta"),
        "funding_8h": data.get("funding_8h") if is_perp else None,
        "current_funding": data.get("current_funding") if is_perp else None,
        "source_timestamp": record.source_timestamp.isoformat(),
        "source_age_seconds": age,
        "connection_epoch": record.connection_epoch,
        "subscription_epoch": record.subscription_epoch,
        "quote_available": quote_ok,
        "delta_available": delta_ok if not is_perp else None,
        "instrument_state": data.get("state"),
    })
    reasons: list[str] = []
    if not current_epoch:
        reasons.append("PRE_RECONNECT_TICKER")
    if not quote_ok:
        reasons.append("NO_EXECUTABLE_QUOTE")
    if not delta_ok:
        reasons.append("MISSING_ACTUAL_DELTA")
    if store.data_gap_open:
        reasons.append("CONNECTION_NOT_REHYDRATED")
    row["failure_reason"] = "|".join(reasons)
    row["authority"] = current_epoch and quote_ok and delta_ok and store.fully_hydrated
    return row


def freeze_snapshot(
    store: TickerStateStore,
    option_universe: dict[str, dict[str, Any]],
    cutoff: pd.Timestamp,
    cfg: WSConfig,
    frozen_at: pd.Timestamp | None = None,
) -> pd.DataFrame:
    cfg.validate()
    cutoff = _utc(cutoff).floor(f"{cfg.snapshot_interval_seconds}s")
    frozen_at = frozen_at or pd.Timestamp.now(tz="UTC")
    expected = set(option_universe) | {f"{cfg.currency}-PERPETUAL"}
    rows = [
        _base_row(
            symbol,
            option_universe.get(symbol),
            cutoff,
            frozen_at,
            store.latest_at_or_before(symbol, cutoff),
            store,
        )
        for symbol in sorted(expected)
    ]
    frame = pd.DataFrame(rows, columns=COLUMNS)
    if set(frame["symbol"]) != expected:
        raise RuntimeError("snapshot completeness failed")
    return frame.sort_values(["type", "expiration", "strike_price", "symbol"], na_position="last").reset_index(drop=True)


def snapshot_authority(frame: pd.DataFrame, cfg: WSConfig) -> dict[str, Any]:
    options = frame[frame["type"].isin(["call", "put"])].copy()
    perp = frame[frame["type"] == "perpetual"].copy()
    expected_options = max(len(options), 1)
    symbol_coverage = float(options["eligible"].fillna(False).mean()) if len(options) else 0.0
    quote_coverage = float(options["quote_available"].fillna(False).mean()) if len(options) else 0.0
    delta_coverage = float(options["delta_available"].fillna(False).mean()) if len(options) else 0.0
    perp_quote = float(perp["quote_available"].fillna(False).mean()) if len(perp) else 0.0
    funding = float(perp["funding_8h"].notna().mean()) if len(perp) else 0.0
    ages = pd.to_numeric(frame.loc[frame["quote_available"].fillna(False), "source_age_seconds"], errors="coerce").dropna()
    median_age = float(ages.median()) if len(ages) else math.inf
    p99_age = float(ages.quantile(0.99)) if len(ages) else math.inf
    max_age = float(ages.max()) if len(ages) else math.inf
    connection_epochs = pd.to_numeric(frame["connection_epoch"], errors="coerce").dropna().unique()
    all_rows_authority = bool(frame["authority"].fillna(False).all())
    ready = (
        len(perp) == 1
        and symbol_coverage >= cfg.minimum_option_symbol_coverage
        and quote_coverage >= cfg.minimum_option_quote_coverage
        and delta_coverage >= cfg.minimum_option_delta_coverage
        and perp_quote >= cfg.minimum_perpetual_quote_coverage
        and funding >= cfg.minimum_funding_coverage
        and median_age <= cfg.maximum_median_source_age_seconds
        and p99_age <= cfg.maximum_p99_source_age_seconds
        and max_age <= cfg.maximum_source_age_seconds
        and len(connection_epochs) == 1
        and all_rows_authority
    )
    return {
        "version": VERSION,
        "expected_option_symbols": expected_options,
        "option_symbol_coverage": symbol_coverage,
        "option_quote_coverage": quote_coverage,
        "option_delta_coverage": delta_coverage,
        "perpetual_quote_coverage": perp_quote,
        "funding_coverage": funding,
        "median_source_age_seconds": median_age,
        "p99_source_age_seconds": p99_age,
        "maximum_source_age_seconds": max_age,
        "single_connection_epoch": len(connection_epochs) == 1,
        "all_rows_authority": all_rows_authority,
        "ready": bool(ready),
    }


def deterministic_gzip_csv(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = frame[COLUMNS].to_csv(index=False, lineterminator="\n", float_format="%.12g").encode("utf-8")
    with path.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as stream:
            stream.write(payload)


def append_snapshot(frame: pd.DataFrame, root: Path) -> Path:
    target = _utc(frame["timestamp"].iloc[0])
    path = root / f"{target:%Y-%m-%d}.ws.compact.csv.gz"
    existing = pd.read_csv(path, compression="gzip", low_memory=False) if path.exists() else pd.DataFrame(columns=COLUMNS)
    combined = pd.concat([existing, frame], ignore_index=True)
    combined["timestamp"] = pd.to_datetime(combined["timestamp"], utc=True, errors="coerce")
    combined = combined.dropna(subset=["timestamp"]).sort_values(["timestamp", "symbol"]).drop_duplicates(["timestamp", "symbol"], keep="last")
    combined["timestamp"] = combined["timestamp"].map(lambda value: value.isoformat())
    deterministic_gzip_csv(combined.reindex(columns=COLUMNS), path)
    return path


def discover_files(root: Path) -> list[Path]:
    return sorted(root.rglob("*.ws.compact.csv.gz"))


def load_data(root: Path) -> pd.DataFrame:
    files = discover_files(root)
    if not files:
        return pd.DataFrame(columns=COLUMNS)
    data = pd.concat([pd.read_csv(path, compression="gzip", low_memory=False) for path in files], ignore_index=True)
    data["timestamp"] = pd.to_datetime(data["timestamp"], utc=True, errors="coerce")
    return data.dropna(subset=["timestamp"]).sort_values(["timestamp", "symbol"]).drop_duplicates(["timestamp", "symbol"], keep="last").reset_index(drop=True)


def _window_stats(timestamps: pd.DatetimeIndex, cfg: WSConfig) -> dict[str, Any]:
    if len(timestamps) < 2:
        return {"active_days": 0, "span_days": 0.0, "active_day_ratio": 0.0, "maximum_gap_hours": None, "ready": False}
    active_days = len(set(timestamps.date))
    span_days = (timestamps[-1] - timestamps[0]).total_seconds() / 86400.0 + 1.0
    gaps = pd.Series(timestamps).diff().dt.total_seconds().dropna() / 3600.0
    maximum_gap = float(gaps.max()) if len(gaps) else math.inf
    ratio = active_days / max(span_days, 1.0)
    return {
        "active_days": active_days,
        "span_days": span_days,
        "active_day_ratio": ratio,
        "maximum_gap_hours": maximum_gap,
        "ready": active_days >= cfg.minimum_active_days and ratio >= cfg.minimum_active_day_ratio and maximum_gap <= cfg.maximum_day_gap_hours,
    }


def coverage(data: pd.DataFrame, cfg: WSConfig) -> dict[str, Any]:
    if data.empty:
        return {"version": VERSION, "snapshot_count": 0, "active_days": 0, "ready": False, "reason": "insufficient_data"}
    timestamps = pd.DatetimeIndex(sorted(data["timestamp"].dropna().unique()))
    if len(timestamps) < 2:
        return {"version": VERSION, "snapshot_count": int(len(timestamps)), "active_days": 0, "ready": False, "reason": "insufficient_data"}
    cutoff = timestamps[-1] - pd.Timedelta(cfg.minimum_active_days, unit="D")
    trailing = timestamps[timestamps >= cutoff]
    suffix_start = len(timestamps) - 1
    for index in range(len(timestamps) - 1, 0, -1):
        if (timestamps[index] - timestamps[index - 1]).total_seconds() / 3600.0 <= cfg.maximum_day_gap_hours:
            suffix_start = index - 1
        else:
            break
    suffix = timestamps[suffix_start:]
    trailing_stats = _window_stats(trailing, cfg)
    suffix_stats = _window_stats(suffix, cfg)
    current_day = timestamps[-1].floor("D")
    complete = timestamps[timestamps.floor("D") < current_day]
    intraday = {"complete_days_evaluated": 0, "density_p10": 0.0, "median_gap_minutes": None, "maximum_gap_minutes": None, "ready": False}
    if len(complete) >= 2:
        series = pd.Series(complete)
        by_day = series.groupby(complete.floor("D")).size()
        within: list[float] = []
        for _, group in series.groupby(complete.floor("D")):
            within.extend((group.sort_values().diff().dt.total_seconds().dropna() / 60.0).tolist())
        if within:
            density = by_day / cfg.expected_snapshots_per_complete_day
            median_gap = float(pd.Series(within).median())
            maximum_gap = float(max(within))
            intraday = {
                "complete_days_evaluated": int(len(by_day)),
                "density_p10": float(density.quantile(0.10)),
                "median_gap_minutes": median_gap,
                "maximum_gap_minutes": maximum_gap,
                "ready": float(density.quantile(0.10)) >= cfg.minimum_intraday_ratio and median_gap <= cfg.maximum_median_gap_minutes and maximum_gap <= cfg.maximum_operational_gap_minutes,
            }
    per_snapshot = []
    for _, group in data.groupby("timestamp", sort=True):
        per_snapshot.append(snapshot_authority(group, cfg))
    authority_ratio = float(sum(item["ready"] for item in per_snapshot) / len(per_snapshot)) if per_snapshot else 0.0
    authority_gate = {
        "snapshot_authority_ratio": authority_ratio,
        "minimum_snapshot_authority_ratio": cfg.minimum_snapshot_authority_ratio,
        "ready": authority_ratio >= cfg.minimum_snapshot_authority_ratio,
    }
    ready = (trailing_stats["ready"] or suffix_stats["ready"]) and intraday["ready"] and authority_gate["ready"]
    return {
        "version": VERSION,
        "snapshot_count": int(len(timestamps)),
        "active_days": int(len(set(timestamps.date))),
        "ready": bool(ready),
        "gate_mode": "trailing_or_suffix_AND_intraday_AND_websocket_authority",
        "trailing_window": trailing_stats,
        "contiguous_suffix": suffix_stats,
        "intraday_gate": intraday,
        "websocket_authority_gate": authority_gate,
    }


def input_manifest(root: Path) -> dict[str, Any]:
    files = [{"path": str(path.relative_to(root)), "size": path.stat().st_size, "sha256": sha256_file(path)} for path in discover_files(root)]
    encoded = json.dumps(files, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return {
        "version": VERSION,
        "source": "Deribit public WebSocket ticker.<instrument>.agg2",
        "authentication": "none",
        "historical_backfill": "forbidden",
        "files": files,
        "tree_sha256": hashlib.sha256(encoded).hexdigest(),
    }


class DeribitWSRecorder:
    def __init__(
        self,
        root: Path,
        cfg: WSConfig | None = None,
        rest: Callable[..., Any] = public_rest,
        connect: Callable[..., Any] = websockets.connect,
        on_snapshot: Callable[[Path, pd.DataFrame, dict[str, Any]], Awaitable[None] | None] | None = None,
    ) -> None:
        self.root = root
        self.cfg = cfg or WSConfig()
        self.rest = rest
        self.connect = connect
        self.on_snapshot = on_snapshot
        self.store = TickerStateStore()
        self.universe: dict[str, dict[str, Any]] = {}
        self.request_id = 1000
        self.errors_path = root / "WEBSOCKET_ERRORS.log"
        self.gaps_path = root / "CONNECTION_GAPS.jsonl"

    def _next_id(self) -> int:
        self.request_id += 1
        return self.request_id

    def refresh_universe(self, now: pd.Timestamp | None = None) -> dict[str, dict[str, Any]]:
        now = now or pd.Timestamp.now(tz="UTC")
        instruments = self.rest(
            "get_instruments",
            {"currency": self.cfg.currency, "kind": "option", "expired": "false"},
            self.cfg.request_timeout_seconds,
        )
        self.universe = choose_collection_universe(instruments, now, self.cfg)
        return self.universe

    async def _send_subscriptions(self, websocket: Any, symbols: Iterable[str]) -> None:
        channels = subscription_channels(symbols, self.cfg.currency)
        for batch in batch_channels(channels, self.cfg.subscription_batch_size):
            await websocket.send(json.dumps({
                "jsonrpc": "2.0",
                "id": self._next_id(),
                "method": "public/subscribe",
                "params": {"channels": batch},
            }, separators=(",", ":")))

    async def _send_unsubscriptions(self, websocket: Any, symbols: Iterable[str]) -> None:
        channels = [ticker_channel(symbol) for symbol in sorted(set(symbols))]
        for batch in batch_channels(channels, self.cfg.subscription_batch_size):
            await websocket.send(json.dumps({
                "jsonrpc": "2.0",
                "id": self._next_id(),
                "method": "public/unsubscribe",
                "params": {"channels": batch},
            }, separators=(",", ":")))

    async def _freeze_and_write(self, cutoff: pd.Timestamp) -> None:
        frame = freeze_snapshot(self.store, self.universe, cutoff, self.cfg)
        authority = snapshot_authority(frame, self.cfg)
        path = append_snapshot(frame, self.root)
        write_json(self.root / "WS_INPUT_MANIFEST.json", input_manifest(self.root))
        write_json(self.root / "WS_COVERAGE.json", coverage(load_data(self.root), self.cfg))
        if self.on_snapshot is not None:
            result = self.on_snapshot(path, frame, authority)
            if asyncio.iscoroutine(result):
                await result

    async def _connection_loop(self, websocket: Any) -> None:
        now = pd.Timestamp.now(tz="UTC")
        self.refresh_universe(now)
        expected = set(self.universe) | {f"{self.cfg.currency}-PERPETUAL"}
        self.store.begin_connection(expected, now)
        await self._send_subscriptions(websocket, self.universe)
        next_refresh = time.monotonic() + self.cfg.universe_refresh_seconds
        interval = self.cfg.snapshot_interval_seconds
        next_cutoff_epoch = (int(time.time()) // interval + 1) * interval
        while True:
            freeze_at = next_cutoff_epoch + self.cfg.freeze_settle_seconds
            timeout = max(min(freeze_at - time.time(), 5.0), 0.05)
            try:
                raw = await asyncio.wait_for(websocket.recv(), timeout=timeout)
                payload = json.loads(raw)
                self.store.ingest_message(payload)
            except asyncio.TimeoutError:
                pass
            if time.monotonic() >= next_refresh or self.store.universe_refresh_requested:
                old = set(self.universe)
                self.refresh_universe(pd.Timestamp.now(tz="UTC"))
                additions, removals = self.store.update_expected_symbols(set(self.universe) | {f"{self.cfg.currency}-PERPETUAL"})
                option_additions = additions - {f"{self.cfg.currency}-PERPETUAL"}
                option_removals = removals - {f"{self.cfg.currency}-PERPETUAL"}
                if option_additions:
                    await self._send_subscriptions(websocket, option_additions)
                if option_removals:
                    await self._send_unsubscriptions(websocket, option_removals)
                self.store.universe_refresh_requested = False
                next_refresh = time.monotonic() + self.cfg.universe_refresh_seconds
            if time.time() >= freeze_at:
                cutoff = pd.Timestamp(next_cutoff_epoch, unit="s", tz="UTC")
                await self._freeze_and_write(cutoff)
                next_cutoff_epoch += interval

    async def run_forever(self) -> None:
        self.cfg.validate()
        self.root.mkdir(parents=True, exist_ok=True)
        while True:
            try:
                async with self.connect(
                    self.cfg.websocket_url,
                    ping_interval=self.cfg.heartbeat_seconds,
                    ping_timeout=self.cfg.heartbeat_timeout_seconds,
                    close_timeout=10,
                    max_queue=20000,
                ) as websocket:
                    await self._connection_loop(websocket)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                now = pd.Timestamp.now(tz="UTC")
                self.store.mark_disconnect(now)
                with self.errors_path.open("a", encoding="utf-8") as handle:
                    handle.write(f"{now.isoformat()} {type(exc).__name__}: {exc}\n")
                with self.gaps_path.open("a", encoding="utf-8") as handle:
                    handle.write(json.dumps({"timestamp": now.isoformat(), "event": "DISCONNECT", "error": f"{type(exc).__name__}: {exc}"}, sort_keys=True) + "\n")
                await asyncio.sleep(self.cfg.reconnect_delay_seconds)


async def record_forever(
    root: Path,
    cfg: WSConfig | None = None,
    on_snapshot: Callable[[Path, pd.DataFrame, dict[str, Any]], Awaitable[None] | None] | None = None,
) -> None:
    await DeribitWSRecorder(root=root, cfg=cfg, on_snapshot=on_snapshot).run_forever()

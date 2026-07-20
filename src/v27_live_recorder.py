#!/usr/bin/env python3
"""Forward-OOS Deribit public WebSocket recorder for V27.

This recorder is not used to backfill history. It creates new point-in-time data
from the moment it is started and can be scheduled repeatedly.
"""
from __future__ import annotations

import argparse
import asyncio
import csv
import gzip
import json
import math
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import websockets

from v27_core import VERSION, sha256_file, write_json

REST = "https://www.deribit.com/api/v2/"
WS = "wss://www.deribit.com/ws/api/v2"
FIELDS = [
    "exchange", "symbol", "timestamp", "local_timestamp", "type", "strike_price", "expiration",
    "open_interest", "last_price", "bid_price", "bid_amount", "bid_iv", "ask_price", "ask_amount",
    "ask_iv", "mark_price", "mark_iv", "underlying_index", "underlying_price", "delta", "gamma",
    "vega", "theta", "rho",
]


def rest_rpc(method: str, params: dict[str, Any]) -> Any:
    query = urllib.parse.urlencode(params)
    url = f"{REST}public/{method}?{query}"
    with urllib.request.urlopen(url, timeout=60) as response:
        payload = json.loads(response.read().decode("utf-8"))
    if "error" in payload:
        raise RuntimeError(payload["error"])
    return payload["result"]


def discover_instruments(currency: str, minimum_dte: float, maximum_dte: float, moneyness: float) -> tuple[list[dict[str, Any]], float]:
    index = rest_rpc("get_index_price", {"index_name": f"{currency.lower()}_usd"})
    spot = float(index["index_price"])
    instruments = rest_rpc("get_instruments", {"currency": currency, "kind": "option", "expired": "false"})
    now_ms = int(time.time() * 1000)
    selected = []
    for item in instruments:
        expiry = int(item["expiration_timestamp"])
        dte = (expiry - now_ms) / 86_400_000.0
        strike = float(item.get("strike", 0.0))
        if minimum_dte <= dte <= maximum_dte and spot > 0 and abs(strike / spot - 1.0) <= moneyness:
            selected.append(item)
    return selected, spot


def normalize_ticker(data: dict[str, Any], instrument: dict[str, Any], local_us: int) -> dict[str, Any]:
    greeks = data.get("greeks") or {}
    option_type = instrument.get("option_type", "")
    return {
        "exchange": "deribit",
        "symbol": instrument["instrument_name"],
        "timestamp": int(data.get("timestamp", local_us // 1000)) * 1000,
        "local_timestamp": local_us,
        "type": option_type,
        "strike_price": instrument.get("strike"),
        "expiration": int(instrument["expiration_timestamp"]) * 1000,
        "open_interest": data.get("open_interest"),
        "last_price": data.get("last_price"),
        "bid_price": data.get("best_bid_price"),
        "bid_amount": data.get("best_bid_amount"),
        "bid_iv": data.get("bid_iv"),
        "ask_price": data.get("best_ask_price"),
        "ask_amount": data.get("best_ask_amount"),
        "ask_iv": data.get("ask_iv"),
        "mark_price": data.get("mark_price"),
        "mark_iv": data.get("mark_iv"),
        "underlying_index": data.get("underlying_index"),
        "underlying_price": data.get("underlying_price") or data.get("index_price"),
        "delta": greeks.get("delta"),
        "gamma": greeks.get("gamma"),
        "vega": greeks.get("vega"),
        "theta": greeks.get("theta"),
        "rho": greeks.get("rho"),
    }


async def record(destination: Path, currency: str, minutes: int, snapshot_minutes: int) -> dict[str, Any]:
    instruments, initial_spot = discover_instruments(currency, 5.0, 60.0, 0.15)
    if not instruments:
        raise RuntimeError("no eligible Deribit options")
    metadata = {item["instrument_name"]: item for item in instruments}
    channels = [f"ticker.{name}.100ms" for name in metadata]
    latest: dict[str, dict[str, Any]] = {}
    destination.parent.mkdir(parents=True, exist_ok=True)
    started = datetime.now(timezone.utc)
    deadline = time.monotonic() + minutes * 60
    next_flush = time.monotonic() + snapshot_minutes * 60
    rows_written = 0
    request_id = 1
    async with websockets.connect(WS, ping_interval=20, ping_timeout=20, max_size=32 * 1024 * 1024) as ws:
        for start in range(0, len(channels), 500):
            batch = channels[start:start + 500]
            await ws.send(json.dumps({"jsonrpc": "2.0", "id": request_id, "method": "public/subscribe", "params": {"channels": batch}}))
            request_id += 1
            response = json.loads(await ws.recv())
            if "error" in response:
                raise RuntimeError(response["error"])
        with gzip.open(destination, "wt", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=FIELDS)
            writer.writeheader()
            while time.monotonic() < deadline:
                timeout = max(0.1, min(5.0, deadline - time.monotonic()))
                try:
                    payload = json.loads(await asyncio.wait_for(ws.recv(), timeout=timeout))
                except asyncio.TimeoutError:
                    payload = None
                if payload and payload.get("method") == "subscription":
                    params = payload.get("params") or {}
                    channel = str(params.get("channel", ""))
                    parts = channel.split(".")
                    if len(parts) >= 3:
                        symbol = parts[1]
                        if symbol in metadata:
                            local_us = time.time_ns() // 1000
                            row = normalize_ticker(params.get("data") or {}, metadata[symbol], local_us)
                            if row["bid_price"] is not None and row["ask_price"] is not None and row["underlying_price"] is not None:
                                latest[symbol] = row
                if time.monotonic() >= next_flush:
                    snapshot_us = time.time_ns() // 1000
                    for symbol in sorted(latest):
                        row = dict(latest[symbol])
                        row["local_timestamp"] = snapshot_us
                        writer.writerow(row)
                        rows_written += 1
                    handle.flush()
                    next_flush += snapshot_minutes * 60
    ended = datetime.now(timezone.utc)
    manifest = {
        "version": VERSION,
        "source": "Deribit public WebSocket v2",
        "mode": "FORWARD_OOS_ONLY",
        "currency": currency,
        "initial_index_price": initial_spot,
        "instrument_count": len(instruments),
        "rows_written": rows_written,
        "started_at": started.isoformat(),
        "ended_at": ended.isoformat(),
        "snapshot_minutes": snapshot_minutes,
        "path": str(destination),
        "sha256": sha256_file(destination),
    }
    write_json(destination.with_suffix(destination.suffix + ".manifest.json"), manifest)
    return manifest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Record forward Deribit option-chain snapshots")
    parser.add_argument("--currency", default="BTC", choices=["BTC", "ETH"])
    parser.add_argument("--minutes", type=int, default=60)
    parser.add_argument("--snapshot-minutes", type=int, default=5)
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = Path(__file__).resolve().parents[1]
    if args.output:
        destination = args.output.expanduser().resolve()
    else:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        destination = root / f"data/v27_forward/deribit_options_chain_{stamp}.csv.gz"
    result = asyncio.run(record(destination, args.currency, args.minutes, args.snapshot_minutes))
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

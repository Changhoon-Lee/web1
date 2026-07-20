from __future__ import annotations

import asyncio
import csv
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import requests

from .v271_core import sha256_file, utc_now_iso, write_json

DERIBIT_HTTP = "https://www.deribit.com/api/v2"
DERIBIT_WS = "wss://www.deribit.com/ws/api/v2"


class DeribitPublicClient:
    def __init__(self, timeout: int = 60, session: requests.Session | None = None):
        self.timeout = timeout
        self.session = session or requests.Session()
        self.request_id = 0

    def call(self, method: str, params: dict[str, Any] | None = None) -> Any:
        self.request_id += 1
        payload = {"jsonrpc": "2.0", "id": self.request_id, "method": method, "params": params or {}}
        response = self.session.post(DERIBIT_HTTP, json=payload, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()
        if "error" in data:
            raise RuntimeError(f"Deribit {method}: {data['error']}")
        return data["result"]


def fetch_dvol(client: DeribitPublicClient, start_ms: int, end_ms: int, resolution: str = "3600") -> tuple[pd.DataFrame, list[dict[str, Any]]]:
    rows: list[list[Any]] = []
    raw_pages: list[dict[str, Any]] = []
    cursor_end = end_ms
    while True:
        result = client.call("public/get_volatility_index_data", {"currency": "BTC", "start_timestamp": start_ms, "end_timestamp": cursor_end, "resolution": resolution})
        page_rows = result.get("data", []) if isinstance(result, dict) else []
        raw_pages.append(result)
        rows.extend(page_rows)
        continuation = result.get("continuation") if isinstance(result, dict) else None
        if continuation is None or continuation >= cursor_end or not page_rows:
            break
        cursor_end = int(continuation)
        time.sleep(0.05)
    frame = pd.DataFrame(rows, columns=["timestamp", "open", "high", "low", "dvol"])
    if not frame.empty:
        frame["timestamp"] = pd.to_datetime(frame["timestamp"], unit="ms", utc=True)
        frame = frame.drop_duplicates("timestamp", keep="last").sort_values("timestamp")
    return frame[["timestamp", "dvol"]] if not frame.empty else pd.DataFrame(columns=["timestamp", "dvol"]), raw_pages


def fetch_index(client: DeribitPublicClient) -> tuple[pd.DataFrame, Any]:
    result = client.call("public/get_index_chart_data", {"index_name": "btc_usd", "range": "all"})
    frame = pd.DataFrame(result, columns=["timestamp", "index_price"])
    if not frame.empty:
        frame["timestamp"] = pd.to_datetime(frame["timestamp"], unit="ms", utc=True)
        frame = frame.drop_duplicates("timestamp", keep="last").sort_values("timestamp")
    return frame, result


def fetch_historical_volatility(client: DeribitPublicClient) -> tuple[pd.DataFrame, Any]:
    result = client.call("public/get_historical_volatility", {"currency": "BTC"})
    frame = pd.DataFrame(result, columns=["timestamp", "historical_volatility"])
    if not frame.empty:
        frame["timestamp"] = pd.to_datetime(frame["timestamp"], unit="ms", utc=True)
        frame = frame.drop_duplicates("timestamp", keep="last").sort_values("timestamp")
    return frame, result


def current_atm_snapshot(client: DeribitPublicClient) -> dict[str, Any]:
    instruments = client.call("public/get_instruments", {"currency": "BTC", "kind": "option", "expired": False})
    index_points = client.call("public/get_index_chart_data", {"index_name": "btc_usd", "range": "1h"})
    spot = float(index_points[-1][1]) if index_points else float("nan")
    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    candidates = []
    for inst in instruments:
        dte = (int(inst["expiration_timestamp"]) - now_ms) / 86400000.0
        if 21 <= dte <= 45:
            candidates.append((abs(float(inst.get("strike", 0)) - spot), inst))
    candidates.sort(key=lambda item: item[0])
    selected = []
    expiry = None
    strike = None
    for _, inst in candidates:
        if expiry is None:
            expiry = inst["expiration_timestamp"]
            strike = inst.get("strike")
        if inst["expiration_timestamp"] == expiry and inst.get("strike") == strike:
            selected.append(inst)
    summaries = {}
    for inst in selected:
        summaries[inst["instrument_name"]] = client.call("public/get_book_summary_by_instrument", {"instrument_name": inst["instrument_name"]})
    return {"retrieved_at": utc_now_iso(), "spot": spot, "selected_instruments": selected, "book_summaries": summaries}


def fetch_all_free_data(output_dir: Path, years: int = 6) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    raw_dir = output_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    client = DeribitPublicClient()
    end_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    start_ms = int(pd.Timestamp.now(tz="UTC").timestamp() * 1000 - years * 365.25 * 86400000)
    dvol, dvol_raw = fetch_dvol(client, start_ms, end_ms)
    index, index_raw = fetch_index(client)
    hv, hv_raw = fetch_historical_volatility(client)
    snapshot = current_atm_snapshot(client)

    dvol_path = output_dir / "btc_dvol.csv.gz"
    index_path = output_dir / "btc_index.csv.gz"
    hv_path = output_dir / "btc_historical_volatility.csv.gz"
    dvol.to_csv(dvol_path, index=False, compression={"method": "gzip", "mtime": 0})
    index.to_csv(index_path, index=False, compression={"method": "gzip", "mtime": 0})
    hv.to_csv(hv_path, index=False, compression={"method": "gzip", "mtime": 0})
    write_json(raw_dir / "dvol_pages.json", dvol_raw)
    write_json(raw_dir / "index_chart.json", index_raw)
    write_json(raw_dir / "historical_volatility.json", hv_raw)
    write_json(output_dir / "current_atm_snapshot.json", snapshot)

    provenance = {
        "retrieved_at": utc_now_iso(),
        "license_and_access": "Deribit public unauthenticated JSON-RPC API",
        "paid_sources_used": False,
        "api_key_required": False,
        "sources": {
            "dvol": {"endpoint": "public/get_volatility_index_data", "url": DERIBIT_HTTP, "file": dvol_path.name, "sha256": sha256_file(dvol_path), "rows": len(dvol)},
            "index": {"endpoint": "public/get_index_chart_data", "url": DERIBIT_HTTP, "file": index_path.name, "sha256": sha256_file(index_path), "rows": len(index)},
            "historical_volatility": {"endpoint": "public/get_historical_volatility", "url": DERIBIT_HTTP, "file": hv_path.name, "sha256": sha256_file(hv_path), "rows": len(hv)},
            "current_atm_snapshot": {"endpoints": ["public/get_instruments", "public/get_book_summary_by_instrument"], "file": "current_atm_snapshot.json", "sha256": sha256_file(output_dir / "current_atm_snapshot.json")},
        },
        "limitations": [
            "No historical option bid/ask chain is available from the selected public endpoints.",
            "Historical model results are synthetic feasibility diagnostics, not executable option backtests.",
            "Public currency-wide trade history is limited to recent records; no paid archive is used.",
        ],
    }
    write_json(output_dir / "FREE_DATA_PROVENANCE.json", provenance)
    return provenance


async def record_public_chain(output_dir: Path, minutes: int = 60, snapshot_seconds: int = 30) -> None:
    try:
        import websockets
    except ImportError as exc:
        raise RuntimeError("Install websockets to use the forward recorder") from exc
    output_dir.mkdir(parents=True, exist_ok=True)
    jsonl_path = output_dir / "deribit_public_chain.jsonl"
    client = DeribitPublicClient()
    instruments = client.call("public/get_instruments", {"currency": "BTC", "kind": "option", "expired": False})
    index_points = client.call("public/get_index_chart_data", {"index_name": "btc_usd", "range": "1h"})
    spot = float(index_points[-1][1]) if index_points else 0.0
    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    selected = []
    for inst in instruments:
        dte = (int(inst["expiration_timestamp"]) - now_ms) / 86400000.0
        strike = float(inst.get("strike", 0))
        if 21 <= dte <= 45 and spot > 0 and abs(strike / spot - 1.0) <= 0.20:
            selected.append(inst["instrument_name"])
    channels = [f"ticker.{name}.agg2" for name in selected]
    channels += ["ticker.BTC-PERPETUAL.agg2", "deribit_volatility_index.btc_usd"]
    started = time.time()
    async with websockets.connect(DERIBIT_WS, ping_interval=20, ping_timeout=20, max_size=16 * 1024 * 1024) as ws:
        await ws.send(json.dumps({"jsonrpc": "2.0", "id": 1, "method": "public/subscribe", "params": {"channels": channels}}))
        with jsonl_path.open("a", encoding="utf-8") as out:
            while time.time() - started < minutes * 60:
                try:
                    message = await asyncio.wait_for(ws.recv(), timeout=max(snapshot_seconds * 2, 10))
                except asyncio.TimeoutError:
                    await ws.send(json.dumps({"jsonrpc": "2.0", "id": 2, "method": "public/test", "params": {}}))
                    continue
                payload = json.loads(message)
                payload["recorded_at"] = utc_now_iso()
                out.write(json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n")
                out.flush()
    provenance = {"source": DERIBIT_WS, "retrieved_at": utc_now_iso(), "minutes": minutes, "instrument_count": len(selected), "file": jsonl_path.name, "sha256": sha256_file(jsonl_path), "paid_sources_used": False}
    write_json(output_dir / "FORWARD_RECORDER_PROVENANCE.json", provenance)

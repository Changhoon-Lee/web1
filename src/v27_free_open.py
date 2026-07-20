#!/usr/bin/env python3
"""V27 free/open-data-only Deribit recorder and fail-closed runner.

Only public Deribit JSON-RPC endpoints are used. No paid API, private key,
historical quote interpolation, mark-as-fill substitution, or synthetic backfill
is permitted. Recorded rows are normalized to the authoritative V27 compact
schema so the unchanged long-gamma accounting engine can evaluate them once
continuity gates are genuinely satisfied.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import math
import os
import shutil
import sys
import time
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import pandas as pd

from v27_core import Config, deterministic_zip, output_manifest, sha256_file, write_json
from v27_cli import build_handoff, coverage_summary, run_lab, verify_results

VERSION = "27.1.0-free-open"
DERIBIT_RPC = "https://www.deribit.com/api/v2"
COLUMNS = [
    "timestamp", "symbol", "type", "strike_price", "expiration",
    "bid_price", "ask_price", "bid_amount", "ask_amount", "mark_price",
    "mark_iv", "bid_iv", "ask_iv", "underlying_price", "underlying_index",
    "open_interest", "delta", "gamma", "vega", "theta",
]
FORBIDDEN_ENV_VARS = {"TARDIS_API_KEY", "DERIBIT_CLIENT_ID", "DERIBIT_CLIENT_SECRET"}


@dataclass(frozen=True)
class FreeConfig:
    currency: str = "BTC"
    target_dte: float = 30.0
    minimum_dte: float = 21.0
    maximum_dte: float = 45.0
    interval_seconds: int = 300
    record_minutes: int = 1
    minimum_active_days: int = 90
    minimum_active_day_ratio: float = 0.80
    maximum_gap_hours: float = 48.0
    request_timeout_seconds: int = 20

    def validate(self) -> None:
        if self.currency not in {"BTC", "ETH"}:
            raise ValueError("currency must be BTC or ETH")
        if not 0 < self.minimum_dte <= self.target_dte <= self.maximum_dte:
            raise ValueError("invalid DTE ordering")
        if self.interval_seconds < 30:
            raise ValueError("interval_seconds must be at least 30")
        if self.record_minutes < 0:
            raise ValueError("negative record duration")
        if self.minimum_active_days < 1:
            raise ValueError("minimum_active_days must be positive")
        if not 0 < self.minimum_active_day_ratio <= 1:
            raise ValueError("invalid coverage ratio")


def json_default(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if hasattr(value, "item"):
        return value.item()
    raise TypeError(type(value).__name__)


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def public_rpc(method: str, params: dict[str, Any] | None = None, timeout: int = 20) -> Any:
    if any(os.getenv(name) for name in FORBIDDEN_ENV_VARS):
        raise RuntimeError("free-only mode refuses paid/private API credentials")
    query = urllib.parse.urlencode(params or {})
    url = f"{DERIBIT_RPC}/public/{method}" + (f"?{query}" if query else "")
    req = urllib.request.Request(url, headers={"User-Agent": "V27-Free-Open-Research/27.1"})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        payload = json.loads(response.read().decode("utf-8"))
    if "error" in payload:
        raise RuntimeError(json.dumps(payload["error"], sort_keys=True))
    return payload.get("result")


def _utc_ms(value: int | float | str | pd.Timestamp) -> pd.Timestamp:
    if isinstance(value, pd.Timestamp):
        ts = value
    elif isinstance(value, (int, float)):
        ts = pd.to_datetime(value, unit="ms", utc=True)
    else:
        ts = pd.to_datetime(value, utc=True)
    return ts.tz_convert("UTC") if ts.tzinfo else ts.tz_localize("UTC")


def choose_pair(instruments: list[dict[str, Any]], index_price: float, now: pd.Timestamp, cfg: FreeConfig) -> tuple[dict[str, Any], dict[str, Any]]:
    rows = []
    for item in instruments:
        try:
            expiry = _utc_ms(item["expiration_timestamp"])
            dte = (expiry - now).total_seconds() / 86400.0
            strike = float(item["strike"])
            option_type = str(item["option_type"]).lower()
            if cfg.minimum_dte <= dte <= cfg.maximum_dte and option_type in {"call", "put"}:
                rows.append((abs(dte - cfg.target_dte), abs(strike / index_price - 1.0), expiry, strike, option_type, item))
        except (KeyError, TypeError, ValueError, ZeroDivisionError):
            continue
    if not rows:
        raise RuntimeError("no active options inside pre-registered DTE range")
    expiries = sorted({r[2] for r in rows}, key=lambda x: abs((x - now).total_seconds() / 86400.0 - cfg.target_dte))
    expiry = expiries[0]
    subset = [r for r in rows if r[2] == expiry]
    strikes = sorted({r[3] for r in subset}, key=lambda x: (abs(x / index_price - 1.0), x))
    for strike in strikes:
        call = next((r[5] for r in subset if r[3] == strike and r[4] == "call"), None)
        put = next((r[5] for r in subset if r[3] == strike and r[4] == "put"), None)
        if call is not None and put is not None:
            return call, put
    raise RuntimeError("no call/put pair at a common strike and expiry")


def ticker_to_row(instrument: dict[str, Any], ticker: dict[str, Any], now: pd.Timestamp, index_name: str) -> dict[str, Any]:
    greeks = ticker.get("greeks") or {}
    bid = ticker.get("best_bid_price")
    ask = ticker.get("best_ask_price")
    if bid is None or ask is None or float(ask) <= 0 or float(bid) < 0 or float(ask) < float(bid):
        raise RuntimeError(f"non-executable quote for {instrument.get('instrument_name')}")
    underlying = ticker.get("underlying_price") or ticker.get("index_price")
    if underlying is None or float(underlying) <= 0:
        raise RuntimeError("missing positive underlying price")
    return {
        "timestamp": now.isoformat(),
        "symbol": instrument["instrument_name"],
        "type": str(instrument["option_type"]).lower(),
        "strike_price": float(instrument["strike"]),
        "expiration": _utc_ms(instrument["expiration_timestamp"]).isoformat(),
        "bid_price": float(bid),
        "ask_price": float(ask),
        "bid_amount": ticker.get("best_bid_amount"),
        "ask_amount": ticker.get("best_ask_amount"),
        "mark_price": ticker.get("mark_price"),
        "mark_iv": ticker.get("mark_iv"),
        "bid_iv": ticker.get("bid_iv"),
        "ask_iv": ticker.get("ask_iv"),
        "underlying_price": float(underlying),
        "underlying_index": index_name,
        "open_interest": ticker.get("open_interest"),
        "delta": greeks.get("delta"),
        "gamma": greeks.get("gamma"),
        "vega": greeks.get("vega"),
        "theta": greeks.get("theta"),
    }


def fetch_snapshot(cfg: FreeConfig, rpc: Callable[..., Any] = public_rpc, now: pd.Timestamp | None = None) -> pd.DataFrame:
    cfg.validate()
    now = now or pd.Timestamp.now(tz="UTC").floor("s")
    index_name = f"{cfg.currency.lower()}_usd"
    index_result = rpc("get_index_price", {"index_name": index_name}, cfg.request_timeout_seconds)
    index_price = float(index_result["index_price"])
    instruments = rpc("get_instruments", {"currency": cfg.currency, "kind": "option", "expired": "false"}, cfg.request_timeout_seconds)
    call, put = choose_pair(instruments, index_price, now, cfg)
    rows = []
    for instrument in (call, put):
        ticker = rpc("ticker", {"instrument_name": instrument["instrument_name"]}, cfg.request_timeout_seconds)
        row = ticker_to_row(instrument, ticker, now, index_name)
        # Keep the official index as a conservative fallback only when the ticker omits its underlying.
        if not math.isfinite(float(row["underlying_price"])):
            row["underlying_price"] = index_price
        rows.append(row)
    frame = pd.DataFrame(rows, columns=COLUMNS)
    if len(frame) != 2 or set(frame["type"]) != {"call", "put"}:
        raise RuntimeError("snapshot is not one executable call/put pair")
    return frame


def deterministic_gzip_csv(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    csv = frame.to_csv(index=False, lineterminator="\n", float_format="%.12g").encode("utf-8")
    with path.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as gz:
            gz.write(csv)


def append_snapshot(frame: pd.DataFrame, root: Path) -> Path:
    timestamp = pd.to_datetime(frame["timestamp"].iloc[0], utc=True)
    path = root / f"{timestamp:%Y-%m-%d}.free.compact.csv.gz"
    if path.exists():
        existing = pd.read_csv(path, compression="gzip")
        combined = pd.concat([existing, frame], ignore_index=True)
    else:
        combined = frame.copy()
    combined["timestamp"] = pd.to_datetime(combined["timestamp"], utc=True)
    combined = combined.sort_values(["timestamp", "symbol"]).drop_duplicates(["timestamp", "symbol"], keep="last")
    combined["timestamp"] = combined["timestamp"].map(lambda x: x.isoformat())
    deterministic_gzip_csv(combined[COLUMNS], path)
    return path


def discover_free_files(root: Path) -> list[Path]:
    return sorted(root.rglob("*.free.compact.csv.gz"))


def load_free_data(root: Path) -> pd.DataFrame:
    files = discover_free_files(root)
    if not files:
        return pd.DataFrame(columns=COLUMNS)
    frames = [pd.read_csv(path, compression="gzip") for path in files]
    data = pd.concat(frames, ignore_index=True)
    data["timestamp"] = pd.to_datetime(data["timestamp"], utc=True, errors="coerce")
    data = data.dropna(subset=["timestamp"]).sort_values(["timestamp", "symbol"]).drop_duplicates(["timestamp", "symbol"], keep="last")
    return data.reset_index(drop=True)


def free_coverage(data: pd.DataFrame, cfg: FreeConfig) -> dict[str, Any]:
    timestamps = pd.DatetimeIndex(sorted(data.get("timestamp", pd.Series(dtype="datetime64[ns, UTC]")).dropna().unique()))
    if len(timestamps) < 2:
        return {
            "snapshot_count": int(len(timestamps)), "active_days": 0, "span_days": 0.0,
            "active_day_ratio": 0.0, "maximum_gap_hours": None,
            "required_active_days": cfg.minimum_active_days,
            "required_active_day_ratio": cfg.minimum_active_day_ratio,
            "maximum_allowed_gap_hours": cfg.maximum_gap_hours,
            "ready": False,
        }
    active_days = len(set(timestamps.date))
    span_days = (timestamps[-1] - timestamps[0]).total_seconds() / 86400.0 + 1.0
    gaps = pd.Series(timestamps).diff().dt.total_seconds().dropna() / 3600.0
    maximum_gap = float(gaps.max()) if len(gaps) else math.inf
    ratio = active_days / max(span_days, 1.0)
    ready = active_days >= cfg.minimum_active_days and ratio >= cfg.minimum_active_day_ratio and maximum_gap <= cfg.maximum_gap_hours
    return {
        "snapshot_count": int(len(timestamps)), "active_days": int(active_days), "span_days": float(span_days),
        "active_day_ratio": float(ratio), "maximum_gap_hours": maximum_gap,
        "required_active_days": cfg.minimum_active_days,
        "required_active_day_ratio": cfg.minimum_active_day_ratio,
        "maximum_allowed_gap_hours": cfg.maximum_gap_hours,
        "ready": bool(ready),
    }


def input_manifest(root: Path) -> dict[str, Any]:
    files = discover_free_files(root)
    rows = [{"path": str(path.relative_to(root)), "size": path.stat().st_size, "sha256": sha256_file(path)} for path in files]
    payload = json.dumps(rows, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return {
        "version": VERSION,
        "source": "Deribit public JSON-RPC API",
        "endpoint": DERIBIT_RPC,
        "authentication": "none",
        "historical_backfill": "forbidden",
        "files": rows,
        "tree_sha256": sha256_bytes(payload),
    }


def record(root: Path, cfg: FreeConfig, rpc: Callable[..., Any] = public_rpc, sleep: Callable[[float], None] = time.sleep) -> dict[str, Any]:
    cfg.validate()
    root.mkdir(parents=True, exist_ok=True)
    end = time.monotonic() + cfg.record_minutes * 60
    captured = 0
    errors: list[str] = []
    first = True
    while first or time.monotonic() < end:
        first = False
        started = time.monotonic()
        try:
            frame = fetch_snapshot(cfg, rpc=rpc)
            append_snapshot(frame, root)
            captured += 1
        except Exception as exc:  # network failures are logged, never silently filled.
            errors.append(f"{datetime.now(timezone.utc).isoformat()} {type(exc).__name__}: {exc}")
        if cfg.record_minutes <= 0:
            break
        remaining = cfg.interval_seconds - (time.monotonic() - started)
        if remaining > 0 and time.monotonic() < end:
            sleep(min(remaining, max(end - time.monotonic(), 0)))
    (root / "RECORDER_ERRORS.log").write_text("\n".join(errors) + ("\n" if errors else ""), encoding="utf-8")
    manifest = input_manifest(root)
    write_json(root / "FREE_INPUT_MANIFEST.json", manifest)
    data = load_free_data(root)
    coverage = free_coverage(data, cfg)
    write_json(root / "FREE_COVERAGE.json", coverage)
    return {"captured_snapshots": captured, "errors": len(errors), "coverage": coverage, "manifest": manifest}


def fail_closed_results(root: Path, data_root: Path, cfg: FreeConfig, coverage: dict[str, Any], output: Path) -> dict[str, Any]:
    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True)
    status = "FREE_OPEN_DATA_CONTINUITY_NOT_READY"
    gate = {
        "version": VERSION,
        "primary_status": status,
        "overall_status": status,
        "free_open_data_only": True,
        "paid_credentials_allowed": False,
        "economic_metrics_allowed": False,
        "coverage": coverage,
        "tests": {
            "official_public_source_only": True,
            "no_paid_credentials": True,
            "no_historical_interpolation": True,
            "sufficient_contiguous_history": False,
        },
    }
    write_json(output / "CONFIG.json", asdict(cfg))
    write_json(output / "DATA_COVERAGE.json", coverage)
    write_json(output / "FINAL_GATE.json", gate)
    write_json(output / "INPUT_MANIFEST.json", input_manifest(data_root))
    report = "\n".join([
        "# V27 Free/Open Data Only — Fail-Closed Report", "",
        f"- Status: `{status}`",
        f"- Active days: `{coverage['active_days']}` / required `{cfg.minimum_active_days}`",
        f"- Active-day ratio: `{coverage['active_day_ratio']:.6f}` / required `{cfg.minimum_active_day_ratio:.2f}`",
        f"- Maximum gap hours: `{coverage['maximum_gap_hours']}` / allowed `{cfg.maximum_gap_hours}`",
        "", "No Sharpe, CAGR, or economic conclusion is produced from discontinuous free data.",
        "Only official Deribit public snapshots are accepted. Historical quotes are never interpolated.",
    ])
    (output / "FINAL_REPORT.md").write_text(report + "\n", encoding="utf-8")
    manifest = output_manifest(output, exclude={"OUTPUT_MANIFEST.json"})
    write_json(output / "OUTPUT_MANIFEST.json", manifest)
    return gate


def run_free_only(project_root: Path, cfg: FreeConfig, data_root: Path, output: Path, handoff: Path, do_record: bool = True) -> dict[str, Any]:
    if do_record:
        record(data_root, cfg)
    data = load_free_data(data_root)
    coverage = free_coverage(data, cfg)
    if coverage["ready"]:
        v27_cfg = Config(currency=cfg.currency, snapshot_minutes=max(1, cfg.interval_seconds // 60))
        gate = run_lab(data_root, output, v27_cfg, prepared=True)
        gate["free_open_data_only"] = True
        gate["source"] = "Deribit public JSON-RPC snapshots recorded prospectively"
        write_json(output / "FINAL_GATE.json", gate)
        manifest = output_manifest(output, exclude={"OUTPUT_MANIFEST.json"})
        write_json(output / "OUTPUT_MANIFEST.json", manifest)
        verification = verify_results(output)
    else:
        gate = fail_closed_results(project_root, data_root, cfg, coverage, output)
        verification = {"passed": True, "fail_closed": True, "status": gate["overall_status"]}
    handoff.parent.mkdir(parents=True, exist_ok=True)
    deterministic_zip(project_root, handoff, include_results=True)
    return {"gate": gate, "verification": verification, "handoff": {"path": handoff, "size": handoff.stat().st_size, "sha256": sha256_file(handoff)}}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="V27 official-free-open-data-only runner")
    sub = parser.add_subparsers(dest="command", required=True)
    record_p = sub.add_parser("record")
    record_p.add_argument("--data", type=Path, default=Path("data/v27_free_chain"))
    audit_p = sub.add_parser("audit")
    audit_p.add_argument("--data", type=Path, default=Path("data/v27_free_chain"))
    run_p = sub.add_parser("all")
    run_p.add_argument("--data", type=Path, default=Path("data/v27_free_chain"))
    run_p.add_argument("--output", type=Path, default=Path("v27_free_results"))
    run_p.add_argument("--handoff", type=Path, default=Path("runtime/V27_Free_Open_Data_Only_Handoff.zip"))
    run_p.add_argument("--record", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--currency", default=os.getenv("V27_FREE_CURRENCY", "BTC"))
    parser.add_argument("--interval-seconds", type=int, default=int(os.getenv("V27_FREE_INTERVAL_SECONDS", "300")))
    parser.add_argument("--record-minutes", type=int, default=int(os.getenv("V27_FREE_RECORD_MINUTES", "1")))
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    project = Path(__file__).resolve().parents[1]
    cfg = FreeConfig(currency=args.currency, interval_seconds=args.interval_seconds, record_minutes=args.record_minutes)
    data_root = args.data if args.data.is_absolute() else project / args.data
    if args.command == "record":
        print(json.dumps(record(data_root, cfg), default=json_default, indent=2))
        return 0
    data = load_free_data(data_root)
    coverage = free_coverage(data, cfg)
    if args.command == "audit":
        print(json.dumps({"coverage": coverage, "manifest": input_manifest(data_root)}, default=json_default, indent=2))
        return 0
    output = args.output if args.output.is_absolute() else project / args.output
    handoff = args.handoff if args.handoff.is_absolute() else project / args.handoff
    print(json.dumps(run_free_only(project, cfg, data_root, output, handoff, args.record), default=json_default, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

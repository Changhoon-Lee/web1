#!/usr/bin/env python3
"""V27.2.4 WebSocket authority recorder, audit, and verifier."""
from __future__ import annotations

import argparse
import asyncio
import json
import shutil
from dataclasses import asdict
from pathlib import Path
from typing import Any

import pandas as pd

from v272_core import (
    VERSION, Config, audit_suite, deterministic_zip, discover_market_files,
    json_default, load_market_data, output_manifest, sha256_file, verify_ledger,
    write_json,
)
from v2724_ws import (
    WSConfig, coverage, input_manifest, load_data, record_forever,
    snapshot_authority,
)


def save_result(output: Path, key: str, result: Any) -> None:
    result.ledger.to_csv(output / f"{key}_exact_ledger.csv.gz", index=False, compression={"method": "gzip", "mtime": 0}, float_format="%.12g")
    result.trades.to_csv(output / f"{key}_trades.csv.gz", index=False, compression={"method": "gzip", "mtime": 0}, float_format="%.12g")
    result.diagnostics.to_csv(output / f"{key}_diagnostics.csv", index=False, float_format="%.12g")
    write_json(output / f"{key}_metrics.json", {"name": result.name, "status": result.status, **result.metrics})


def _cell(value: Any) -> str:
    if isinstance(value, (list, tuple, dict, set)):
        payload = sorted(value) if isinstance(value, set) else value
        return json.dumps(payload, default=json_default, ensure_ascii=False, sort_keys=isinstance(payload, dict))
    missing = pd.isna(value)
    if isinstance(missing, bool) and missing:
        return ""
    if isinstance(value, float):
        return f"{value:.8g}"
    return str(value)


def markdown(frame: pd.DataFrame) -> str:
    if frame.empty:
        return "_No rows._"
    values = [[str(column) for column in frame.columns]]
    values.extend([[_cell(value) for value in row] for row in frame.itertuples(index=False, name=None)])
    widths = [max(len(row[index]) for row in values) for index in range(len(values[0]))]
    render = lambda row: "| " + " | ".join(row[index].ljust(widths[index]) for index in range(len(row))) + " |"
    return "\n".join([render(values[0]), "| " + " | ".join("-" * width for width in widths) + " |", *[render(row) for row in values[1:]]])


def fail_closed(output: Path, data_root: Path, cfg: WSConfig, data_coverage: dict[str, Any]) -> dict[str, Any]:
    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True)
    status = "FREE_OPEN_DATA_CONTINUITY_NOT_READY"
    gate = {
        "version": VERSION,
        "primary_status": status,
        "overall_status": status,
        "free_open_data_only": True,
        "economic_metrics_allowed": False,
        "transport": "public_websocket_agg2",
        "coverage": data_coverage,
        "tests": {
            "official_public_source_only": True,
            "no_paid_credentials": True,
            "no_historical_interpolation": True,
            "no_rest_ticker_polling": True,
            "sufficient_contiguous_history": False,
        },
    }
    write_json(output / "WS_CONFIG.json", asdict(cfg))
    write_json(output / "DATA_COVERAGE.json", data_coverage)
    write_json(output / "FINAL_GATE.json", gate)
    write_json(output / "INPUT_MANIFEST.json", input_manifest(data_root))
    (output / "FINAL_REPORT.md").write_text(
        "# V27.2.4 WebSocket Authority — Fail-Closed Report\n\n"
        f"Status: `{status}`\n\n"
        "No Sharpe, CAGR, or economic conclusion is emitted until the 90-day, "
        "intraday, WebSocket authority, quote, delta, perpetual, and funding gates pass.\n",
        encoding="utf-8",
    )
    write_json(output / "OUTPUT_MANIFEST.json", output_manifest(output, exclude={"OUTPUT_MANIFEST.json"}))
    return gate


def run_economic(data_root: Path, output: Path, core_cfg: Config, ws_cfg: WSConfig, data_coverage: dict[str, Any], held_state: Path) -> dict[str, Any]:
    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True)
    data = load_market_data(discover_market_files(data_root), core_cfg)
    variants, gate = audit_suite(data, core_cfg, held_state)
    gate.update({
        "free_open_data_only": True,
        "economic_metrics_allowed": True,
        "transport": "public_websocket_agg2",
        "coverage": data_coverage,
        "source": "Deribit public ticker.<instrument>.agg2 prospectively recorded snapshots",
    })
    rows: list[dict[str, Any]] = []
    for key, result in variants.items():
        save_result(output, key, result)
        rows.append({"variant": key, "status": result.status, **result.metrics})
    summary = pd.DataFrame(rows)
    summary.to_csv(output / "strategy_summary.csv", index=False, float_format="%.12g")
    write_json(output / "CORE_CONFIG.json", asdict(core_cfg))
    write_json(output / "WS_CONFIG.json", asdict(ws_cfg))
    write_json(output / "DATA_COVERAGE.json", data_coverage)
    write_json(output / "FINAL_GATE.json", gate)
    write_json(output / "INPUT_MANIFEST.json", input_manifest(data_root))
    report = [
        "# V27.2.4 Actual Inverse Long-Gamma WebSocket Report", "",
        f"Protocol: `{VERSION}`", "",
        "## Coverage", "", "```json", json.dumps(data_coverage, default=json_default, indent=2), "```", "",
        "## Variants", "", markdown(summary), "",
        "## Final state", "", "```text",
        f"PRIMARY: {gate['primary_status']}", f"OVERALL: {gate['overall_status']}", "```", "",
        "The authority input is a same-cutoff public agg2 WebSocket state with actual option Greeks, option bid/ask, BTC-PERPETUAL bid/ask, inverse-contract P&L, and actual funding_8h.", "",
    ]
    (output / "FINAL_REPORT.md").write_text("\n".join(report), encoding="utf-8")
    write_json(output / "OUTPUT_MANIFEST.json", output_manifest(output, exclude={"OUTPUT_MANIFEST.json"}))
    return gate


def verify(output: Path) -> dict[str, Any]:
    failures: list[str] = []
    gate_path = output / "FINAL_GATE.json"
    manifest_path = output / "OUTPUT_MANIFEST.json"
    gate = json.loads(gate_path.read_text(encoding="utf-8")) if gate_path.exists() else {}
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {"files": []}
    if not gate_path.exists():
        failures.append("missing_final_gate")
    if not manifest_path.exists():
        failures.append("missing_output_manifest")
    for item in manifest.get("files", []):
        path = output / item["path"]
        if not path.exists():
            failures.append(f"missing:{item['path']}")
        elif path.stat().st_size != item["size"]:
            failures.append(f"size:{item['path']}")
        elif sha256_file(path) != item["sha256"]:
            failures.append(f"sha256:{item['path']}")
    status = gate.get("overall_status")
    allowed = {
        "FREE_OPEN_DATA_CONTINUITY_NOT_READY",
        "INSUFFICIENT_CONTIGUOUS_OPTIONS_DATA",
        "MARKET_DATA_CONTINUITY_GATE_FAILED",
        "HISTORICAL_DERIBIT_LONG_GAMMA_REJECTED",
        "HISTORICAL_DERIBIT_LONG_GAMMA_PASS_NEEDS_NEW_OOS",
    }
    if status not in allowed:
        failures.append(f"invalid_status:{status}")
    if gate.get("free_open_data_only") is not True:
        failures.append("free_open_data_only_not_asserted")
    if gate.get("transport") != "public_websocket_agg2":
        failures.append("websocket_transport_not_asserted")
    if status == "FREE_OPEN_DATA_CONTINUITY_NOT_READY":
        if gate.get("economic_metrics_allowed") is not False:
            failures.append("economic_metrics_not_blocked")
        if list(output.glob("*_exact_ledger.csv.gz")):
            failures.append("ledger_present_before_gate")
    else:
        ledgers = sorted(output.glob("*_exact_ledger.csv.gz"))
        if not ledgers:
            failures.append("no_economic_ledgers")
        for path in ledgers:
            failures.extend(f"{path.name}:{failure}" for failure in verify_ledger(pd.read_csv(path, compression="gzip")))
    result = {"passed": not failures, "status": status, "failures": failures, "tree_sha256": manifest.get("tree_sha256")}
    if failures:
        raise RuntimeError(json.dumps(result, indent=2))
    return result


def audit_once(project: Path, data_root: Path, output: Path, handoff: Path, cfg: WSConfig) -> dict[str, Any]:
    data_coverage = coverage(load_data(data_root), cfg)
    held_state = data_root / "HELD_OPTION_STATE.json"
    if data_coverage.get("ready"):
        gate = run_economic(data_root, output, Config(snapshot_minutes=cfg.snapshot_interval_seconds // 60), cfg, data_coverage, held_state)
    else:
        gate = fail_closed(output, data_root, cfg, data_coverage)
    verification = verify(output)
    deterministic_zip(project, handoff)
    return {
        "gate": gate,
        "verification": verification,
        "handoff": {"path": str(handoff), "size": handoff.stat().st_size, "sha256": sha256_file(handoff)},
    }


def _atomic_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(value + "\n", encoding="utf-8")
    tmp.replace(path)


def maybe_daily_audit(project: Path, data_root: Path, output: Path, handoff: Path, cfg: WSConfig) -> dict[str, Any]:
    state_root = project / "runtime/state"
    date_path = state_root / "LAST_AUDIT_DATE_UTC.txt"
    hash_path = state_root / "LAST_AUDITED_INPUT_HASH.txt"
    today = pd.Timestamp.now(tz="UTC").date().isoformat()
    manifest = input_manifest(data_root)
    current_hash = str(manifest["tree_sha256"])
    last_date = date_path.read_text(encoding="utf-8").strip() if date_path.exists() else ""
    last_hash = hash_path.read_text(encoding="utf-8").strip() if hash_path.exists() else ""
    data_coverage = coverage(load_data(data_root), cfg)
    if not data_coverage.get("ready"):
        gate = fail_closed(output, data_root, cfg, data_coverage)
        verify(output)
        return {"ran_economic": False, "reason": "not_ready", "gate": gate}
    if today == last_date or current_hash == last_hash:
        return {"ran_economic": False, "reason": "daily_or_hash_duplicate", "date": today, "tree_sha256": current_hash}
    result = audit_once(project, data_root, output, handoff, cfg)
    _atomic_text(hash_path, current_hash)
    _atomic_text(date_path, today)
    return {"ran_economic": True, **result}


async def run_recorder(project: Path, data_root: Path, output: Path, handoff: Path, cfg: WSConfig) -> None:
    async def after_snapshot(_path: Path, frame: pd.DataFrame, authority: dict[str, Any]) -> None:
        write_json(project / "runtime/LATEST_SNAPSHOT_AUTHORITY.json", authority)
        maybe_daily_audit(project, data_root, output, handoff, cfg)

    await record_forever(data_root, cfg, after_snapshot)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="V27.2.4 public WebSocket authority runtime")
    sub = parser.add_subparsers(dest="command", required=True)
    record = sub.add_parser("record")
    record.add_argument("--data", type=Path, default=Path("data/v2724_ws_chain"))
    record.add_argument("--output", type=Path, default=Path("v2724_results"))
    record.add_argument("--handoff", type=Path, default=Path("runtime/V2724_WebSocket_Authority_Handoff.zip"))
    audit = sub.add_parser("audit")
    audit.add_argument("--data", type=Path, default=Path("data/v2724_ws_chain"))
    all_parser = sub.add_parser("all")
    all_parser.add_argument("--data", type=Path, default=Path("data/v2724_ws_chain"))
    all_parser.add_argument("--output", type=Path, default=Path("v2724_results"))
    all_parser.add_argument("--handoff", type=Path, default=Path("runtime/V2724_WebSocket_Authority_Handoff.zip"))
    verify_parser = sub.add_parser("verify")
    verify_parser.add_argument("--output", type=Path, default=Path("v2724_results"))
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    project = Path(__file__).resolve().parents[1]
    if args.command == "verify":
        output = args.output if args.output.is_absolute() else project / args.output
        print(json.dumps(verify(output), indent=2))
        return 0
    data_root = args.data if args.data.is_absolute() else project / args.data
    cfg = WSConfig()
    if args.command == "audit":
        print(json.dumps({"coverage": coverage(load_data(data_root), cfg), "manifest": input_manifest(data_root)}, default=json_default, indent=2))
        return 0
    output = args.output if args.output.is_absolute() else project / args.output
    handoff = args.handoff if args.handoff.is_absolute() else project / args.handoff
    if args.command == "all":
        print(json.dumps(audit_once(project, data_root, output, handoff, cfg), default=json_default, indent=2))
        return 0
    asyncio.run(run_recorder(project, data_root, output, handoff, cfg))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

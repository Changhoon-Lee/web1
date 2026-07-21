#!/usr/bin/env python3
"""V27.2 one-command official-free recorder, audit, and verifier."""
from __future__ import annotations

import argparse
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
from v272_free import FreeConfig, free_coverage, input_manifest, load_free_data, record


def save_result(output: Path, key: str, result: Any) -> None:
    result.ledger.to_csv(output / f"{key}_exact_ledger.csv.gz", index=False, compression={"method": "gzip", "mtime": 0}, float_format="%.12g")
    result.trades.to_csv(output / f"{key}_trades.csv.gz", index=False, compression={"method": "gzip", "mtime": 0}, float_format="%.12g")
    result.diagnostics.to_csv(output / f"{key}_diagnostics.csv", index=False, float_format="%.12g")
    write_json(output / f"{key}_metrics.json", {"name": result.name, "status": result.status, **result.metrics})


def _markdown_cell(value: Any) -> str:
    """Render scalar and structured metrics without ambiguous pd.isna arrays."""
    if isinstance(value, (list, tuple, dict, set)):
        payload = sorted(value) if isinstance(value, set) else value
        return json.dumps(payload, default=json_default, ensure_ascii=False, sort_keys=isinstance(payload, dict))
    missing = pd.isna(value)
    if isinstance(missing, bool) and missing:
        return ""
    if isinstance(value, float):
        return f"{value:.8g}"
    return str(value)


def manual_markdown(frame: pd.DataFrame) -> str:
    if frame.empty:
        return "_No rows._"
    values = [[str(c) for c in frame.columns]]
    for row in frame.itertuples(index=False, name=None):
        values.append([_markdown_cell(value) for value in row])
    widths = [max(len(row[i]) for row in values) for i in range(len(values[0]))]
    fmt = lambda row: "| " + " | ".join(row[i].ljust(widths[i]) for i in range(len(row))) + " |"
    return "\n".join([fmt(values[0]), "| " + " | ".join("-" * w for w in widths) + " |", *[fmt(row) for row in values[1:]]])


def fail_closed(output: Path, data_root: Path, free_cfg: FreeConfig, coverage: dict[str, Any]) -> dict[str, Any]:
    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True)
    status = "FREE_OPEN_DATA_CONTINUITY_NOT_READY"
    gate = {
        "version": VERSION, "primary_status": status, "overall_status": status,
        "free_open_data_only": True, "economic_metrics_allowed": False,
        "coverage": coverage,
        "tests": {
            "official_public_source_only": True, "no_paid_credentials": True,
            "no_historical_interpolation": True, "sufficient_contiguous_history": False,
        },
    }
    write_json(output / "FREE_CONFIG.json", asdict(free_cfg))
    write_json(output / "DATA_COVERAGE.json", coverage)
    write_json(output / "FINAL_GATE.json", gate)
    write_json(output / "INPUT_MANIFEST.json", input_manifest(data_root))
    (output / "FINAL_REPORT.md").write_text(
        "# V27.2 Free/Open — Fail-Closed Report\n\n"
        f"Status: `{status}`\n\n"
        "No Sharpe, CAGR, or economic conclusion is emitted until both the trailing/contiguous and intraday gates pass.\n",
        encoding="utf-8",
    )
    write_json(output / "OUTPUT_MANIFEST.json", output_manifest(output, exclude={"OUTPUT_MANIFEST.json"}))
    return gate


def run_economic(data_root: Path, output: Path, cfg: Config, free_cfg: FreeConfig, coverage: dict[str, Any], held_state: Path) -> dict[str, Any]:
    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True)
    data = load_market_data(discover_market_files(data_root), cfg)
    variants, gate = audit_suite(data, cfg, held_state)
    gate["free_open_data_only"] = True
    gate["economic_metrics_allowed"] = True
    gate["coverage"] = coverage
    gate["source"] = "Deribit public JSON-RPC prospectively recorded snapshots"
    rows = []
    for key, result in variants.items():
        save_result(output, key, result)
        rows.append({"variant": key, "status": result.status, **result.metrics})
    summary = pd.DataFrame(rows)
    summary.to_csv(output / "strategy_summary.csv", index=False, float_format="%.12g")
    write_json(output / "CORE_CONFIG.json", asdict(cfg))
    write_json(output / "FREE_CONFIG.json", asdict(free_cfg))
    write_json(output / "DATA_COVERAGE.json", coverage)
    write_json(output / "FINAL_GATE.json", gate)
    write_json(output / "INPUT_MANIFEST.json", input_manifest(data_root))
    report = [
        "# V27.2 Actual Inverse Long-Gamma Report", "",
        f"Protocol: `{VERSION}`", "",
        "## Coverage", "", "```json", json.dumps(coverage, default=json_default, indent=2), "```", "",
        "## Variants", "", manual_markdown(summary), "",
        "## Final state", "", "```text",
        f"PRIMARY: {gate['primary_status']}", f"OVERALL: {gate['overall_status']}", "```", "",
        "The hedge is BTC-PERPETUAL with actual bid/ask, inverse-contract P&L, actual public funding_8h, and executable held-option quote gates.", "",
    ]
    (output / "FINAL_REPORT.md").write_text("\n".join(report), encoding="utf-8")
    write_json(output / "OUTPUT_MANIFEST.json", output_manifest(output, exclude={"OUTPUT_MANIFEST.json"}))
    return gate


def verify(output: Path) -> dict[str, Any]:
    failures: list[str] = []
    gate_path, manifest_path = output / "FINAL_GATE.json", output / "OUTPUT_MANIFEST.json"
    if not gate_path.exists():
        failures.append("missing_final_gate")
        gate = {}
    else:
        gate = json.loads(gate_path.read_text(encoding="utf-8"))
    if not manifest_path.exists():
        failures.append("missing_output_manifest")
        manifest = {"files": []}
    else:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
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
        "FREE_OPEN_DATA_CONTINUITY_NOT_READY", "INSUFFICIENT_CONTIGUOUS_OPTIONS_DATA",
        "MARKET_DATA_CONTINUITY_GATE_FAILED", "HISTORICAL_DERIBIT_LONG_GAMMA_REJECTED",
        "HISTORICAL_DERIBIT_LONG_GAMMA_PASS_NEEDS_NEW_OOS",
    }
    if status not in allowed:
        failures.append(f"invalid_status:{status}")
    if gate.get("free_open_data_only") is not True:
        failures.append("free_open_data_only_not_asserted")
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
            failures.extend(f"{path.name}:{x}" for x in verify_ledger(pd.read_csv(path, compression="gzip")))
    result = {"passed": not failures, "status": status, "failures": failures, "tree_sha256": manifest.get("tree_sha256")}
    if failures:
        raise RuntimeError(json.dumps(result, indent=2))
    return result


def run_all(project: Path, data_root: Path, output: Path, handoff: Path, do_record: bool, free_cfg: FreeConfig) -> dict[str, Any]:
    held_state = data_root / "HELD_OPTION_STATE.json"
    if do_record:
        record(data_root, free_cfg, held_state)
    coverage = free_coverage(load_free_data(data_root), free_cfg)
    if coverage["ready"]:
        core_cfg = Config(snapshot_minutes=max(1, free_cfg.interval_seconds // 60))
        gate = run_economic(data_root, output, core_cfg, free_cfg, coverage, held_state)
    else:
        gate = fail_closed(output, data_root, free_cfg, coverage)
    verification = verify(output)
    deterministic_zip(project, handoff)
    return {"gate": gate, "verification": verification, "handoff": {"path": handoff, "size": handoff.stat().st_size, "sha256": sha256_file(handoff)}}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="V27.2 actual inverse free/open runtime")
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("record", "audit"):
        p = sub.add_parser(name)
        p.add_argument("--data", type=Path, default=Path("data/v272_free_chain"))
    p = sub.add_parser("all")
    p.add_argument("--data", type=Path, default=Path("data/v272_free_chain"))
    p.add_argument("--output", type=Path, default=Path("v272_results"))
    p.add_argument("--handoff", type=Path, default=Path("runtime/V272_Actual_Inverse_Handoff.zip"))
    p.add_argument("--record", action=argparse.BooleanOptionalAction, default=True)
    p = sub.add_parser("verify")
    p.add_argument("--output", type=Path, default=Path("v272_results"))
    parser.add_argument("--record-minutes", type=int, default=0)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    project = Path(__file__).resolve().parents[1]
    if args.command == "verify":
        output = args.output if args.output.is_absolute() else project / args.output
        print(json.dumps(verify(output), indent=2))
        return 0
    data_root = args.data if args.data.is_absolute() else project / args.data
    free_cfg = FreeConfig(record_minutes=args.record_minutes)
    held_state = data_root / "HELD_OPTION_STATE.json"
    if args.command == "record":
        print(json.dumps(record(data_root, free_cfg, held_state), default=json_default, indent=2))
        return 0
    if args.command == "audit":
        coverage = free_coverage(load_free_data(data_root), free_cfg)
        print(json.dumps({"coverage": coverage, "manifest": input_manifest(data_root)}, default=json_default, indent=2))
        return 0
    output = args.output if args.output.is_absolute() else project / args.output
    handoff = args.handoff if args.handoff.is_absolute() else project / args.handoff
    print(json.dumps(run_all(project, data_root, output, handoff, args.record, free_cfg), default=json_default, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

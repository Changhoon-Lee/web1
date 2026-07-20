#!/usr/bin/env python3
"""Sanitized V27 economic runner for official free/open data only.

This module intentionally contains no downloader, credential, Tardis, or private
exchange path. It consumes only already-recorded compact option-chain snapshots.
"""
from __future__ import annotations

import json
import math
import shutil
from dataclasses import asdict
from pathlib import Path
from typing import Any

import pandas as pd

from v27_core import (
    Config,
    VERSION,
    audit_suite,
    discover_chain_files,
    load_compact_data,
    output_manifest,
    sha256_file,
    verify_ledger,
    write_json,
)


def manual_markdown(frame: pd.DataFrame) -> str:
    if frame.empty:
        return "_No rows._"
    values = [[str(c) for c in frame.columns]]
    for row in frame.itertuples(index=False, name=None):
        values.append(["" if pd.isna(v) else f"{v:.8g}" if isinstance(v, float) else str(v) for v in row])
    widths = [max(len(row[i]) for row in values) for i in range(len(values[0]))]
    def fmt(row: list[str]) -> str:
        return "| " + " | ".join(row[i].ljust(widths[i]) for i in range(len(row))) + " |"
    return "\n".join([fmt(values[0]), "| " + " | ".join("-" * widths[i] for i in range(len(widths))) + " |", *[fmt(r) for r in values[1:]]])


def save_result(output: Path, key: str, result: Any) -> None:
    result.ledger.to_csv(output / f"{key}_exact_ledger.csv.gz", index=False, compression={"method": "gzip", "mtime": 0}, float_format="%.12g")
    result.trades.to_csv(output / f"{key}_trades.csv.gz", index=False, compression={"method": "gzip", "mtime": 0}, float_format="%.12g")
    result.diagnostics.to_csv(output / f"{key}_diagnostics.csv", index=False, float_format="%.12g")
    write_json(output / f"{key}_metrics.json", {"name": result.name, "status": result.status, **result.metrics})


def make_report(output: Path, gate: dict[str, Any], summary: pd.DataFrame, coverage: dict[str, Any]) -> None:
    lines = [
        "# V27 Free/Open Data Only — Economic Report", "",
        f"Core protocol version: `{VERSION}`", "",
        "## Data coverage", "",
        f"- Active days: `{coverage['active_days']}`",
        f"- Span days: `{coverage['span_days']:.3f}`",
        f"- Active-day ratio: `{coverage['active_day_ratio']:.6f}`",
        f"- Maximum timestamp gap: `{coverage['maximum_gap_hours']:.3f} hours`",
        f"- Contiguous pass: `{coverage['ready']}`", "",
        "## Variant metrics", "", manual_markdown(summary), "",
        "## Final gate", "", "```text",
        f"PRIMARY: {gate['primary_status']}",
        f"OVERALL: {gate['overall_status']}", "```", "",
        "Only prospectively recorded public Deribit bid/ask snapshots are used. No historical interpolation or paid-data path exists in this runtime.", "",
    ]
    (output / "FINAL_REPORT.md").write_text("\n".join(lines), encoding="utf-8")


def run_lab(input_path: Path, output: Path, cfg: Config, coverage: dict[str, Any]) -> dict[str, Any]:
    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True)
    files = discover_chain_files(input_path)
    if not files:
        raise FileNotFoundError(f"no compact free option-chain files under {input_path}")
    data = load_compact_data(files, cfg)
    variants, gate = audit_suite(data, cfg)
    gate["coverage"] = coverage
    gate["free_open_data_only"] = True
    gate["source"] = "Deribit public JSON-RPC snapshots recorded prospectively"
    gate["economic_metrics_allowed"] = True
    for key, result in variants.items():
        save_result(output, key, result)
    summary = pd.DataFrame([{"variant": key, "status": result.status, **result.metrics} for key, result in variants.items()])
    summary.to_csv(output / "strategy_summary.csv", index=False, float_format="%.12g")
    write_json(output / "CONFIG.json", asdict(cfg))
    write_json(output / "DATA_COVERAGE.json", coverage)
    write_json(output / "FINAL_GATE.json", gate)
    write_json(output / "INPUT_MANIFEST.json", {"source": "Deribit public JSON-RPC", "files": [{"path": str(p), "size": p.stat().st_size, "sha256": sha256_file(p)} for p in files]})
    make_report(output, gate, summary, coverage)
    write_json(output / "OUTPUT_MANIFEST.json", output_manifest(output, exclude={"OUTPUT_MANIFEST.json"}))
    return gate


def verify_results(output: Path) -> dict[str, Any]:
    failures: list[str] = []
    manifest_path = output / "OUTPUT_MANIFEST.json"
    if not manifest_path.exists():
        failures.append("missing_manifest")
        manifest = {"files": []}
    else:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for item in manifest.get("files", []):
        path = output / item["path"]
        if not path.exists(): failures.append(f"missing:{item['path']}")
        elif path.stat().st_size != item["size"]: failures.append(f"size:{item['path']}")
        elif sha256_file(path) != item["sha256"]: failures.append(f"sha256:{item['path']}")
    ledgers = sorted(output.glob("*_exact_ledger.csv.gz"))
    if not ledgers:
        failures.append("no_ledgers")
    for path in ledgers:
        ledger = pd.read_csv(path, compression="gzip")
        failures.extend(f"{path.name}:{failure}" for failure in verify_ledger(ledger))
    gate_path = output / "FINAL_GATE.json"
    if not gate_path.exists():
        failures.append("missing_final_gate")
        gate = {}
    else:
        gate = json.loads(gate_path.read_text(encoding="utf-8"))
    if gate.get("free_open_data_only") is not True:
        failures.append("free_open_data_only_not_asserted")
    result = {"passed": not failures, "failures": failures, "ledger_count": len(ledgers), "tree_sha256": manifest.get("tree_sha256")}
    if failures:
        raise RuntimeError(json.dumps(result, indent=2))
    return result

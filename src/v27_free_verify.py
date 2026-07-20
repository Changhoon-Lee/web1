#!/usr/bin/env python3
"""Verify V27 free/open-data results without weakening fail-closed semantics."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def verify(output: Path) -> dict[str, Any]:
    failures: list[str] = []
    gate_path = output / "FINAL_GATE.json"
    manifest_path = output / "OUTPUT_MANIFEST.json"
    report_path = output / "FINAL_REPORT.md"
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
    if not report_path.exists():
        failures.append("missing_final_report")
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
        "HISTORICAL_DERIBIT_LONG_GAMMA_REJECTED",
        "HISTORICAL_DERIBIT_LONG_GAMMA_PASS_NEEDS_NEW_OOS",
    }
    if status not in allowed:
        failures.append(f"invalid_status:{status}")
    if gate.get("free_open_data_only") is not True:
        failures.append("free_open_data_only_not_asserted")
    if status == "FREE_OPEN_DATA_CONTINUITY_NOT_READY" and gate.get("economic_metrics_allowed") is not False:
        failures.append("economic_metrics_not_blocked")
    result = {
        "passed": not failures,
        "status": status,
        "failures": failures,
        "manifest_file_count": len(manifest.get("files", [])),
        "tree_sha256": manifest.get("tree_sha256"),
    }
    if failures:
        raise RuntimeError(json.dumps(result, indent=2))
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("v27_free_results"))
    args = parser.parse_args()
    print(json.dumps(verify(args.output), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

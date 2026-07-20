from __future__ import annotations

import argparse
import asyncio
import json
import math
import os
import shutil
from pathlib import Path
from typing import Any

import pandas as pd

from .v271_core import (
    LabConfig,
    build_manifest,
    deterministic_zip,
    exact_ledger,
    run_open_free_lab,
    sha256_file,
    verify_manifest,
    write_json,
)
from .v271_deribit_public import fetch_all_free_data, record_public_chain


def read_inputs(data_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    index_path = data_dir / "btc_index.csv.gz"
    dvol_path = data_dir / "btc_dvol.csv.gz"
    if not index_path.exists() or not dvol_path.exists():
        raise FileNotFoundError("Run the free Deribit downloader first: missing btc_index.csv.gz or btc_dvol.csv.gz")
    return pd.read_csv(index_path), pd.read_csv(dvol_path)


def _clean_result_payload(result: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in result.items() if key != "frames"}


def _fmt(value: Any, digits: int = 4) -> str:
    if value is None:
        return "—"
    try:
        v = float(value)
    except (TypeError, ValueError):
        return str(value)
    if not math.isfinite(v):
        return "—"
    return f"{v:.{digits}f}"


def markdown_table(headers: list[str], rows: list[list[Any]]) -> str:
    def esc(v: Any) -> str:
        return str(v).replace("|", "\\|").replace("\n", " ")
    lines = ["| " + " | ".join(map(esc, headers)) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    lines.extend("| " + " | ".join(esc(v) for v in row) + " |" for row in rows)
    return "\n".join(lines)


def build_report(result: dict[str, Any], provenance: dict[str, Any] | None) -> str:
    status = result["status"]
    strategies = result["strategies"]
    rows = []
    for name, metrics in strategies.items():
        rows.append([name, _fmt(metrics.get("sharpe"), 3), f"{_fmt(100 * metrics.get('cagr', float('nan')), 2)}%", f"{_fmt(100 * metrics.get('mdd', float('nan')), 2)}%", _fmt(metrics.get("wealth"), 4)])
    vrp = result["variance_risk_premium"]
    continuity = result["continuity"]
    paid = provenance.get("paid_sources_used") if provenance else None
    lines = [
        "# V27.1 Open-Free Deribit Long-Variance Lab",
        "",
        "## Final status",
        "",
        f"- Model status: `{status['model_status']}`",
        f"- Deployable status: `{status['deployable_status']}`",
        f"- Historical claim: `{status['historical_claim']}`",
        "",
        "The historical test uses only Deribit public DVOL and BTC index data. It is a model-based feasibility and falsification test, not an executable historical option-chain backtest.",
        "",
        "## Data coverage",
        "",
        f"- Calendar days: {continuity['calendar_days']}",
        f"- Active days: {continuity['active_days']}",
        f"- Coverage: {100 * continuity['coverage']:.2f}%",
        f"- Maximum observation gap: {continuity['max_gap_days']:.2f} days",
        f"- Monthly non-overlapping 30-day anchors: {result['anchors']}",
        f"- Paid data used: {paid}",
        "",
        "## Model strategy diagnostics",
        "",
        markdown_table(["Variant", "Sharpe", "CAGR", "MDD", "Wealth"], rows),
        "",
        "## Long-variance diagnostic",
        "",
        f"- Mean realized variance minus implied variance: {_fmt(vrp['newey_west']['mean'], 6)}",
        f"- Newey-West t statistic: {_fmt(vrp['newey_west']['t'], 3)}",
        f"- Bootstrap 95% interval: [{_fmt(vrp['bootstrap']['lower'], 6)}, {_fmt(vrp['bootstrap']['upper'], 6)}]",
        f"- Bootstrap probability mean is positive: {_fmt(vrp['bootstrap']['p_positive'], 3)}",
        f"- Positive monthly payoff fraction: {_fmt(vrp['positive_fraction'], 3)}",
        "",
        "## Mandatory interpretation",
        "",
        "- No paid source, private API, or Tardis archive is used.",
        "- Historical bid/ask option-chain data is not reconstructed or imputed.",
        "- Black–Scholes/DVOL straddle results are theoretical execution-stress diagnostics.",
        "- Even a positive result cannot be promoted beyond `EXECUTION_UNVERIFIED`.",
        "- The public recorder can accumulate real future bid/ask and Greeks without an API key.",
    ]
    return "\n".join(lines) + "\n"


def run_lab(root: Path, cfg: LabConfig | None = None) -> dict[str, Any]:
    cfg = cfg or LabConfig()
    data_dir = root / "data" / "deribit_public"
    results_dir = root / "v271_results"
    results_dir.mkdir(parents=True, exist_ok=True)
    index_frame, dvol_frame = read_inputs(data_dir)
    result = run_open_free_lab(index_frame, dvol_frame, cfg)
    frames = result["frames"]
    provenance_path = data_dir / "FREE_DATA_PROVENANCE.json"
    provenance = json.loads(provenance_path.read_text(encoding="utf-8")) if provenance_path.exists() else None

    frames["market"].reset_index().to_csv(results_dir / "daily_market.csv.gz", index=False, compression={"method": "gzip", "mtime": 0})
    frames["anchors"].to_csv(results_dir / "monthly_variance_anchors.csv", index=False)
    strategy_map = {
        "synthetic_delta_hedged": (frames["base_curve"], frames["base_ledger"]),
        "synthetic_unhedged": (frames["unhedged_curve"], frames["unhedged_ledger"]),
        "synthetic_delta_hedged_cost_2x": (frames["cost2_curve"], frames["cost2_ledger"]),
        "synthetic_delta_hedged_cost_3x": (frames["cost3_curve"], frames["cost3_ledger"]),
    }
    for name, (curve, ledger) in strategy_map.items():
        curve.reset_index().to_csv(results_dir / f"{name}_equity.csv.gz", index=False, compression={"method": "gzip", "mtime": 0})
        ledger.to_csv(results_dir / f"{name}_trades.csv", index=False)
        exact_ledger(curve).to_csv(results_dir / f"{name}_exact_ledger.csv.gz", index=False, compression={"method": "gzip", "mtime": 0})
    payload = _clean_result_payload(result)
    write_json(results_dir / "FINAL_GATE.json", payload)
    (results_dir / "FINAL_REPORT.md").write_text(build_report(payload, provenance), encoding="utf-8")
    write_json(results_dir / "INPUT_IDENTITY.json", {
        "index_file": str(data_dir / "btc_index.csv.gz"),
        "index_sha256": sha256_file(data_dir / "btc_index.csv.gz"),
        "dvol_file": str(data_dir / "btc_dvol.csv.gz"),
        "dvol_sha256": sha256_file(data_dir / "btc_dvol.csv.gz"),
        "provenance_file": str(provenance_path) if provenance_path.exists() else None,
        "paid_sources_used": provenance.get("paid_sources_used") if provenance else None,
    })
    manifest = build_manifest(results_dir, exclude={"OUTPUT_MANIFEST.json"})
    write_json(results_dir / "OUTPUT_MANIFEST.json", manifest)
    return payload


def verify_results(root: Path) -> tuple[bool, list[str]]:
    results_dir = root / "v271_results"
    manifest_path = results_dir / "OUTPUT_MANIFEST.json"
    errors: list[str] = []
    if not manifest_path.exists():
        return False, ["missing OUTPUT_MANIFEST.json"]
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    ok, manifest_errors = verify_manifest(results_dir, manifest)
    errors.extend(manifest_errors)
    gate_path = results_dir / "FINAL_GATE.json"
    if not gate_path.exists():
        errors.append("missing FINAL_GATE.json")
    else:
        gate = json.loads(gate_path.read_text(encoding="utf-8"))
        if gate.get("status", {}).get("deployable_status") != "BLOCKED_NO_HISTORICAL_OPTION_BID_ASK_CHAIN":
            errors.append("deployable gate must remain blocked")
    identity_path = results_dir / "INPUT_IDENTITY.json"
    if not identity_path.exists():
        errors.append("missing INPUT_IDENTITY.json")
    else:
        identity = json.loads(identity_path.read_text(encoding="utf-8"))
        if identity.get("paid_sources_used") is not False:
            errors.append("paid source detected or provenance missing")
    return ok and not errors, errors


def pack(root: Path) -> Path:
    runtime = root / "runtime"
    runtime.mkdir(parents=True, exist_ok=True)
    destination = runtime / "V27_1_Open_Free_Deribit_Handoff.zip"
    deterministic_zip(root, destination)
    write_json(runtime / "V27_1_ZIP_INFO.json", {"file": destination.name, "size": destination.stat().st_size, "sha256": sha256_file(destination)})
    return destination


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="V27.1 open/free Deribit long-variance research lab")
    parser.add_argument("command", choices=["fetch", "run", "verify", "pack", "all", "record"])
    parser.add_argument("--root", default=".")
    parser.add_argument("--years", type=int, default=6)
    parser.add_argument("--record-minutes", type=int, default=60)
    parser.add_argument("--snapshot-seconds", type=int, default=30)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = Path(args.root).resolve()
    if args.command in {"fetch", "all"}:
        provenance = fetch_all_free_data(root / "data" / "deribit_public", years=args.years)
        print(json.dumps(provenance, ensure_ascii=False, indent=2))
    if args.command in {"run", "all"}:
        result = run_lab(root)
        print(json.dumps(result["status"], ensure_ascii=False, indent=2))
    if args.command in {"verify", "all"}:
        ok, errors = verify_results(root)
        print("VERIFY", "PASS" if ok else "FAIL")
        for error in errors:
            print("-", error)
        if not ok:
            return 2
    if args.command in {"pack", "all"}:
        path = pack(root)
        print(path)
    if args.command == "record":
        asyncio.run(record_public_chain(root / "data" / "forward_public_chain", minutes=args.record_minutes, snapshot_seconds=args.snapshot_seconds))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""CLI for V25 Dual Causal Defense."""
from __future__ import annotations

import argparse
import json
import os
import shutil
from dataclasses import asdict, replace
from pathlib import Path
from typing import Any

import pandas as pd

import v25_core as core


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def markdown_table(frame: pd.DataFrame) -> str:
    data = frame.copy()
    columns = [str(c) for c in data.columns]
    def fmt(value: Any) -> str:
        if pd.isna(value):
            return ""
        if isinstance(value, float):
            return f"{value:.6g}"
        return str(value).replace("|", "\\|").replace("\n", " ")
    lines = ["| " + " | ".join(columns) + " |", "| " + " | ".join("---" for _ in columns) + " |"]
    for row in data.itertuples(index=False, name=None):
        lines.append("| " + " | ".join(fmt(v) for v in row) + " |")
    return "\n".join(lines)


def config_from_args(args: argparse.Namespace) -> core.Config:
    cfg = core.Config(
        delay=int(os.getenv("V25_DELAY", getattr(args, "delay", 2))),
        one_way_cost_bps=float(os.getenv("V25_COST_BPS", getattr(args, "cost_bps", 17.0))),
        bootstrap_samples=int(os.getenv("V25_BOOTSTRAP_SAMPLES", getattr(args, "bootstrap_samples", 5000))),
        allow_unverified_tail=os.getenv("V25_ALLOW_UNVERIFIED_TAIL", "0") == "1",
    )
    cfg.validate()
    return cfg


def _save_strategy(output: Path, result: core.StrategyResult) -> dict[str, Any]:
    safe = result.name.lower()
    pd.DataFrame({"date": result.returns.index, "return": result.returns.values, "equity": result.equity.values}).to_csv(
        output / f"{safe}_returns.csv.gz", index=False, compression="gzip", float_format="%.12g"
    )
    weights = result.weights.reset_index().rename(columns={result.weights.index.name or "index": "date"})
    weights["turnover"] = result.turnover.values
    weights["cost"] = result.costs.values
    weights.to_csv(output / f"{safe}_weights.csv.gz", index=False, compression="gzip", float_format="%.12g")
    result.ledger.to_csv(output / f"{safe}_exact_ledger.csv.gz", index=False, compression="gzip")
    if not result.diagnostics.empty:
        result.diagnostics.reset_index().rename(columns={result.diagnostics.index.name or "index": "date"}).to_csv(
            output / f"{safe}_diagnostics.csv.gz", index=False, compression="gzip", float_format="%.12g"
        )
    if not result.qualification.empty:
        result.qualification.to_csv(output / f"{safe}_qualification.csv", index=False, float_format="%.12g")
    gross = result.weights.drop(columns=["CASH"]).abs().sum(axis=1)
    metrics = core.performance_metrics(result.returns, gross)
    metrics.update({
        "name": result.name,
        "average_turnover": float(result.turnover.mean()),
        "total_turnover": float(result.turnover.sum()),
        "total_cost": float(result.costs.sum()),
        "ledger_sha256": result.ledger.attrs.get("sha256"),
    })
    return metrics


def _make_report(output: Path, summary: pd.DataFrame, gate: dict[str, Any], identity: dict[str, Any], tail_cols: list[str]) -> None:
    lines = [
        "# V25 Dual Causal Defense — Final Report", "",
        f"Protocol version: `{core.VERSION}`", "",
        "## Identity", "",
        f"- Baseline: `{identity['name']}`", f"- Not baseline: `{identity['not_name']}`",
        f"- Period: {identity['aligned_start']} to {identity['aligned_end']}",
        f"- Observations: {identity['aligned_observations']}", "",
        "## Tail engine columns", "",
        "`" + (", ".join(tail_cols) if tail_cols else "NONE") + "`", "",
        "## Strategy metrics", "", markdown_table(summary), "",
        "## Final status", "", "```text",
        f"CORE_DERISK: {gate['core_status']}",
        f"TAIL_ENGINE: {gate['tail_engine_status']}",
        f"DUAL_DEFENSE: {gate['dual_status']}",
        f"OVERALL: {gate['overall_status']}", "```", "",
        "## Deductive boundary", "",
        "The controller guarantees only the registered algebraic invariants and a stress-set capacity calculation. It does not guarantee future returns or protection from losses outside the registered stress set. Tail engines require external point-in-time provenance before official qualification.", "",
    ]
    (output / "FINAL_REPORT.md").write_text("\n".join(lines), encoding="utf-8")


def run_lab(input_path: Path, provenance_path: Path | None, output: Path, cfg: core.Config) -> dict[str, Any]:
    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True)
    data = core.canonicalize_input(input_path)
    provenance = core.load_provenance(provenance_path)
    strategies = {
        "v10": core.run_v10(data, cfg),
        "core": core.run_core_derisk(data, cfg),
        "dual": core.run_dual_defense(data, cfg, provenance),
    }
    strategies["core_control"] = core.run_equal_average_control(data, cfg, strategies["core"], "CORE_EQUAL_AVERAGE_CONTROL")
    strategies["dual_control"] = core.run_equal_average_control(data, cfg, strategies["dual"], "DUAL_EQUAL_AVERAGE_CONTROL")

    metrics = [_save_strategy(output, result) for result in strategies.values()]
    summary = pd.DataFrame(metrics)
    ordered = ["name", "sharpe", "cagr", "mdd", "calmar", "cvar5", "final_equity", "average_gross", "maximum_gross", "average_turnover", "total_cost", "liquidations", "start", "end", "observations", "ledger_sha256"]
    summary = summary[[c for c in ordered if c in summary.columns]]
    summary.to_csv(output / "strategy_summary.csv", index=False, float_format="%.12g")

    identity = core.baseline_identity(data, cfg, input_path)
    core.write_json(output / "BASELINE_IDENTITY.json", identity)
    core.write_json(output / "CONFIG.json", asdict(cfg))
    core.write_json(output / "INPUT_MANIFEST.json", {
        "path": input_path, "sha256": core.sha256_file(input_path), "rows": len(data),
        "start": data.index[0], "end": data.index[-1], "columns": list(data.columns),
        "tail_columns": core.tail_columns(data), "provenance": provenance,
    })

    core_gate = core.strategy_gate(strategies["core"], strategies["v10"])
    dual_gate = core.strategy_gate(strategies["dual"], strategies["v10"])
    tail_increment = core.incremental_gate(strategies["dual"], strategies["core"])
    core_dynamic = core.incremental_gate(strategies["core"], strategies["core_control"])
    dual_dynamic = core.incremental_gate(strategies["dual"], strategies["dual_control"])

    qualification = strategies["dual"].qualification
    qualified_count = int(qualification[qualification.get("qualified", False) == True]["engine"].nunique()) if not qualification.empty and "qualified" in qualification else 0
    tail_cols = core.tail_columns(data)
    if not tail_cols:
        tail_status = "NO_TAIL_ENGINE_COLUMNS"
    elif qualified_count == 0:
        tail_status = "NO_QUALIFIED_PROVENANCE_BACKED_TAIL_ENGINE"
    elif tail_increment["pass"]:
        tail_status = "TAIL_ENGINE_INCREMENTAL_PASS_NEEDS_NEW_OOS"
    else:
        tail_status = "QUALIFIED_TAIL_ENGINE_NO_INCREMENTAL_VALUE"
    core_status = "CORE_DERISK_HISTORICAL_PASS_NEEDS_NEW_OOS" if core_gate["pass"] and core_dynamic["pass"] else "CORE_DERISK_NO_PARETO_VALUE"
    dual_status = "DUAL_DEFENSE_HISTORICAL_PARETO_PASS_NEEDS_NEW_OOS" if dual_gate["pass"] and tail_increment["pass"] else "DUAL_DEFENSE_NO_HISTORICAL_PARETO_VALUE"
    overall = dual_status if dual_status.startswith("DUAL_DEFENSE_HISTORICAL") else core_status if core_status.startswith("CORE_DERISK_HISTORICAL") else "NO_HISTORICAL_PARETO_STRATEGY_FOUND"

    boot_rows = []
    for candidate_key, baseline_key, label in (("core", "v10", "CORE_vs_V10"), ("dual", "v10", "DUAL_vs_V10"), ("dual", "core", "DUAL_vs_CORE")):
        for block in (30, 60, 120):
            row = core.paired_block_bootstrap(
                strategies[candidate_key].returns, strategies[baseline_key].returns,
                block, cfg.bootstrap_samples, cfg.random_seed + block + sum(ord(x) for x in label),
            )
            row["comparison"] = label
            boot_rows.append(row)
    pd.DataFrame(boot_rows).to_csv(output / "bootstrap_results.csv", index=False, float_format="%.12g")

    gate = {
        "version": core.VERSION,
        "core_status": core_status,
        "tail_engine_status": tail_status,
        "dual_status": dual_status,
        "overall_status": overall,
        "qualified_tail_engine_count": qualified_count,
        "core_gate": core_gate,
        "dual_gate": dual_gate,
        "tail_incremental_gate": tail_increment,
        "core_dynamic_gate": core_dynamic,
        "dual_dynamic_gate": dual_dynamic,
    }
    core.write_json(output / "FINAL_GATE.json", gate)
    _make_report(output, summary, gate, identity, tail_cols)
    manifest = core.output_manifest(output, exclude={"OUTPUT_MANIFEST.json"})
    core.write_json(output / "OUTPUT_MANIFEST.json", manifest)
    return gate


def verify_results(output: Path) -> dict[str, Any]:
    manifest_path = output / "OUTPUT_MANIFEST.json"
    if not manifest_path.exists():
        raise FileNotFoundError(manifest_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    failures: list[str] = []
    for item in manifest["files"]:
        path = output / item["path"]
        if not path.exists():
            failures.append(f"missing:{item['path']}")
        elif path.stat().st_size != item["size"]:
            failures.append(f"size:{item['path']}")
        elif core.sha256_file(path) != item["sha256"]:
            failures.append(f"sha256:{item['path']}")
    ledgers = sorted(output.glob("*_exact_ledger.csv.gz"))
    if len(ledgers) < 5:
        failures.append("ledger_count")
    for path in ledgers:
        frame = pd.read_csv(path, compression="gzip")
        if not (frame["net_ppm"] == 1_000_000).all():
            failures.append(f"net:{path.name}")
        if (frame["risky_gross_ppm"] > 1_000_000).any():
            failures.append(f"gross:{path.name}")
        if "v10_ppm" in frame and ((frame["v10_ppm"] < 0) | (frame["v10_ppm"] > 1_000_000)).any():
            failures.append(f"core_bounds:{path.name}")
        tail_ppm = [c for c in frame.columns if c.startswith("tail_") and c.endswith("_ppm")]
        if tail_ppm and (frame[tail_ppm] < 0).any().any():
            failures.append(f"negative_tail:{path.name}")
    gate = json.loads((output / "FINAL_GATE.json").read_text(encoding="utf-8"))
    if not {"core_status", "tail_engine_status", "dual_status", "overall_status"}.issubset(gate):
        failures.append("gate_schema")
    result = {"version": core.VERSION, "passed": not failures, "failures": failures, "ledger_count": len(ledgers), "tree_sha256": manifest.get("tree_sha256")}
    if failures:
        raise RuntimeError(json.dumps(result, indent=2))
    return result


def build_handoff(root: Path, output: Path, destination: Path) -> dict[str, Any]:
    verification = verify_results(output)
    core.deterministic_zip(root, destination, exclusions={destination.relative_to(root).as_posix()} if destination.is_relative_to(root) else set())
    return {"path": destination, "size": destination.stat().st_size, "sha256": core.sha256_file(destination), "verification": verification}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="V25 Dual Causal Defense")
    sub = parser.add_subparsers(dest="command", required=True)
    for command in ("run", "all"):
        p = sub.add_parser(command)
        p.add_argument("--input", type=Path)
        p.add_argument("--provenance", type=Path)
        p.add_argument("--output", type=Path, default=Path("v25_results"))
        p.add_argument("--handoff", type=Path, default=Path("runtime/V25_Dual_Causal_Defense_Handoff.zip"))
        p.add_argument("--delay", type=int, default=2)
        p.add_argument("--cost-bps", type=float, default=17.0)
        p.add_argument("--bootstrap-samples", type=int, default=5000)
    p = sub.add_parser("verify")
    p.add_argument("--output", type=Path, default=Path("v25_results"))
    p = sub.add_parser("handoff")
    p.add_argument("--output", type=Path, default=Path("v25_results"))
    p.add_argument("--destination", type=Path, default=Path("runtime/V25_Dual_Causal_Defense_Handoff.zip"))
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = project_root()
    if args.command in ("run", "all"):
        cfg = config_from_args(args)
        input_path = core.discover_input(root, args.input)
        output = args.output if args.output.is_absolute() else root / args.output
        gate = run_lab(input_path, args.provenance, output, cfg)
        print(json.dumps(core._json_safe(gate), indent=2, ensure_ascii=False, allow_nan=False))
        if args.command == "all":
            destination = args.handoff if args.handoff.is_absolute() else root / args.handoff
            print(json.dumps(core._json_safe(build_handoff(root, output, destination)), indent=2, ensure_ascii=False, allow_nan=False))
    elif args.command == "verify":
        output = args.output if args.output.is_absolute() else root / args.output
        print(json.dumps(verify_results(output), indent=2))
    elif args.command == "handoff":
        output = args.output if args.output.is_absolute() else root / args.output
        destination = args.destination if args.destination.is_absolute() else root / args.destination
        print(json.dumps(core._json_safe(build_handoff(root, output, destination)), indent=2, ensure_ascii=False, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

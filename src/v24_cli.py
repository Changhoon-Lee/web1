#!/usr/bin/env python3
"""Command-line runner for the V24 Portable Diversifier Overlay lab."""
from __future__ import annotations

import argparse
import json
import math
import os
import shutil
import sys
from dataclasses import asdict, replace
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from v24_core import (
    VERSION,
    Config,
    StrategyResult,
    baseline_identity,
    causal_inverse_vol_anchor,
    deflated_sharpe_probability,
    deterministic_zip,
    discover_input,
    economic_gates,
    feasibility_screen,
    financing_cost_stress,
    gap_stress_table,
    incremental_gate,
    json_default,
    leave_one_year_out,
    newey_west_mean_test,
    output_manifest,
    paired_block_bootstrap,
    performance_metrics,
    run_dynamic_overlay,
    run_equal_average_overlay_control,
    run_static_portable,
    run_uniform_diluted,
    run_v10,
    sha256_file,
    start_shift_stress,
    transaction_cost_stress,
    write_json,
    canonicalize_input,
)


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def config_from_environment(args: argparse.Namespace) -> Config:
    samples = int(os.getenv("V24_BOOTSTRAP_SAMPLES", getattr(args, "bootstrap_samples", 10000)))
    cfg = Config(
        delay=int(os.getenv("V24_DELAY", getattr(args, "delay", 2))),
        one_way_cost_bps=float(os.getenv("V24_COST_BPS", getattr(args, "cost_bps", 17.0))),
        borrow_spread_annual=float(os.getenv("V24_BORROW_SPREAD", getattr(args, "borrow_spread", 0.05))),
        bootstrap_samples=samples,
    )
    cfg.validate()
    return cfg


def _strategy_metrics(result: StrategyResult) -> dict[str, Any]:
    gross = result.weights[["V10", "EQUITY_TREND", "GOLD_TREND"]].abs().sum(axis=1)
    metrics = performance_metrics(result.returns, gross)
    metrics.update({
        "name": result.name,
        "average_turnover": float(result.turnover.mean()),
        "total_turnover": float(result.turnover.sum()),
        "total_financing": float(result.financing.sum()),
        "ledger_sha256": result.ledger.attrs.get("sha256"),
    })
    return metrics


def _save_strategy(output: Path, result: StrategyResult) -> None:
    safe = result.name.lower()
    pd.DataFrame({"date": result.returns.index, "return": result.returns.values, "equity": result.equity.values}).to_csv(output / f"{safe}_returns.csv.gz", index=False, compression="gzip", float_format="%.12g")
    frame = result.weights.reset_index().rename(columns={result.weights.index.name or "index": "date"})
    frame["turnover"] = result.turnover.values
    frame["financing"] = result.financing.values
    frame.to_csv(output / f"{safe}_weights.csv.gz", index=False, compression="gzip", float_format="%.12g")
    result.ledger.to_csv(output / f"{safe}_exact_ledger.csv.gz", index=False, compression="gzip", float_format="%.12g")
    result.contributions.reset_index().rename(columns={result.contributions.index.name or "index": "date"}).to_csv(output / f"{safe}_contributions.csv.gz", index=False, compression="gzip", float_format="%.12g")
    if result.diagnostics is not None and not result.diagnostics.empty:
        result.diagnostics.reset_index().rename(columns={result.diagnostics.index.name or "index": "date"}).to_csv(output / f"{safe}_diagnostics.csv.gz", index=False, compression="gzip", float_format="%.12g")


def _comparison_statistics(candidate: StrategyResult, control: StrategyResult, cfg: Config, label: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    boot = []
    for block in (30, 60, 120):
        row = paired_block_bootstrap(candidate.returns, control.returns, block, cfg.bootstrap_samples, cfg.random_seed + block + sum(ord(c) for c in label))
        row["comparison"] = label
        boot.append(row)
    diff = candidate.returns - control.returns
    hac = []
    for lag in (20, 60, 120):
        row = newey_west_mean_test(diff, lag)
        row["comparison"] = label
        hac.append(row)
    dsr = {
        "comparison": label,
        "candidate": deflated_sharpe_probability(candidate.returns, cfg.trials_for_dsr),
        "active_return": deflated_sharpe_probability(diff, cfg.trials_for_dsr),
    }
    return boot, hac, dsr


def _delay_stress(data: pd.DataFrame, cfg: Config) -> list[dict[str, Any]]:
    rows = []
    for delay in (2, 3, 4):
        stressed_cfg = replace(cfg, delay=delay)
        no_tilt = run_dynamic_overlay(data, stressed_cfg, online=False)
        online = run_dynamic_overlay(data, stressed_cfg, online=True)
        for result in (no_tilt, online):
            metrics = _strategy_metrics(result)
            rows.append({"stress": "execution_delay", "value": delay, **metrics})
    return rows


def _correlation_stress(data: pd.DataFrame, cfg: Config) -> list[dict[str, Any]]:
    rows = []
    oos = data.iloc[cfg.warmup_days + cfg.delay :]
    vols = oos[["V10", "EQUITY_TREND", "GOLD_TREND"]].std(ddof=1).to_numpy() * math.sqrt(365.25)
    weights = np.asarray([1.0, 0.30, 0.30])
    for floor in (0.50, 0.75, 1.00):
        corr = np.full((3, 3), floor, dtype=float)
        np.fill_diagonal(corr, 1.0)
        cov = np.outer(vols, vols) * corr
        vol = float(math.sqrt(max(float(weights @ cov @ weights), 0.0)))
        rows.append({"stress": "correlation_floor", "value": floor, "projected_annual_volatility": vol})
    return rows


def _make_final_report(path: Path, gate: dict[str, Any], summary: pd.DataFrame, feasibility: dict[str, Any], baseline: dict[str, Any]) -> None:
    lines = [
        "# V24 Portable Diversifier Overlay — Final Report",
        "",
        f"Protocol version: `{VERSION}`",
        "",
        "## Baseline identity",
        "",
        f"- Name: `{baseline['name']}`",
        f"- This is not: `{baseline['not_name']}`",
        f"- Aligned period: {baseline['aligned_start']} to {baseline['aligned_end']}",
        f"- Observations: {baseline['aligned_observations']}",
        "",
        "## Strategy metrics",
        "",
        summary.to_markdown(index=False),
        "",
        "## Feasibility",
        "",
        f"- Required overlay for aligned V10 CAGR: `{feasibility['required_overlay_for_v10_cagr']}`",
        f"- Maximum overlay under MDD gate: `{feasibility['maximum_overlay_under_mdd_gate']}`",
        f"- Protocol overlay cap: `{feasibility['protocol_max_overlay']}`",
        f"- Feasible: `{feasibility['feasible']}`",
        "",
        "## Final status",
        "",
        "```text",
        f"STATIC_PORTABLE_30_30: {gate['static_status']}",
        f"DYNAMIC_CONTROLLER:    {gate['dynamic_status']}",
        f"ONLINE_OVERLAY:        {gate['online_status']}",
        f"OVERALL:               {gate['overall_status']}",
        "```",
        "",
        "## Interpretation boundary",
        "",
        "Even a full historical pass is capped at `HISTORICAL_PORTABLE_OVERLAY_PARETO_PASS_NEEDS_NEW_OOS`. The package does not claim live readiness, does not replace external data provenance, and does not equate the aligned common OOS baseline with the official full-history V10 record.",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def run_lab(input_path: Path, output: Path, cfg: Config) -> dict[str, Any]:
    output.mkdir(parents=True, exist_ok=True)
    data = canonicalize_input(input_path)
    strategies: dict[str, StrategyResult] = {}
    strategies["v10"] = run_v10(data, cfg)
    strategies["uniform"] = run_uniform_diluted(data, cfg)
    strategies["inverse_vol"] = causal_inverse_vol_anchor(data, cfg)
    strategies["static"] = run_static_portable(data, cfg)
    strategies["dynamic"] = run_dynamic_overlay(data, cfg, online=False)
    strategies["online"] = run_dynamic_overlay(data, cfg, online=True)
    strategies["dynamic_control"] = run_equal_average_overlay_control(data, cfg, strategies["dynamic"], "EQUAL_AVERAGE_DYNAMIC_CONTROL")
    strategies["online_control"] = run_equal_average_overlay_control(data, cfg, strategies["online"], "EQUAL_AVERAGE_ONLINE_CONTROL")

    for result in strategies.values():
        _save_strategy(output, result)

    metrics_rows = [_strategy_metrics(result) for result in strategies.values()]
    summary = pd.DataFrame(metrics_rows)
    ordered = ["name", "sharpe", "cagr", "mdd", "calmar", "cvar5", "final_equity", "average_risky_gross", "maximum_risky_gross", "average_turnover", "total_financing", "liquidations", "start", "end", "observations", "ledger_sha256"]
    summary = summary[[c for c in ordered if c in summary.columns]]
    summary.to_csv(output / "strategy_summary.csv", index=False, float_format="%.12g")

    identity = baseline_identity(data, cfg, input_path)
    write_json(output / "BASELINE_IDENTITY.json", identity)
    write_json(output / "CONFIG.json", asdict(cfg))
    write_json(output / "INPUT_MANIFEST.json", {"path": input_path, "sha256": sha256_file(input_path), "rows": len(data), "start": data.index[0], "end": data.index[-1], "columns": list(data.columns)})

    feasibility = feasibility_screen(data, cfg, strategies["v10"])
    grid = feasibility.pop("grid")
    pd.DataFrame(grid).to_csv(output / "feasibility_grid.csv", index=False, float_format="%.12g")
    write_json(output / "FEASIBILITY_SCREEN.json", feasibility)

    static_gate = economic_gates(strategies["static"], strategies["v10"])
    online_gate = incremental_gate(strategies["online"], strategies["dynamic"], "online")
    dynamic_gate = incremental_gate(strategies["dynamic"], strategies["dynamic_control"], "dynamic")

    bootstrap_rows: list[dict[str, Any]] = []
    hac_rows: list[dict[str, Any]] = []
    dsr_rows: list[dict[str, Any]] = []
    comparisons = (
        (strategies["static"], strategies["v10"], "STATIC_PORTABLE_30_30_vs_V10"),
        (strategies["dynamic"], strategies["dynamic_control"], "DYNAMIC_vs_EQUAL_AVERAGE"),
        (strategies["online"], strategies["dynamic"], "ONLINE_vs_NO_TILT"),
    )
    for candidate, control, label in comparisons:
        boot, hac, dsr = _comparison_statistics(candidate, control, cfg, label)
        bootstrap_rows.extend(boot)
        hac_rows.extend(hac)
        dsr_rows.append(dsr)
    pd.DataFrame(bootstrap_rows).to_csv(output / "bootstrap_results.csv", index=False, float_format="%.12g")
    pd.DataFrame(hac_rows).to_csv(output / "hac_results.csv", index=False, float_format="%.12g")
    write_json(output / "DSR_RESULTS.json", dsr_rows)

    primary_boot = [r for r in bootstrap_rows if r["comparison"] == "STATIC_PORTABLE_30_30_vs_V10"]
    primary_stat_pass = all(r["delta_sharpe_p025"] > 0 and r["wealth_ratio_p025"] >= 1.0 for r in primary_boot)
    if static_gate["pass"] and primary_stat_pass:
        static_status = "HISTORICAL_PORTABLE_OVERLAY_PARETO_PASS_NEEDS_NEW_OOS"
    elif static_gate["pass"]:
        static_status = "HISTORICAL_ECONOMIC_PASS_STATISTICAL_UNRESOLVED"
    else:
        static_status = "REJECTED"
    online_status = "ONLINE_OVERLAY_INCREMENTAL_PASS_NEEDS_NEW_OOS" if online_gate["pass"] else "ONLINE_OVERLAY_NO_INCREMENTAL_VALUE"
    dynamic_status = "DYNAMIC_CONTROLLER_INCREMENTAL_PASS_NEEDS_NEW_OOS" if dynamic_gate["pass"] else "DYNAMIC_CONTROLLER_NO_INCREMENTAL_VALUE"
    overall = static_status if static_status != "REJECTED" else "NO_HISTORICAL_PARETO_STRATEGY_FOUND"
    final_gate = {
        "version": VERSION,
        "primary_hypothesis": "V10_100_PLUS_EQUITY_30_PLUS_GOLD_30_MINUS_CASH_60",
        "static_status": static_status,
        "dynamic_status": dynamic_status,
        "online_status": online_status,
        "overall_status": overall,
        "static_gate": static_gate,
        "dynamic_gate": dynamic_gate,
        "online_gate": online_gate,
        "primary_statistical_pass": primary_stat_pass,
        "feasibility": feasibility,
    }
    write_json(output / "FINAL_GATE.json", final_gate)

    stress_rows: list[dict[str, Any]] = []
    stress_rows.extend(financing_cost_stress(data, cfg, (cfg.borrow_spread_annual + 0.025, 0.08, 0.12)))
    stress_rows.extend(transaction_cost_stress(data, cfg, (17.0, 34.0, 51.0)))
    stress_rows.extend(_delay_stress(data, cfg))
    stress_rows.extend(_correlation_stress(data, cfg))
    pd.DataFrame(stress_rows).to_csv(output / "stress_tests.csv", index=False, float_format="%.12g")
    write_json(output / "GAP_STRESS.json", gap_stress_table())
    write_json(output / "START_SHIFT_STRESS.json", start_shift_stress(strategies["static"], strategies["v10"]))
    write_json(output / "LEAVE_ONE_YEAR_OUT.json", leave_one_year_out(strategies["static"], strategies["v10"]))

    attribution = pd.DataFrame({
        name: result.contributions.sum() for name, result in strategies.items()
    }).T.reset_index().rename(columns={"index": "strategy"})
    attribution.to_csv(output / "contribution_attribution.csv", index=False, float_format="%.12g")

    _make_final_report(output / "FINAL_REPORT.md", final_gate, summary, feasibility, identity)
    manifest = output_manifest(output, exclude={"OUTPUT_MANIFEST.json"})
    write_json(output / "OUTPUT_MANIFEST.json", manifest)
    return final_gate


def verify_results(output: Path) -> dict[str, Any]:
    manifest_path = output / "OUTPUT_MANIFEST.json"
    if not manifest_path.exists():
        raise FileNotFoundError(manifest_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    failures = []
    for item in manifest["files"]:
        path = output / item["path"]
        if not path.exists():
            failures.append(f"missing:{item['path']}")
        elif path.stat().st_size != item["size"]:
            failures.append(f"size:{item['path']}")
        elif sha256_file(path) != item["sha256"]:
            failures.append(f"sha256:{item['path']}")
    ledger_files = sorted(output.glob("*_exact_ledger.csv.gz"))
    if not ledger_files:
        failures.append("no_exact_ledgers")
    portable_ledgers = [p for p in ledger_files if any(key in p.name for key in ("static_portable", "dynamic_no_tilt", "dynamic_online", "equal_average"))]
    for path in ledger_files:
        frame = pd.read_csv(path, compression="gzip")
        if not (frame["net_ppm"] == 1_000_000).all():
            failures.append(f"net_ppm:{path.name}")
        if (frame["risky_gross_ppm"] < 0).any():
            failures.append(f"negative_gross:{path.name}")
    for path in portable_ledgers:
        frame = pd.read_csv(path, compression="gzip")
        if not (frame["v10_ppm"] == 1_000_000).all():
            failures.append(f"core_not_fixed:{path.name}")
        if (frame["risky_gross_ppm"] > 1_600_000).any():
            failures.append(f"gross_cap:{path.name}")
    gate = json.loads((output / "FINAL_GATE.json").read_text(encoding="utf-8"))
    required = {"static_status", "dynamic_status", "online_status", "overall_status"}
    if not required.issubset(gate):
        failures.append("final_gate_schema")
    result = {"version": VERSION, "passed": not failures, "failures": failures, "manifest_tree_sha256": manifest.get("tree_sha256"), "ledger_count": len(ledger_files)}
    if failures:
        raise RuntimeError(json.dumps(result, indent=2))
    return result


def build_handoff(root: Path, output: Path, destination: Path) -> dict[str, Any]:
    verification = verify_results(output)
    deterministic_zip(root, destination, include_results=True)
    return {"zip": destination, "sha256": sha256_file(destination), "size": destination.stat().st_size, "verification": verification}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="V24 Portable Diversifier Overlay Lab")
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("run", "all"):
        p = sub.add_parser(name)
        p.add_argument("--input", type=Path)
        p.add_argument("--output", type=Path, default=Path("results"))
        p.add_argument("--delay", type=int, default=2)
        p.add_argument("--cost-bps", type=float, default=17.0)
        p.add_argument("--borrow-spread", type=float, default=0.05)
        p.add_argument("--bootstrap-samples", type=int, default=10000)
        p.add_argument("--handoff", type=Path, default=Path("runtime/V24_ZCode_Handoff.zip"))
    p = sub.add_parser("verify")
    p.add_argument("--output", type=Path, default=Path("results"))
    p = sub.add_parser("handoff")
    p.add_argument("--output", type=Path, default=Path("results"))
    p.add_argument("--destination", type=Path, default=Path("runtime/V24_ZCode_Handoff.zip"))
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = project_root()
    if args.command in ("run", "all"):
        cfg = config_from_environment(args)
        input_path = discover_input(root, args.input)
        output = (root / args.output).resolve() if not args.output.is_absolute() else args.output
        if output.exists():
            shutil.rmtree(output)
        gate = run_lab(input_path, output, cfg)
        print(json.dumps(gate, default=json_default, indent=2))
        if args.command == "all":
            verification = verify_results(output)
            destination = (root / args.handoff).resolve() if not args.handoff.is_absolute() else args.handoff
            handoff = build_handoff(root, output, destination)
            print(json.dumps({"verification": verification, "handoff": handoff}, default=json_default, indent=2))
    elif args.command == "verify":
        output = (root / args.output).resolve() if not args.output.is_absolute() else args.output
        print(json.dumps(verify_results(output), indent=2))
    elif args.command == "handoff":
        output = (root / args.output).resolve() if not args.output.is_absolute() else args.output
        destination = (root / args.destination).resolve() if not args.destination.is_absolute() else args.destination
        print(json.dumps(build_handoff(root, output, destination), default=json_default, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

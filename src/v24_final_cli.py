#!/usr/bin/env python3
"""Authoritative one-command V24 final audited handoff runner."""
from __future__ import annotations

import argparse
import json
import os
import shutil
from pathlib import Path
from typing import Any

import pandas as pd

import v24_cli as base
from v24_core import Config, canonicalize_input, deterministic_zip, discover_input, json_default, sha256_file
from v24_tail_audit import (
    AUDIT_VERSION,
    markdown_table,
    refresh_manifest,
    run_tail_audit,
    verify_tail_audit,
    write_audited_report,
)


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _base_report_without_tabulate(path: Path, gate: dict[str, Any], summary: pd.DataFrame, feasibility: dict[str, Any], baseline: dict[str, Any]) -> None:
    lines = [
        "# V24 Portable Diversifier Overlay — Base Report",
        "",
        f"- Baseline: `{baseline['name']}`",
        f"- Aligned period: {baseline['aligned_start']} to {baseline['aligned_end']}",
        f"- Observations: {baseline['aligned_observations']}",
        "",
        "## Strategy metrics",
        "",
        markdown_table(summary),
        "",
        "## Base status",
        "",
        "```text",
        f"STATIC_PORTABLE_30_30: {gate['static_status']}",
        f"DYNAMIC_CONTROLLER:    {gate['dynamic_status']}",
        f"ONLINE_OVERLAY:        {gate['online_status']}",
        f"OVERALL:               {gate['overall_status']}",
        "```",
        "",
        f"Feasible interval exists: `{feasibility.get('feasible')}`",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def config_from_args(args: argparse.Namespace) -> Config:
    cfg = Config(
        delay=int(os.getenv("V24_DELAY", args.delay)),
        one_way_cost_bps=float(os.getenv("V24_COST_BPS", args.cost_bps)),
        borrow_spread_annual=float(os.getenv("V24_BORROW_SPREAD", args.borrow_spread)),
        bootstrap_samples=int(os.getenv("V24_BOOTSTRAP_SAMPLES", args.bootstrap_samples)),
    )
    cfg.validate()
    return cfg


def resolve_output(root: Path, value: Path) -> Path:
    return value.resolve() if value.is_absolute() else (root / value).resolve()


def run_complete(input_path: Path, output: Path, cfg: Config) -> tuple[dict[str, Any], dict[str, Any]]:
    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True, exist_ok=True)
    base._make_final_report = _base_report_without_tabulate
    base_gate = base.run_lab(input_path, output, cfg)
    data = canonicalize_input(input_path)
    audit_gate = run_tail_audit(data, cfg, output)
    write_audited_report(output / "FINAL_REPORT.md", base_gate, audit_gate, output)
    refresh_manifest(output)
    base.verify_results(output)
    verify_tail_audit(output)
    return base_gate, audit_gate


def verify_complete(output: Path) -> dict[str, Any]:
    base_result = base.verify_results(output)
    audit_result = verify_tail_audit(output)
    report = (output / "FINAL_REPORT.md").read_text(encoding="utf-8")
    if "tabulate" in report.lower() and "removes the optional" not in report.lower():
        raise RuntimeError("unexpected optional tabulate dependency in final report")
    return {"base": base_result, "audit": audit_result, "passed": True}


def build_handoff(root: Path, output: Path, destination: Path) -> dict[str, Any]:
    verification = verify_complete(output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    deterministic_zip(root, destination, include_results=True)
    return {
        "path": destination,
        "sha256": sha256_file(destination),
        "size": destination.stat().st_size,
        "audit_version": AUDIT_VERSION,
        "verification": verification,
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="V24 final audited handoff")
    sub = parser.add_subparsers(dest="command", required=True)
    for command in ("run", "all"):
        p = sub.add_parser(command)
        p.add_argument("--input", type=Path)
        p.add_argument("--output", type=Path, default=Path("results"))
        p.add_argument("--handoff", type=Path, default=Path("runtime/V24_Final_Audited_Handoff.zip"))
        p.add_argument("--delay", type=int, default=2)
        p.add_argument("--cost-bps", type=float, default=17.0)
        p.add_argument("--borrow-spread", type=float, default=0.05)
        p.add_argument("--bootstrap-samples", type=int, default=10000)
    p = sub.add_parser("verify")
    p.add_argument("--output", type=Path, default=Path("results"))
    p = sub.add_parser("handoff")
    p.add_argument("--output", type=Path, default=Path("results"))
    p.add_argument("--destination", type=Path, default=Path("runtime/V24_Final_Audited_Handoff.zip"))
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = project_root()
    if args.command in ("run", "all"):
        cfg = config_from_args(args)
        input_path = discover_input(root, args.input)
        output = resolve_output(root, args.output)
        base_gate, audit_gate = run_complete(input_path, output, cfg)
        payload: dict[str, Any] = {"base_gate": base_gate, "audit_gate": audit_gate, "verification": verify_complete(output)}
        if args.command == "all":
            destination = resolve_output(root, args.handoff)
            payload["handoff"] = build_handoff(root, output, destination)
        print(json.dumps(payload, default=json_default, indent=2, ensure_ascii=False))
    elif args.command == "verify":
        print(json.dumps(verify_complete(resolve_output(root, args.output)), indent=2))
    else:
        output = resolve_output(root, args.output)
        destination = resolve_output(root, args.destination)
        print(json.dumps(build_handoff(root, output, destination), default=json_default, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

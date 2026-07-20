#!/usr/bin/env python3
"""Command line interface for V27 Deribit Long Gamma."""
from __future__ import annotations

import argparse
import json
import math
import os
import shutil
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any

import pandas as pd

from v27_core import (
    VERSION,
    Config,
    audit_suite,
    deterministic_zip,
    discover_chain_files,
    json_default,
    load_compact_data,
    output_manifest,
    prepare_compact_file,
    sha256_file,
    verify_ledger,
    write_json,
)


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def config_from_env(args: argparse.Namespace) -> Config:
    cfg = Config(
        currency=os.getenv("V27_CURRENCY", getattr(args, "currency", "BTC")),
        snapshot_minutes=int(os.getenv("V27_SNAPSHOT_MINUTES", getattr(args, "snapshot_minutes", 30))),
        initial_equity=float(os.getenv("V27_INITIAL_EQUITY", getattr(args, "initial_equity", 100000.0))),
    )
    cfg.validate()
    return cfg


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


def coverage_summary(data: pd.DataFrame, cfg: Config) -> dict[str, Any]:
    timestamps = pd.DatetimeIndex(sorted(data["timestamp"].dropna().unique()))
    if len(timestamps) < 2:
        return {"observations": len(timestamps), "active_days": 0, "span_days": 0.0, "active_day_ratio": 0.0, "maximum_gap_hours": math.inf, "contiguous_pass": False}
    active_days = len(set(timestamps.date))
    span_days = (timestamps[-1] - timestamps[0]).total_seconds() / 86400.0 + 1.0
    gaps = pd.Series(timestamps).diff().dt.total_seconds().dropna() / 3600.0
    maximum_gap = float(gaps.max()) if len(gaps) else math.inf
    active_ratio = float(active_days / max(span_days, 1.0))
    return {
        "observations": int(len(timestamps)),
        "active_days": int(active_days),
        "span_days": float(span_days),
        "active_day_ratio": active_ratio,
        "maximum_gap_hours": maximum_gap,
        "required_active_day_ratio": 0.80,
        "maximum_allowed_gap_hours": 48.0,
        "contiguous_pass": bool(active_ratio >= 0.80 and maximum_gap <= 48.0),
    }


def resolve_input(root: Path, explicit: Path | None = None) -> Path:
    if explicit is not None:
        path = explicit.expanduser().resolve()
        if not path.exists():
            raise FileNotFoundError(path)
        return path
    env = os.getenv("V27_OPTIONS_DATA_DIR")
    candidates = []
    if env:
        candidates.append(Path(env).expanduser())
    candidates.extend([
        root / "data/v27_compact",
        root / "data/v27_tardis",
        Path.home() / "Downloads/deribit_options",
        Path.home() / "Downloads/v27_options",
    ])
    for candidate in candidates:
        if candidate.exists() and discover_chain_files(candidate):
            return candidate.resolve()
    raise FileNotFoundError("Set V27_OPTIONS_DATA_DIR, pass --input, or run V27_DOWNLOAD_TARDIS.command")


def prepare_data(input_path: Path, compact_dir: Path, cfg: Config) -> dict[str, Any]:
    files = discover_chain_files(input_path)
    if not files:
        raise FileNotFoundError(f"no option chain files under {input_path}")
    if compact_dir.exists():
        shutil.rmtree(compact_dir)
    compact_dir.mkdir(parents=True)
    rows = []
    for i, source in enumerate(files):
        destination = compact_dir / f"{i:06d}_{source.name.replace('.csv.gz', '')}.compact.csv.gz"
        rows.append(prepare_compact_file(source, destination, cfg))
    manifest = {"version": VERSION, "input_root": input_path, "files": rows}
    write_json(compact_dir / "PREPARE_MANIFEST.json", manifest)
    return manifest


def save_result(output: Path, key: str, result: Any) -> None:
    result.ledger.to_csv(output / f"{key}_exact_ledger.csv.gz", index=False, compression={"method": "gzip", "mtime": 0}, float_format="%.12g")
    result.trades.to_csv(output / f"{key}_trades.csv.gz", index=False, compression={"method": "gzip", "mtime": 0}, float_format="%.12g")
    result.diagnostics.to_csv(output / f"{key}_diagnostics.csv", index=False, float_format="%.12g")
    write_json(output / f"{key}_metrics.json", {"name": result.name, "status": result.status, **result.metrics})


def make_report(output: Path, gate: dict[str, Any], summary: pd.DataFrame, coverage: dict[str, Any]) -> None:
    lines = [
        "# V27 Deribit Long Gamma — Final Report",
        "",
        f"Protocol version: `{VERSION}`",
        "",
        "## Data coverage",
        "",
        f"- Active days: `{coverage['active_days']}`",
        f"- Span days: `{coverage['span_days']:.3f}`",
        f"- Active-day ratio: `{coverage['active_day_ratio']:.6f}`",
        f"- Maximum timestamp gap: `{coverage['maximum_gap_hours']:.3f} hours`",
        f"- Contiguous pass: `{coverage['contiguous_pass']}`",
        "",
        "## Variant metrics",
        "",
        manual_markdown(summary),
        "",
        "## Final gate",
        "",
        "```text",
        f"PRIMARY: {gate['primary_status']}",
        f"OVERALL: {gate['overall_status']}",
        "```",
        "",
        "## Interpretation boundary",
        "",
        "This package evaluates a pre-registered ATM long-straddle plus causal delta-hedging rule. It does not claim that all possible option strategies are impossible. Sparse free monthly samples cannot produce an economic pass. Any historical pass remains capped at NEEDS_NEW_OOS.",
        "",
    ]
    (output / "FINAL_REPORT.md").write_text("\n".join(lines), encoding="utf-8")


def run_lab(input_path: Path, output: Path, cfg: Config, prepared: bool = False) -> dict[str, Any]:
    output.mkdir(parents=True, exist_ok=True)
    files = discover_chain_files(input_path)
    data = load_compact_data(files, cfg)
    coverage = coverage_summary(data, cfg)
    variants, gate = audit_suite(data, cfg)
    if not coverage["contiguous_pass"]:
        gate["primary_status"] = "INSUFFICIENT_CONTIGUOUS_OPTIONS_DATA"
        gate["overall_status"] = "INSUFFICIENT_CONTIGUOUS_OPTIONS_DATA"
        gate["tests"]["sufficient_contiguous_history"] = False
    gate["coverage"] = coverage
    for key, result in variants.items():
        save_result(output, key, result)
    rows = []
    for key, result in variants.items():
        rows.append({"variant": key, "status": result.status, **result.metrics})
    summary = pd.DataFrame(rows)
    summary.to_csv(output / "strategy_summary.csv", index=False, float_format="%.12g")
    write_json(output / "CONFIG.json", asdict(cfg))
    write_json(output / "DATA_COVERAGE.json", coverage)
    write_json(output / "FINAL_GATE.json", gate)
    input_rows = [{"path": str(path), "size": path.stat().st_size, "sha256": sha256_file(path)} for path in files]
    write_json(output / "INPUT_MANIFEST.json", {"input": input_path, "prepared": prepared, "files": input_rows})
    make_report(output, gate, summary, coverage)
    manifest = output_manifest(output, exclude={"OUTPUT_MANIFEST.json"})
    write_json(output / "OUTPUT_MANIFEST.json", manifest)
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
        if not path.exists():
            failures.append(f"missing:{item['path']}")
        elif path.stat().st_size != item["size"]:
            failures.append(f"size:{item['path']}")
        elif sha256_file(path) != item["sha256"]:
            failures.append(f"sha256:{item['path']}")
    ledgers = sorted(output.glob("*_exact_ledger.csv.gz"))
    if not ledgers:
        failures.append("no_ledgers")
    for path in ledgers:
        ledger = pd.read_csv(path, compression="gzip")
        failures.extend(f"{path.name}:{x}" for x in verify_ledger(ledger))
    gate_path = output / "FINAL_GATE.json"
    if not gate_path.exists():
        failures.append("missing_final_gate")
    result = {"version": VERSION, "passed": not failures, "failures": failures, "ledger_count": len(ledgers), "tree_sha256": manifest.get("tree_sha256")}
    if failures:
        raise RuntimeError(json.dumps(result, indent=2))
    return result


def build_handoff(root: Path, output: Path, destination: Path) -> dict[str, Any]:
    verification = verify_results(output)
    deterministic_zip(root, destination, include_results=True)
    return {"path": destination, "size": destination.stat().st_size, "sha256": sha256_file(destination), "verification": verification}


def try_auto_download(root: Path) -> Path:
    from v27_tardis import download_configured_history
    destination = root / "data/v27_tardis"
    download_configured_history(destination)
    return destination


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="V27 Deribit Long Gamma")
    sub = parser.add_subparsers(dest="command", required=True)
    prep = sub.add_parser("prepare")
    prep.add_argument("--input", type=Path, required=True)
    prep.add_argument("--output", type=Path, default=Path("data/v27_compact"))
    for name in ("run", "all"):
        p = sub.add_parser(name)
        p.add_argument("--input", type=Path)
        p.add_argument("--output", type=Path, default=Path("v27_results"))
        p.add_argument("--compact", type=Path, default=Path("data/v27_compact"))
        p.add_argument("--handoff", type=Path, default=Path("runtime/V27_Deribit_Long_Gamma_Handoff.zip"))
        p.add_argument("--auto-download", action=argparse.BooleanOptionalAction, default=True)
    verify = sub.add_parser("verify")
    verify.add_argument("--output", type=Path, default=Path("v27_results"))
    handoff = sub.add_parser("handoff")
    handoff.add_argument("--output", type=Path, default=Path("v27_results"))
    handoff.add_argument("--destination", type=Path, default=Path("runtime/V27_Deribit_Long_Gamma_Handoff.zip"))
    parser.add_argument("--currency", default="BTC")
    parser.add_argument("--snapshot-minutes", type=int, default=30)
    parser.add_argument("--initial-equity", type=float, default=100000.0)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = project_root()
    cfg = config_from_env(args)
    if args.command == "prepare":
        output = args.output if args.output.is_absolute() else root / args.output
        print(json.dumps(prepare_data(args.input, output, cfg), default=json_default, indent=2))
        return 0
    if args.command in {"run", "all"}:
        output = args.output if args.output.is_absolute() else root / args.output
        if output.exists():
            shutil.rmtree(output)
        try:
            source = resolve_input(root, args.input)
        except FileNotFoundError:
            if not args.auto_download:
                raise
            source = try_auto_download(root)
        compact = args.compact if args.compact.is_absolute() else root / args.compact
        source_files = discover_chain_files(source)
        already_compact = bool(source_files) and all(".compact." in p.name for p in source_files)
        if not already_compact:
            prepare_data(source, compact, cfg)
            source = compact
        gate = run_lab(source, output, cfg, prepared=True)
        print(json.dumps(gate, default=json_default, indent=2))
        if args.command == "all":
            verification = verify_results(output)
            destination = args.handoff if args.handoff.is_absolute() else root / args.handoff
            handoff = build_handoff(root, output, destination)
            print(json.dumps({"verification": verification, "handoff": handoff}, default=json_default, indent=2))
        return 0
    if args.command == "verify":
        output = args.output if args.output.is_absolute() else root / args.output
        print(json.dumps(verify_results(output), indent=2))
        return 0
    if args.command == "handoff":
        output = args.output if args.output.is_absolute() else root / args.output
        destination = args.destination if args.destination.is_absolute() else root / args.destination
        print(json.dumps(build_handoff(root, output, destination), default=json_default, indent=2))
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())

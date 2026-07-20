#!/usr/bin/env python3
"""Compatibility wrapper for the original V24 CLI without optional tabulate.

The original implementation is retained byte-for-byte in ``v24_cli_legacy.py``.
This module re-exports it and replaces only the Markdown report renderer.  The
wrapper also propagates runtime monkeypatches of ``_make_final_report`` so the
final audited runner can provide its own report while all existing callers and
tests continue to use ``v24_cli.run_lab``.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

import v24_cli_legacy as _legacy


def _display(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if isinstance(value, float):
        return f"{value:.6g}"
    return str(value).replace("|", "\\|").replace("\n", " ")


def _markdown_table(frame: pd.DataFrame) -> str:
    columns = [str(c) for c in frame.columns]
    rows = [[_display(value) for value in row] for row in frame.itertuples(index=False, name=None)]
    widths = [len(column) for column in columns]
    for row in rows:
        widths = [max(width, len(value)) for width, value in zip(widths, row)]
    header = "| " + " | ".join(column.ljust(width) for column, width in zip(columns, widths)) + " |"
    separator = "| " + " | ".join("-" * width for width in widths) + " |"
    body = ["| " + " | ".join(value.ljust(width) for value, width in zip(row, widths)) + " |" for row in rows]
    return "\n".join([header, separator, *body])


def _make_final_report(path: Path, gate: dict[str, Any], summary: pd.DataFrame, feasibility: dict[str, Any], baseline: dict[str, Any]) -> None:
    lines = [
        "# V24 Portable Diversifier Overlay — Final Report",
        "",
        f"Protocol version: `{_legacy.VERSION}`",
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
        _markdown_table(summary),
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
        "Even a full historical pass is capped at `HISTORICAL_PORTABLE_OVERLAY_PARETO_PASS_NEEDS_NEW_OOS`. This report uses the deterministic built-in Markdown renderer and has no optional tabulate dependency.",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


for _name in dir(_legacy):
    if not _name.startswith("__") and _name not in {"run_lab", "main", "_make_final_report"}:
        globals()[_name] = getattr(_legacy, _name)


def run_lab(*args: Any, **kwargs: Any):
    _legacy._make_final_report = globals()["_make_final_report"]
    return _legacy.run_lab(*args, **kwargs)


def main(argv: list[str] | None = None) -> int:
    _legacy._make_final_report = globals()["_make_final_report"]
    return _legacy.main(argv)


if __name__ == "__main__":
    raise SystemExit(main())

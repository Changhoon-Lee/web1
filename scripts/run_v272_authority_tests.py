#!/usr/bin/env python3
"""Run every V27.2 authority test in a fresh Python interpreter.

Fresh-process isolation prevents module caches, environment patches, pandas
state, and retained synthetic DataFrames from influencing later tests. The
runner is deterministic and exits nonzero if any named authority test fails.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

TESTS = [
    *(f"tests.test_v272.V272Tests.test_{n:02d}_{name}" for n, name in [
        (1, "config_validates"),
        (2, "inverse_contract_pnl_identity"),
        (3, "inverse_short_profit_on_price_fall"),
        (4, "funding_sign"),
        (5, "canonicalization_preserves_perpetual"),
        (6, "free_snapshot_contains_actual_perpetual_fields"),
        (7, "per_timestamp_symbol_count"),
        (8, "paid_credentials_rejected"),
        (9, "perpetual_bid_ask_changes_final_equity"),
        (10, "actual_funding_changes_final_equity"),
        (11, "missing_funding_fails_continuity"),
        (12, "held_state_writer"),
        (13, "held_quote_gap_fails_gate"),
        (14, "ledger_identity"),
        (15, "audit_suite_contains_actual_data_gates"),
        (16, "complete_utc_intraday_gate"),
        (17, "partial_day_excluded"),
        (18, "sparse_intraday_fails"),
        (19, "deterministic_gzip"),
        (20, "network_failure_never_fills"),
        (21, "fail_closed_has_no_ledgers"),
        (22, "ready_true_end_to_end"),
        (23, "future_snapshot_does_not_change_past_file"),
        (24, "manifest_hash_changes"),
        (25, "public_methods_only"),
    ]),
    "tests.test_v272_wrapper.V272WrapperTests.test_26_pretrade_initial_equity_is_authoritative_baseline",
    "tests.test_v272_wrapper.V272WrapperTests.test_27_report_renderer_accepts_structured_metrics",
]


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    env = os.environ.copy()
    env["PYTHONPATH"] = str(root / "src") + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
    env.setdefault("PYTHONHASHSEED", "0")
    env.setdefault("OMP_NUM_THREADS", "1")
    env.setdefault("OPENBLAS_NUM_THREADS", "1")
    env.setdefault("MKL_NUM_THREADS", "1")
    failures: list[str] = []
    for index, test in enumerate(TESTS, start=1):
        print(f"[{index:02d}/{len(TESTS)}] {test}", flush=True)
        completed = subprocess.run(
            [sys.executable, "-m", "unittest", test, "-v"],
            cwd=root,
            env=env,
            text=True,
        )
        if completed.returncode != 0:
            failures.append(test)
    print(f"\nV27.2 authority tests: {len(TESTS) - len(failures)}/{len(TESTS)} passed")
    if failures:
        print("Failures:")
        for test in failures:
            print(f"- {test}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

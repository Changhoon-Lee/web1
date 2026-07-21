#!/usr/bin/env python3
"""Run every V27.2 authority test in a fresh Python interpreter.

Successful subprocess output is suppressed. A failure prints only its exact test
identifier and captured traceback, keeping CI diagnostics compact and complete.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

TESTS = [
    "tests.test_v272.V272Tests.test_01_config_validates",
    "tests.test_v272.V272Tests.test_02_inverse_contract_pnl_identity",
    "tests.test_v272.V272Tests.test_03_inverse_short_profit_on_price_fall",
    "tests.test_v272.V272Tests.test_04_funding_sign",
    "tests.test_v272.V272Tests.test_05_canonicalization_preserves_perpetual",
    "tests.test_v272.V272Tests.test_06_free_snapshot_contains_actual_perpetual_fields",
    "tests.test_v272.V272Tests.test_07_per_timestamp_symbol_count",
    "tests.test_v272.V272Tests.test_08_paid_credentials_rejected",
    "tests.test_v272.V272Tests.test_09_perpetual_bid_ask_changes_final_equity",
    "tests.test_v272.V272Tests.test_10_actual_funding_changes_final_equity",
    "tests.test_v272.V272Tests.test_11_missing_funding_fails_continuity",
    "tests.test_v272.V272Tests.test_12_held_state_writer",
    "tests.test_v272.V272Tests.test_13_held_quote_gap_fails_gate",
    "tests.test_v272.V272Tests.test_14_ledger_identity",
    "tests.test_v272.V272Tests.test_15_audit_suite_contains_actual_data_gates",
    "tests.test_v272.V272Tests.test_16_complete_utc_intraday_gate",
    "tests.test_v272.V272Tests.test_17_partial_day_excluded",
    "tests.test_v272.V272Tests.test_18_sparse_intraday_fails",
    "tests.test_v272.V272Tests.test_19_deterministic_gzip",
    "tests.test_v272.V272Tests.test_20_network_failure_never_fills",
    "tests.test_v272.V272Tests.test_21_fail_closed_has_no_ledgers",
    "tests.test_v272.V272Tests.test_22_ready_true_end_to_end",
    "tests.test_v272.V272Tests.test_23_future_snapshot_does_not_change_past_file",
    "tests.test_v272.V272Tests.test_24_manifest_hash_changes",
    "tests.test_v272.V272Tests.test_25_public_methods_only",
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
    results: list[dict[str, object]] = []
    for index, test in enumerate(TESTS, start=1):
        completed = subprocess.run(
            [sys.executable, "-m", "unittest", test, "-v"],
            cwd=root,
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        passed = completed.returncode == 0
        results.append({"index": index, "test": test, "passed": passed, "returncode": completed.returncode})
        print(f"[{index:02d}/{len(TESTS)}] {'PASS' if passed else 'FAIL'} {test}", flush=True)
        if not passed:
            print(completed.stdout, flush=True)
    failures = [row for row in results if not row["passed"]]
    Path("V272_AUTHORITY_RESULTS.json").write_text(json.dumps({"total": len(TESTS), "passed": len(TESTS) - len(failures), "failures": failures, "results": results}, indent=2) + "\n", encoding="utf-8")
    print(f"V27.2 authority tests: {len(TESTS) - len(failures)}/{len(TESTS)} passed")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())

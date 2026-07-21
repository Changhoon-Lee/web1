#!/usr/bin/env python3
"""Run V27.2 inverse accounting and V27.2.4 WebSocket authority tests.

Every test runs in a fresh Python interpreter. Any failure makes the runner
non-zero and is recorded in V2724_AUTHORITY_RESULTS.json.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

BASE_TESTS = [
    *(f"tests.test_v272.V272Tests.test_{index:02d}_{name}" for index, name in [
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

WS_TESTS = [
    *(f"tests.test_v2724_ws.V2724WebSocketTests.test_{index}_{name}" for index, name in [
        (41, "public_websocket_requires_no_credentials"),
        (42, "subscriptions_are_batched_at_500"),
        (43, "all_7_to_45_dte_symbols_are_subscribed"),
        (44, "ticker_update_preserves_exchange_timestamp"),
        (45, "cutoff_excludes_future_messages"),
        (46, "snapshot_freezes_all_symbols_at_one_cutoff"),
        (47, "missing_delta_blocks_entry"),
        (48, "held_symbol_missing_blocks_economic_gate"),
        (49, "disconnect_marks_data_gap"),
        (50, "reconnect_requires_full_resubscription"),
        (51, "snapshot_blocked_until_all_symbols_rehydrated"),
        (52, "instrument_listing_updates_universe"),
        (53, "expired_instrument_is_unsubscribed"),
        (54, "more_than_500_channels_uses_multiple_batches"),
        (55, "duplicate_and_out_of_order_messages_are_safe"),
        (56, "websocket_snapshot_is_byte_deterministic"),
        (57, "rest_ticker_polling_is_forbidden_in_continuous_mode"),
        (58, "ready_true_end_to_end_websocket_fixture"),
    ])
]

TESTS = BASE_TESTS + WS_TESTS


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    env = os.environ.copy()
    env["PYTHONPATH"] = str(root / "src") + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
    env.setdefault("PYTHONHASHSEED", "0")
    env.setdefault("OMP_NUM_THREADS", "1")
    env.setdefault("OPENBLAS_NUM_THREADS", "1")
    env.setdefault("MKL_NUM_THREADS", "1")
    results: list[dict[str, object]] = []
    for position, test in enumerate(TESTS, start=1):
        completed = subprocess.run(
            [sys.executable, "-m", "unittest", test, "-v"],
            cwd=root,
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        passed = completed.returncode == 0
        results.append({"position": position, "test": test, "passed": passed, "returncode": completed.returncode})
        print(f"[{position:02d}/{len(TESTS)}] {'PASS' if passed else 'FAIL'} {test}", flush=True)
        if not passed:
            print(completed.stdout, flush=True)
    failures = [row for row in results if not row["passed"]]
    payload = {"protocol": "27.2.4-websocket-authority", "total": len(TESTS), "passed": len(TESTS) - len(failures), "failures": failures, "results": results}
    (root / "V2724_AUTHORITY_RESULTS.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"V27.2.4 authority tests: {payload['passed']}/{payload['total']} passed")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())

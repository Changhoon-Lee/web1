#!/usr/bin/env python3
from __future__ import annotations

import gzip
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import pandas as pd

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import v27_free_open as free


class FakeRPC:
    def __init__(self, bad_quote: bool = False):
        self.bad_quote = bad_quote
        self.calls = []

    def __call__(self, method, params=None, timeout=20):
        self.calls.append((method, params, timeout))
        if method == "get_index_price":
            return {"index_price": 100000.0}
        if method == "get_instruments":
            expiry = int(pd.Timestamp("2026-08-20T08:00:00Z").timestamp() * 1000)
            return [
                {"instrument_name": "BTC-20AUG26-100000-C", "expiration_timestamp": expiry, "strike": 100000.0, "option_type": "call"},
                {"instrument_name": "BTC-20AUG26-100000-P", "expiration_timestamp": expiry, "strike": 100000.0, "option_type": "put"},
                {"instrument_name": "BTC-20AUG26-105000-C", "expiration_timestamp": expiry, "strike": 105000.0, "option_type": "call"},
                {"instrument_name": "BTC-20AUG26-105000-P", "expiration_timestamp": expiry, "strike": 105000.0, "option_type": "put"},
            ]
        if method == "ticker":
            option_type = "call" if params["instrument_name"].endswith("-C") else "put"
            return {
                "best_bid_price": 0.04,
                "best_ask_price": 0.039 if self.bad_quote else 0.041,
                "best_bid_amount": 2.0,
                "best_ask_amount": 3.0,
                "mark_price": 0.0405,
                "mark_iv": 55.0,
                "bid_iv": 54.5,
                "ask_iv": 55.5,
                "underlying_price": 100100.0,
                "open_interest": 100.0,
                "greeks": {"delta": 0.5 if option_type == "call" else -0.5, "gamma": 0.0001, "vega": 12.0, "theta": -30.0},
            }
        raise AssertionError(method)


class V27FreeOpenTests(unittest.TestCase):
    def setUp(self):
        self.cfg = free.FreeConfig(record_minutes=0)
        self.now = pd.Timestamp("2026-07-21T08:00:00Z")

    def test_01_config_valid(self):
        self.cfg.validate()

    def test_02_config_rejects_short_interval(self):
        with self.assertRaises(ValueError):
            free.FreeConfig(interval_seconds=10).validate()

    def test_03_config_rejects_invalid_currency(self):
        with self.assertRaises(ValueError):
            free.FreeConfig(currency="SOL").validate()

    def test_04_choose_pair_is_atm_and_common_expiry(self):
        rpc = FakeRPC()
        instruments = rpc("get_instruments", {}, 20)
        call, put = free.choose_pair(instruments, 100000.0, self.now, self.cfg)
        self.assertEqual(call["strike"], 100000.0)
        self.assertEqual(put["strike"], 100000.0)
        self.assertTrue(call["instrument_name"].endswith("-C"))
        self.assertTrue(put["instrument_name"].endswith("-P"))

    def test_05_fetch_snapshot_has_call_and_put(self):
        frame = free.fetch_snapshot(self.cfg, rpc=FakeRPC(), now=self.now)
        self.assertEqual(len(frame), 2)
        self.assertEqual(set(frame["type"]), {"call", "put"})
        self.assertEqual(list(frame.columns), free.COLUMNS)

    def test_06_fetch_snapshot_rejects_crossed_quote(self):
        with self.assertRaises(RuntimeError):
            free.fetch_snapshot(self.cfg, rpc=FakeRPC(bad_quote=True), now=self.now)

    def test_07_snapshot_uses_only_public_methods(self):
        rpc = FakeRPC()
        free.fetch_snapshot(self.cfg, rpc=rpc, now=self.now)
        self.assertTrue(all(method in {"get_index_price", "get_instruments", "ticker"} for method, _, _ in rpc.calls))

    def test_08_paid_credentials_are_rejected(self):
        with mock.patch.dict(os.environ, {"TARDIS_API_KEY": "forbidden"}, clear=False):
            with self.assertRaises(RuntimeError):
                free.public_rpc("get_index_price", {"index_name": "btc_usd"}, 1)

    def test_09_append_snapshot_deduplicates(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            frame = free.fetch_snapshot(self.cfg, rpc=FakeRPC(), now=self.now)
            path = free.append_snapshot(frame, root)
            free.append_snapshot(frame, root)
            loaded = pd.read_csv(path, compression="gzip")
            self.assertEqual(len(loaded), 2)

    def test_10_gzip_is_deterministic(self):
        frame = free.fetch_snapshot(self.cfg, rpc=FakeRPC(), now=self.now)
        with tempfile.TemporaryDirectory() as tmp:
            a, b = Path(tmp) / "a.gz", Path(tmp) / "b.gz"
            free.deterministic_gzip_csv(frame, a)
            free.deterministic_gzip_csv(frame, b)
            self.assertEqual(a.read_bytes(), b.read_bytes())

    def test_11_empty_coverage_blocks(self):
        coverage = free.free_coverage(pd.DataFrame(columns=free.COLUMNS), self.cfg)
        self.assertFalse(coverage["ready"])
        self.assertEqual(coverage["active_days"], 0)

    def test_12_sparse_monthly_coverage_blocks(self):
        rows = []
        for month in range(1, 9):
            ts = pd.Timestamp(year=2026, month=month, day=1, tz="UTC")
            rows.append({"timestamp": ts})
        coverage = free.free_coverage(pd.DataFrame(rows), self.cfg)
        self.assertFalse(coverage["ready"])
        self.assertGreater(coverage["maximum_gap_hours"], 48)

    def test_13_ninety_contiguous_days_pass(self):
        timestamps = pd.date_range("2026-01-01", periods=91, freq="D", tz="UTC")
        coverage = free.free_coverage(pd.DataFrame({"timestamp": timestamps}), self.cfg)
        self.assertTrue(coverage["ready"])

    def test_14_coverage_requires_active_days_not_just_span(self):
        timestamps = pd.DatetimeIndex([pd.Timestamp("2026-01-01", tz="UTC"), pd.Timestamp("2026-04-15", tz="UTC")])
        coverage = free.free_coverage(pd.DataFrame({"timestamp": timestamps}), self.cfg)
        self.assertFalse(coverage["ready"])

    def test_15_manifest_records_official_public_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            manifest = free.input_manifest(Path(tmp))
            self.assertEqual(manifest["source"], "Deribit public JSON-RPC API")
            self.assertEqual(manifest["authentication"], "none")
            self.assertEqual(manifest["historical_backfill"], "forbidden")

    def test_16_manifest_hash_changes_with_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            frame = free.fetch_snapshot(self.cfg, rpc=FakeRPC(), now=self.now)
            free.append_snapshot(frame, root)
            first = free.input_manifest(root)["tree_sha256"]
            frame2 = free.fetch_snapshot(self.cfg, rpc=FakeRPC(), now=self.now + pd.Timedelta(minutes=5))
            free.append_snapshot(frame2, root)
            second = free.input_manifest(root)["tree_sha256"]
            self.assertNotEqual(first, second)

    def test_17_record_writes_error_log_and_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = free.record(Path(tmp), self.cfg, rpc=FakeRPC())
            self.assertEqual(result["captured_snapshots"], 1)
            self.assertTrue((Path(tmp) / "RECORDER_ERRORS.log").exists())
            self.assertTrue((Path(tmp) / "FREE_INPUT_MANIFEST.json").exists())
            self.assertTrue((Path(tmp) / "FREE_COVERAGE.json").exists())

    def test_18_record_network_failure_never_fills_data(self):
        def bad_rpc(*args, **kwargs):
            raise OSError("offline")
        with tempfile.TemporaryDirectory() as tmp:
            result = free.record(Path(tmp), self.cfg, rpc=bad_rpc)
            self.assertEqual(result["captured_snapshots"], 0)
            self.assertEqual(len(free.discover_free_files(Path(tmp))), 0)
            self.assertIn("offline", (Path(tmp) / "RECORDER_ERRORS.log").read_text())

    def test_19_fail_closed_report_has_no_economic_metrics(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data = root / "data"
            output = root / "results"
            data.mkdir()
            coverage = free.free_coverage(pd.DataFrame(columns=free.COLUMNS), self.cfg)
            gate = free.fail_closed_results(root, data, self.cfg, coverage, output)
            self.assertFalse(gate["economic_metrics_allowed"])
            self.assertEqual(gate["overall_status"], "FREE_OPEN_DATA_CONTINUITY_NOT_READY")
            report = (output / "FINAL_REPORT.md").read_text()
            self.assertIn("No Sharpe, CAGR", report)

    def test_20_run_free_only_creates_handoff_when_not_ready(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            data = project / "data/v27_free_chain"
            output = project / "v27_free_results"
            handoff = project / "runtime/handoff.zip"
            data.mkdir(parents=True)
            result = free.run_free_only(project, self.cfg, data, output, handoff, do_record=False)
            self.assertEqual(result["gate"]["overall_status"], "FREE_OPEN_DATA_CONTINUITY_NOT_READY")
            self.assertTrue(handoff.exists())

    def test_21_future_snapshot_does_not_change_past_file_bytes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            first = free.fetch_snapshot(self.cfg, rpc=FakeRPC(), now=self.now)
            path = free.append_snapshot(first, root)
            before = path.read_bytes()
            future = free.fetch_snapshot(self.cfg, rpc=FakeRPC(), now=self.now + pd.Timedelta(days=1))
            free.append_snapshot(future, root)
            self.assertEqual(before, path.read_bytes())

    def test_22_no_private_deribit_credentials_required(self):
        self.assertIn("DERIBIT_CLIENT_ID", free.FORBIDDEN_ENV_VARS)
        self.assertIn("DERIBIT_CLIENT_SECRET", free.FORBIDDEN_ENV_VARS)

    def test_23_timestamps_are_utc(self):
        frame = free.fetch_snapshot(self.cfg, rpc=FakeRPC(), now=self.now)
        parsed = pd.to_datetime(frame["timestamp"], utc=True)
        self.assertTrue(all(x.tzinfo is not None for x in parsed))

    def test_24_quote_rows_preserve_executable_bid_ask(self):
        frame = free.fetch_snapshot(self.cfg, rpc=FakeRPC(), now=self.now)
        self.assertTrue((frame["ask_price"] >= frame["bid_price"]).all())
        self.assertTrue((frame["ask_price"] > 0).all())


if __name__ == "__main__":
    unittest.main()

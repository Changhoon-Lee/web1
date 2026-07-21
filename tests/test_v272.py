#!/usr/bin/env python3
from __future__ import annotations

import json
import math
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest import mock

import numpy as np
import pandas as pd

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import v272_core as core
import v272_free as free
import v272_cli as cli


def synthetic_market(
    days: int = 3,
    perp_spread: float = 2.0,
    funding_8h: float = 0.0002,
    missing_option_after: int | None = None,
) -> pd.DataFrame:
    timestamps = pd.date_range("2026-01-01T00:00:00Z", periods=days * 24 * 12, freq="5min")
    expiry = pd.Timestamp("2026-01-06T00:00:00Z")
    rows = []
    for i, ts in enumerate(timestamps):
        index = 100_000.0 * math.exp(0.00002 * i + 0.01 * math.sin(i / 20.0))
        mark = index * (1.0 + 0.0001 * math.sin(i / 7.0))
        rows.append({
            "timestamp": ts, "symbol": "BTC-PERPETUAL", "type": "perpetual",
            "strike_price": 0.0, "expiration": "", "bid_price": mark - perp_spread / 2,
            "ask_price": mark + perp_spread / 2, "mark_price": mark,
            "underlying_price": index, "index_price": index,
            "funding_8h": funding_8h, "current_funding": funding_8h,
            "contract_size_usd": 10.0,
        })
        if missing_option_after is not None and i >= missing_option_after:
            continue
        for option_type, code, delta in (("call", "C", 0.60), ("put", "P", -0.40)):
            intrinsic = max(index - 100000.0, 0.0) if option_type == "call" else max(100000.0 - index, 0.0)
            time_value = max((expiry - ts).total_seconds() / 86400.0, 0.0) * 0.004 * index
            premium_btc = (intrinsic + time_value + 1500.0) / index
            rows.append({
                "timestamp": ts, "symbol": f"BTC-6JAN26-100000-{code}", "type": option_type,
                "strike_price": 100000.0, "expiration": expiry,
                "bid_price": max(premium_btc - 0.0002, 0.0001), "ask_price": premium_btc + 0.0002,
                "mark_price": premium_btc, "mark_iv": 60.0,
                "underlying_price": index, "index_price": index,
                "delta": delta, "gamma": 0.00001, "vega": 1.0, "theta": -1.0,
            })
    return pd.DataFrame(rows)


def test_config() -> core.Config:
    return core.Config(
        snapshot_minutes=5, target_dte=3.0, minimum_dte=1.0, maximum_dte=6.0,
        exit_dte=0.25, roll_days=1, entry_hour_utc=0, maximum_quote_age_minutes=10,
        minimum_backtest_days=1, minimum_rolls=1, minimum_held_quote_coverage=0.90,
        minimum_perp_quote_coverage=0.99, minimum_funding_coverage=0.99,
    )


class FakeRPC:
    def __init__(self, perp_bid: float = 99990.0, funding: float = 0.0002):
        self.perp_bid = perp_bid
        self.funding = funding
        self.calls = []

    def __call__(self, method, params=None, timeout=20):
        self.calls.append((method, params, timeout))
        if method == "get_index_price":
            return {"index_price": 100000.0}
        if method == "get_instruments":
            expiry = int(pd.Timestamp("2026-08-20T08:00:00Z").timestamp() * 1000)
            return [
                {"instrument_name": f"BTC-20AUG26-{strike}-{code}", "expiration_timestamp": expiry, "strike": float(strike), "option_type": otype}
                for strike in (95000, 100000, 105000)
                for otype, code in (("call", "C"), ("put", "P"))
            ]
        if method == "ticker" and params["instrument_name"] == "BTC-PERPETUAL":
            return {
                "best_bid_price": self.perp_bid, "best_ask_price": self.perp_bid + 2.0,
                "mark_price": self.perp_bid + 1.0, "index_price": 100000.0,
                "funding_8h": self.funding, "current_funding": self.funding,
                "open_interest": 1_000_000,
            }
        if method == "ticker":
            is_call = params["instrument_name"].endswith("-C")
            return {
                "best_bid_price": 0.04, "best_ask_price": 0.041,
                "best_bid_amount": 2.0, "best_ask_amount": 3.0,
                "mark_price": 0.0405, "mark_iv": 55.0, "bid_iv": 54.0, "ask_iv": 56.0,
                "underlying_price": 100000.0, "open_interest": 100.0,
                "greeks": {"delta": 0.55 if is_call else -0.45, "gamma": 0.0001, "vega": 1.0, "theta": -1.0},
            }
        raise AssertionError(method)


class V272Tests(unittest.TestCase):
    def test_01_config_validates(self):
        core.Config().validate()

    def test_02_inverse_contract_pnl_identity(self):
        notional, p0, p1 = 100000.0, 100000.0, 110000.0
        btc = core.inverse_pnl_btc(notional, p0, p1)
        self.assertAlmostEqual(btc, notional * (1 / p0 - 1 / p1), places=14)
        self.assertAlmostEqual(btc * p1, notional * (p1 / p0 - 1), places=8)

    def test_03_inverse_short_profit_on_price_fall(self):
        self.assertGreater(core.inverse_pnl_btc(-100000.0, 100000.0, 90000.0), 0)

    def test_04_funding_sign(self):
        long_cash = core.funding_payment_btc(100000.0, 100000.0, 0.001, 8 * 3600)
        short_cash = core.funding_payment_btc(-100000.0, 100000.0, 0.001, 8 * 3600)
        self.assertAlmostEqual(long_cash, -0.001)
        self.assertAlmostEqual(short_cash, 0.001)

    def test_05_canonicalization_preserves_perpetual(self):
        data = core.canonicalize_market(synthetic_market(days=1), test_config())
        self.assertIn("perpetual", set(data["type"]))
        self.assertTrue(data[data["type"] == "perpetual"]["funding_8h"].notna().all())

    def test_06_free_snapshot_contains_actual_perpetual_fields(self):
        frame = free.fetch_snapshot(free.FreeConfig(record_minutes=0), rpc=FakeRPC(), now=pd.Timestamp("2026-07-21T08:00:00Z"))
        perp = frame[frame["type"] == "perpetual"].iloc[0]
        self.assertEqual(perp["symbol"], "BTC-PERPETUAL")
        self.assertAlmostEqual(perp["funding_8h"], 0.0002)
        self.assertAlmostEqual(perp["contract_size_usd"], 10.0)

    def test_07_per_timestamp_symbol_count(self):
        frame = free.fetch_snapshot(free.FreeConfig(record_minutes=0), rpc=FakeRPC(), now=pd.Timestamp("2026-07-21T08:00:00Z"))
        self.assertEqual(frame["timestamp"].nunique(), 1)
        self.assertEqual(len(frame[frame["type"] == "perpetual"]), 1)
        self.assertGreaterEqual(len(frame[frame["type"].isin(["call", "put"])]), 6)

    def test_08_paid_credentials_rejected(self):
        with mock.patch.dict("os.environ", {"TARDIS_API_KEY": "x"}, clear=False):
            with self.assertRaises(RuntimeError):
                free.public_rpc("get_index_price", {"index_name": "btc_usd"}, 1)

    def test_09_perpetual_bid_ask_changes_final_equity(self):
        cfg = test_config()
        tight = core.canonicalize_market(synthetic_market(perp_spread=1.0), cfg)
        wide = core.canonicalize_market(synthetic_market(perp_spread=100.0), cfg)
        a = core.run_long_gamma(tight, cfg)
        b = core.run_long_gamma(wide, cfg)
        self.assertNotAlmostEqual(a.metrics["final_equity"], b.metrics["final_equity"], places=4)
        self.assertGreater(b.metrics["total_perp_fees_usd"] + abs(b.metrics["total_perp_pnl_usd"]), 0)

    def test_10_actual_funding_changes_final_equity(self):
        cfg = test_config()
        zero = core.run_long_gamma(core.canonicalize_market(synthetic_market(funding_8h=0.0), cfg), cfg)
        high = core.run_long_gamma(core.canonicalize_market(synthetic_market(funding_8h=0.01), cfg), cfg)
        self.assertNotAlmostEqual(zero.metrics["final_equity"], high.metrics["final_equity"], places=4)
        self.assertNotEqual(high.metrics["total_funding_usd"], 0.0)

    def test_11_missing_funding_fails_continuity(self):
        cfg = test_config()
        frame = synthetic_market()
        frame.loc[frame["type"] == "perpetual", "funding_8h"] = np.nan
        result = core.run_long_gamma(core.canonicalize_market(frame, cfg), cfg)
        self.assertEqual(result.status, "MARKET_DATA_CONTINUITY_GATE_FAILED")

    def test_12_held_state_writer(self):
        cfg = test_config()
        data = core.canonicalize_market(synthetic_market(days=2), cfg)
        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp) / "HELD_OPTION_STATE.json"
            core.run_long_gamma(data, cfg, held_state_file=state)
            self.assertTrue(state.exists())
            payload = json.loads(state.read_text())
            self.assertIn("held_symbols", payload)
            self.assertEqual(payload["version"], core.VERSION)

    def test_13_held_quote_gap_fails_gate(self):
        cfg = replace(test_config(), minimum_held_quote_coverage=0.99)
        frame = synthetic_market(days=3, missing_option_after=100)
        result = core.run_long_gamma(core.canonicalize_market(frame, cfg), cfg)
        self.assertLess(result.metrics["held_option_quote_coverage"], 0.99)
        self.assertEqual(result.status, "MARKET_DATA_CONTINUITY_GATE_FAILED")

    def test_14_ledger_identity(self):
        cfg = test_config()
        result = core.run_long_gamma(core.canonicalize_market(synthetic_market(), cfg), cfg)
        self.assertEqual(core.verify_ledger(result.ledger), [])

    def test_15_audit_suite_contains_actual_data_gates(self):
        cfg = test_config()
        _, gate = core.audit_suite(core.canonicalize_market(synthetic_market(), cfg), cfg)
        self.assertIn("perpetual_quote_coverage", gate["tests"])
        self.assertIn("actual_funding_coverage", gate["tests"])
        self.assertIn("held_quote_coverage", gate["tests"])

    def test_16_complete_utc_intraday_gate(self):
        cfg = replace(free.FreeConfig(), minimum_active_days=2)
        ts = pd.date_range("2026-01-01", periods=3 * 288, freq="5min", tz="UTC")
        coverage = free.free_coverage(pd.DataFrame({"timestamp": ts}), cfg)
        self.assertTrue(coverage["ready"])
        self.assertTrue(coverage["intraday_gate"]["ready"])

    def test_17_partial_day_excluded(self):
        cfg = replace(free.FreeConfig(), minimum_active_days=2)
        complete = pd.date_range("2026-01-01", periods=2 * 288, freq="5min", tz="UTC")
        partial = pd.date_range("2026-01-03", periods=12, freq="5min", tz="UTC")
        coverage = free.free_coverage(pd.DataFrame({"timestamp": complete.append(partial)}), cfg)
        self.assertGreater(coverage["intraday_gate"]["density_p10"], 0.99)

    def test_18_sparse_intraday_fails(self):
        cfg = replace(free.FreeConfig(), minimum_active_days=2)
        ts = pd.date_range("2026-01-01", periods=3, freq="D", tz="UTC")
        self.assertFalse(free.free_coverage(pd.DataFrame({"timestamp": ts}), cfg)["ready"])

    def test_19_deterministic_gzip(self):
        frame = free.fetch_snapshot(free.FreeConfig(record_minutes=0), rpc=FakeRPC(), now=pd.Timestamp("2026-07-21T08:00:00Z"))
        with tempfile.TemporaryDirectory() as tmp:
            a, b = Path(tmp) / "a.gz", Path(tmp) / "b.gz"
            free.deterministic_gzip_csv(frame, a)
            free.deterministic_gzip_csv(frame, b)
            self.assertEqual(a.read_bytes(), b.read_bytes())

    def test_20_network_failure_never_fills(self):
        def bad(*args, **kwargs):
            raise OSError("offline")
        with tempfile.TemporaryDirectory() as tmp:
            result = free.record(Path(tmp), free.FreeConfig(record_minutes=0), rpc=bad)
            self.assertEqual(result["captured_snapshots"], 0)
            self.assertEqual(free.discover_files(Path(tmp)), [])

    def test_21_fail_closed_has_no_ledgers(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data, output = root / "data", root / "out"
            data.mkdir()
            coverage = free.free_coverage(pd.DataFrame(), free.FreeConfig())
            gate = cli.fail_closed(output, data, free.FreeConfig(), coverage)
            self.assertFalse(gate["economic_metrics_allowed"])
            self.assertFalse(list(output.glob("*_exact_ledger.csv.gz")))
            self.assertTrue(cli.verify(output)["passed"])

    def test_22_ready_true_end_to_end(self):
        cfg = test_config()
        free_cfg = replace(free.FreeConfig(), minimum_active_days=1)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data_root, output = root / "data", root / "out"
            data_root.mkdir()
            market = synthetic_market(days=3)
            market.to_csv(data_root / "synthetic.free.compact.csv.gz", index=False, compression={"method": "gzip", "mtime": 0})
            coverage = {"ready": True, "active_days": 3, "intraday_gate": {"ready": True}}
            gate = cli.run_economic(data_root, output, cfg, free_cfg, coverage, data_root / "HELD_OPTION_STATE.json")
            self.assertTrue((output / "FINAL_GATE.json").exists())
            self.assertTrue(list(output.glob("*_exact_ledger.csv.gz")))
            self.assertTrue(cli.verify(output)["passed"])
            self.assertIn(gate["overall_status"], {"HISTORICAL_DERIBIT_LONG_GAMMA_REJECTED", "HISTORICAL_DERIBIT_LONG_GAMMA_PASS_NEEDS_NEW_OOS", "MARKET_DATA_CONTINUITY_GATE_FAILED"})

    def test_23_future_snapshot_does_not_change_past_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cfg = free.FreeConfig(record_minutes=0)
            first = free.fetch_snapshot(cfg, rpc=FakeRPC(), now=pd.Timestamp("2026-07-21T08:00:00Z"))
            path = free.append_snapshot(first, root)
            before = path.read_bytes()
            second = free.fetch_snapshot(cfg, rpc=FakeRPC(), now=pd.Timestamp("2026-07-22T08:00:00Z"))
            free.append_snapshot(second, root)
            self.assertEqual(before, path.read_bytes())

    def test_24_manifest_hash_changes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cfg = free.FreeConfig(record_minutes=0)
            free.append_snapshot(free.fetch_snapshot(cfg, rpc=FakeRPC(), now=pd.Timestamp("2026-07-21T08:00:00Z")), root)
            first = free.input_manifest(root)["tree_sha256"]
            free.append_snapshot(free.fetch_snapshot(cfg, rpc=FakeRPC(), now=pd.Timestamp("2026-07-21T08:05:00Z")), root)
            self.assertNotEqual(first, free.input_manifest(root)["tree_sha256"])

    def test_25_public_methods_only(self):
        rpc = FakeRPC()
        free.fetch_snapshot(free.FreeConfig(record_minutes=0), rpc=rpc, now=pd.Timestamp("2026-07-21T08:00:00Z"))
        self.assertTrue(all(method in {"get_index_price", "get_instruments", "ticker"} for method, _, _ in rpc.calls))


if __name__ == "__main__":
    unittest.main()

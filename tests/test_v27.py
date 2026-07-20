#!/usr/bin/env python3
from __future__ import annotations

import json
import math
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

import numpy as np
import pandas as pd

import v27_cli as cli
import v27_core as core
import v27_live_recorder as recorder
import v27_tardis as tardis


def synthetic_chain(days: int = 70) -> pd.DataFrame:
    start = pd.Timestamp("2024-01-01 08:00:00", tz="UTC")
    timestamps = pd.date_range(start, periods=days * 4, freq="6h")
    expiries = [pd.Timestamp("2024-01-26 08:00:00", tz="UTC"), pd.Timestamp("2024-02-23 08:00:00", tz="UTC"), pd.Timestamp("2024-03-29 08:00:00", tz="UTC"), pd.Timestamp("2024-04-26 08:00:00", tz="UTC")]
    rows = []
    for i, ts in enumerate(timestamps):
        spot = 10_000.0 * math.exp(0.00025 * i + 0.035 * math.sin(i / 4.0))
        for expiry in expiries:
            dte = (expiry - ts).total_seconds() / 86400.0
            if not 4 <= dte <= 50:
                continue
            years = max(dte / 365.25, 1e-8)
            for strike in (9000.0, 10000.0, 11000.0, 12000.0):
                for option_type, code in (("call", "C"), ("put", "P")):
                    usd, delta, gamma = core.black_scholes_usd(spot, strike, years, 0.75, 0.0, option_type)
                    premium = usd / spot
                    spread = max(premium * 0.04, 0.0001)
                    rows.append({
                        "exchange": "deribit",
                        "symbol": f"BTC-{expiry:%d%b%y}-{int(strike)}-{code}".upper(),
                        "timestamp": int(ts.timestamp() * 1_000_000),
                        "local_timestamp": int(ts.timestamp() * 1_000_000) + 100,
                        "type": option_type,
                        "strike_price": strike,
                        "expiration": int(expiry.timestamp() * 1_000_000),
                        "open_interest": 100.0,
                        "last_price": premium,
                        "bid_price": max(premium - spread / 2.0, 0.00001),
                        "bid_amount": 10.0,
                        "bid_iv": 74.0,
                        "ask_price": premium + spread / 2.0,
                        "ask_amount": 10.0,
                        "ask_iv": 76.0,
                        "mark_price": premium,
                        "mark_iv": 75.0,
                        "underlying_index": f"SYN.BTC-{expiry:%d%b%y}".upper(),
                        "underlying_price": spot,
                        "delta": delta,
                        "gamma": gamma,
                        "vega": 1.0,
                        "theta": -1.0,
                        "rho": 0.0,
                    })
    return pd.DataFrame(rows)


class V27Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.raw = synthetic_chain()
        cls.data = core.canonicalize_chain(cls.raw)
        cls.cfg = core.Config(
            snapshot_minutes=360,
            minimum_dte=15,
            target_dte=25,
            maximum_dte=40,
            exit_dte=4,
            roll_days=7,
            maximum_quote_age_minutes=400,
            maximum_hedge_minutes=360,
            minimum_backtest_days=10,
            minimum_rolls=1,
            premium_budget_fraction=0.08,
        )

    def test_01_config_valid(self):
        self.cfg.validate()

    def test_02_config_dte_order_rejected(self):
        with self.assertRaises(ValueError):
            replace(self.cfg, exit_dte=20).validate()

    def test_03_microsecond_timestamp(self):
        self.assertEqual(self.data.iloc[0]["timestamp"].year, 2024)

    def test_04_inverse_detected(self):
        self.assertEqual(set(self.data["settlement_type"]), {"inverse"})

    def test_05_linear_detected(self):
        frame = self.raw.iloc[:1].copy()
        frame["symbol"] = "BTC_USDC-26JAN24-10000-C"
        out = core.canonicalize_chain(frame)
        self.assertEqual(out.iloc[0]["settlement_type"], "linear")

    def test_06_put_call_parity(self):
        call, _, _ = core.black_scholes_usd(100, 100, 1, 0.2, 0.01, "call")
        put, _, _ = core.black_scholes_usd(100, 100, 1, 0.2, 0.01, "put")
        self.assertAlmostEqual(call - put, 100 - 100 * math.exp(-0.01), places=8)

    def test_07_delta_bounds(self):
        _, cd, _ = core.black_scholes_usd(100, 100, 1, 0.2, 0, "call")
        _, pd_, _ = core.black_scholes_usd(100, 100, 1, 0.2, 0, "put")
        self.assertTrue(0 < cd < 1 and -1 < pd_ < 0)

    def test_08_inverse_price_conversion(self):
        row = self.data.iloc[0]
        self.assertAlmostEqual(core.option_price_usd(row, 0.01), 0.01 * float(row["underlying_price"]))

    def test_09_inverse_fee_cap(self):
        row = self.data.iloc[0].copy()
        fee = core.option_fee_usd(row, 0.0001, 1.0, self.cfg)
        expected = min(0.0003, 0.125 * 0.0001) * float(row["underlying_price"])
        self.assertAlmostEqual(fee, expected)

    def test_10_linear_fee(self):
        row = self.data.iloc[0].copy()
        row["settlement_type"] = "linear"
        fee = core.option_fee_usd(row, 50.0, 1.0, self.cfg)
        self.assertAlmostEqual(fee, min(0.0003 * float(row["underlying_price"]), 6.25))

    def test_11_spread_fraction_positive(self):
        self.assertGreater(core.spread_fraction(self.data.iloc[0]), 0)

    def test_12_select_same_strike_pair(self):
        ts = self.data["timestamp"].iloc[0]
        selected = core.select_atm_straddle(self.data[self.data["timestamp"] == ts], self.cfg)
        self.assertIsNotNone(selected)
        self.assertTrue(selected["call_symbol"].endswith("-C"))
        self.assertTrue(selected["put_symbol"].endswith("-P"))

    def test_13_wide_spread_rejected(self):
        snap = self.data[self.data["timestamp"] == self.data["timestamp"].iloc[0]].copy()
        snap["ask_price"] = snap["bid_price"] * 10
        self.assertIsNone(core.select_atm_straddle(snap, self.cfg))

    def test_14_prepare_compact_file(self):
        with tempfile.TemporaryDirectory() as td:
            src = Path(td) / "OPTIONS.csv.gz"
            dst = Path(td) / "out.compact.csv.gz"
            self.raw.to_csv(src, index=False, compression={"method": "gzip", "mtime": 0})
            result = core.prepare_compact_file(src, dst, self.cfg)
            self.assertTrue(dst.exists())
            self.assertGreater(result["compact_rows"], 0)

    def test_15_discover_files(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "x_options_chain.csv.gz"
            p.write_bytes(b"x")
            self.assertEqual(core.discover_chain_files(Path(td)), [p.resolve()])

    def test_16_run_has_ledger(self):
        result = core.run_long_gamma(self.data, self.cfg)
        self.assertGreater(len(result.ledger), 0)

    def test_17_ledger_identity(self):
        result = core.run_long_gamma(self.data, self.cfg)
        self.assertEqual(core.verify_ledger(result.ledger), [])

    def test_18_option_trades_exist(self):
        result = core.run_long_gamma(self.data, self.cfg)
        self.assertIn("OPTION_OPEN", set(result.trades["kind"]))

    def test_19_hedge_trades_exist(self):
        result = core.run_long_gamma(self.data, self.cfg)
        self.assertIn("HEDGE", set(result.trades["kind"]))

    def test_20_unhedged_control_has_no_hedges(self):
        result = core.run_long_gamma(self.data, self.cfg, hedge_enabled=False)
        self.assertFalse(len(result.trades) and (result.trades["kind"] == "HEDGE").any())

    def test_21_cost_stress_monotonic(self):
        low = core.run_long_gamma(self.data, self.cfg, cost_multiplier=1.0)
        high = core.run_long_gamma(self.data, self.cfg, cost_multiplier=3.0)
        self.assertLessEqual(high.metrics["final_equity"], low.metrics["final_equity"] + 1e-8)

    def test_22_insufficient_short_sample(self):
        cutoff = self.data["timestamp"].min() + pd.Timedelta(days=2)
        result = core.run_long_gamma(self.data[self.data["timestamp"] <= cutoff], self.cfg)
        self.assertEqual(result.status, "INSUFFICIENT_HISTORICAL_OPTIONS_DATA")

    def test_23_future_perturbation(self):
        original = core.run_long_gamma(self.data, self.cfg)
        changed = self.data.copy()
        cutoff = changed["timestamp"].min() + pd.Timedelta(days=30)
        mask = changed["timestamp"] > cutoff
        changed.loc[mask, "underlying_price"] *= 1.7
        changed.loc[mask, ["bid_price", "ask_price", "mark_price"]] *= 1.2
        perturbed = core.run_long_gamma(changed, self.cfg)
        a = original.ledger[original.ledger["timestamp"] <= cutoff].reset_index(drop=True)
        b = perturbed.ledger[perturbed.ledger["timestamp"] <= cutoff].reset_index(drop=True)
        pd.testing.assert_frame_equal(a, b)

    def test_24_audit_suite_variants(self):
        variants, gate = core.audit_suite(self.data, self.cfg)
        self.assertEqual(set(variants), {"primary", "unhedged", "cost_2x", "cost_3x", "latency_2", "latency_3"})
        self.assertIn("overall_status", gate)

    def test_25_coverage_sparse_fails(self):
        sparse = self.data[self.data["timestamp"].dt.day == 1]
        coverage = cli.coverage_summary(sparse, self.cfg)
        self.assertFalse(coverage["contiguous_pass"])

    def test_26_manifest_deterministic(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "b").write_text("b")
            (root / "a").write_text("a")
            self.assertEqual(core.output_manifest(root), core.output_manifest(root))

    def test_27_zip_deterministic(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "root"
            root.mkdir()
            (root / "a").write_text("hello")
            z1, z2 = Path(td) / "1.zip", Path(td) / "2.zip"
            core.deterministic_zip(root, z1)
            core.deterministic_zip(root, z2)
            self.assertEqual(z1.read_bytes(), z2.read_bytes())

    def test_28_month_starts(self):
        dates = tardis._month_starts(pd.Timestamp("2024-01-01").date(), pd.Timestamp("2024-04-01").date())
        self.assertEqual([d.month for d in dates], [1, 2, 3])

    def test_29_normalize_live_ticker(self):
        instrument = {"instrument_name": "BTC-26JUL26-100000-C", "option_type": "call", "strike": 100000, "expiration_timestamp": 1785052800000}
        data = {"timestamp": 1785000000000, "best_bid_price": 0.01, "best_ask_price": 0.02, "underlying_price": 100000, "greeks": {"delta": 0.5}}
        row = recorder.normalize_ticker(data, instrument, 1)
        self.assertEqual(row["delta"], 0.5)

    def test_30_full_smoke_verify(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source = root / "synthetic.compact.csv.gz"
            self.data.to_csv(source, index=False, compression={"method": "gzip", "mtime": 0})
            output = root / "results"
            gate = cli.run_lab(source, output, self.cfg, prepared=True)
            self.assertIn("overall_status", gate)
            self.assertTrue(cli.verify_results(output)["passed"])


if __name__ == "__main__":
    unittest.main(verbosity=2)

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

import v24_core as core
import v24_cli as cli


class V24Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        rng = np.random.default_rng(20260719)
        idx = pd.date_range("2020-01-01", periods=1200, freq="D", tz="UTC")
        common = rng.normal(0.0003, 0.009, len(idx))
        equity = 0.00022 + 0.18 * common + rng.normal(0, 0.005, len(idx))
        gold = 0.00015 - 0.08 * common + rng.normal(0, 0.004, len(idx))
        v10 = 0.00065 + common
        growth = 0.00060 + common + rng.normal(0, 0.001, len(idx))
        cash = np.full(len(idx), 0.04 / core.ANNUALIZATION)
        cls.data = pd.DataFrame({
            "GROWTH_CRYPTO": growth,
            "EQUITY_TREND": equity,
            "GOLD_TREND": gold,
            "V10": v10,
            "CASH": cash,
        }, index=idx)
        cls.data.index.name = "date"
        cls.cfg = core.Config(warmup_days=300, bootstrap_samples=30, up_confirm_days=3)

    # 01
    def test_01_normalize_string_date(self):
        f = pd.DataFrame({"date": ["2024-01-02"], "x": [1]})
        out = core.normalize_date_frame(f)
        self.assertEqual(out.index[0].day, 2)

    # 02
    def test_02_normalize_unix_ms(self):
        f = pd.DataFrame({"timestamp": [1704153600000], "x": [1]})
        out = core.normalize_date_frame(f)
        self.assertEqual(out.index[0].year, 2024)

    # 03
    def test_03_duplicate_date_keeps_last(self):
        f = pd.DataFrame({"date": ["2024-01-01", "2024-01-01"], "x": [1, 2]})
        out = core.normalize_date_frame(f)
        self.assertEqual(int(out.iloc[0]["x"]), 2)

    # 04
    def test_04_missing_date_rejected(self):
        with self.assertRaises(ValueError):
            core.normalize_date_frame(pd.DataFrame({"x": [1]}))

    # 05
    def test_05_config_static_overlay_sum(self):
        self.cfg.validate()
        self.assertAlmostEqual(self.cfg.static_equity_overlay + self.cfg.static_gold_overlay, 0.60)

    # 06
    def test_06_config_rejects_gross_above_cap(self):
        with self.assertRaises(ValueError):
            replace(self.cfg, max_overlay=0.61, static_equity_overlay=0.305, static_gold_overlay=0.305).validate()

    # 07
    def test_07_bounded_simplex_sum(self):
        x = core.bounded_simplex(np.array([0.8, 0.1, 0.1]), 0.2, 0.5)
        self.assertAlmostEqual(float(x.sum()), 1.0, places=10)

    # 08
    def test_08_bounded_simplex_bounds(self):
        x = core.bounded_simplex(np.array([0.8, 0.1, 0.1]), 0.2, 0.5)
        self.assertTrue(np.all(x >= 0.2 - 1e-10) and np.all(x <= 0.5 + 1e-10))

    # 09
    def test_09_bounded_simplex_infeasible(self):
        with self.assertRaises(ValueError):
            core.bounded_simplex(np.ones(3), 0.4, 0.5)

    # 10
    def test_10_safe_cov_is_psd(self):
        cov = core._safe_cov(self.data[["V10", "EQUITY_TREND", "GOLD_TREND"]])
        self.assertGreaterEqual(float(np.linalg.eigvalsh(cov).min()), -1e-10)

    # 11
    def test_11_stressed_cov_handles_nan(self):
        f = self.data[["V10", "EQUITY_TREND", "GOLD_TREND"]].copy()
        f.iloc[3:8, 1] = np.nan
        cov = core._stressed_cov(f, 0.75, 0.25)
        self.assertTrue(np.isfinite(cov).all())

    # 12
    def test_12_performance_metrics_finite(self):
        m = core.performance_metrics(pd.Series([0.01, -0.005, 0.003], index=pd.date_range("2024-01-01", periods=3, tz="UTC")))
        self.assertTrue(math.isfinite(m["sharpe"]))

    # 13
    def test_13_performance_rejects_liquidation(self):
        with self.assertRaises(ValueError):
            core.performance_metrics(pd.Series([0.0, -1.0], index=pd.date_range("2024-01-01", periods=2, tz="UTC")))

    # 14
    def test_14_exact_ppm_net(self):
        ppm = core._exact_ppm_weights(1.0, 0.3, 0.3, -0.6)
        self.assertEqual(sum(ppm), 1_000_000)

    # 15
    def test_15_exact_ppm_core(self):
        ppm = core._exact_ppm_weights(1.0, 0.1733333, 0.1266667, -0.3)
        self.assertEqual(ppm[0], 1_000_000)

    # 16
    def test_16_v10_common_oos_name(self):
        r = core.run_v10(self.data, self.cfg)
        self.assertEqual(r.name, "V10_ALIGNED_COMMON_OOS")

    # 17
    def test_17_static_core_is_fixed(self):
        r = core.run_static_portable(self.data, self.cfg)
        self.assertTrue(np.allclose(r.weights["V10"], 1.0))

    # 18
    def test_18_static_overlay_is_30_30(self):
        r = core.run_static_portable(self.data, self.cfg)
        self.assertTrue(np.allclose(r.weights["EQUITY_TREND"], 0.30))
        self.assertTrue(np.allclose(r.weights["GOLD_TREND"], 0.30))

    # 19
    def test_19_static_net_is_one(self):
        r = core.run_static_portable(self.data, self.cfg)
        self.assertTrue(np.allclose(r.weights.sum(axis=1), 1.0))

    # 20
    def test_20_static_risky_gross_is_160(self):
        r = core.run_static_portable(self.data, self.cfg)
        gross = r.weights[["V10", "EQUITY_TREND", "GOLD_TREND"]].abs().sum(axis=1)
        self.assertTrue(np.allclose(gross, 1.60))

    # 21
    def test_21_static_zero_overlay_matches_v10(self):
        a = core.run_static_portable(self.data, self.cfg, 0.0, 0.0, "ZERO")
        b = core.run_v10(self.data, self.cfg)
        self.assertTrue(np.allclose(a.returns, b.returns))

    # 22
    def test_22_financing_is_positive_cost(self):
        r = core.run_static_portable(self.data, self.cfg)
        self.assertGreater(float(r.financing.mean()), 0.0)

    # 23
    def test_23_higher_borrow_spread_reduces_return(self):
        low = core.run_static_portable(self.data, replace(self.cfg, borrow_spread_annual=0.01))
        high = core.run_static_portable(self.data, replace(self.cfg, borrow_spread_annual=0.12))
        self.assertGreater(float(low.returns.mean()), float(high.returns.mean()))

    # 24
    def test_24_ledger_net_invariant(self):
        r = core.run_static_portable(self.data, self.cfg)
        self.assertTrue((r.ledger["net_ppm"] == 1_000_000).all())

    # 25
    def test_25_ledger_gross_cap(self):
        r = core.run_static_portable(self.data, self.cfg)
        self.assertTrue((r.ledger["risky_gross_ppm"] <= 1_600_000).all())

    # 26
    def test_26_hysteresis_fast_down(self):
        q, pending = core._hysteresis_step(0.60, 0.15, 2, self.cfg)
        self.assertAlmostEqual(q, 0.15)
        self.assertEqual(pending, 0)

    # 27
    def test_27_hysteresis_slow_up(self):
        q1, p1 = core._hysteresis_step(0.0, 0.60, 0, self.cfg)
        q2, p2 = core._hysteresis_step(q1, 0.60, p1, self.cfg)
        q3, _ = core._hysteresis_step(q2, 0.60, p2, self.cfg)
        self.assertEqual(q1, 0.0)
        self.assertEqual(q2, 0.0)
        self.assertEqual(q3, 0.15)

    # 28
    def test_28_dynamic_core_fixed(self):
        r = core.run_dynamic_overlay(self.data, self.cfg, online=False)
        self.assertTrue(np.allclose(r.weights["V10"], 1.0))

    # 29
    def test_29_dynamic_overlay_states(self):
        r = core.run_dynamic_overlay(self.data, self.cfg, online=False)
        q = (r.weights["EQUITY_TREND"] + r.weights["GOLD_TREND"]).round(8)
        allowed = {round(float(x), 8) for x in core.OVERLAY_STATES}
        self.assertTrue(set(q.unique()).issubset(allowed))

    # 30
    def test_30_online_split_bounds(self):
        r = core.run_dynamic_overlay(self.data, self.cfg, online=True)
        q = r.weights["EQUITY_TREND"] + r.weights["GOLD_TREND"]
        active = q > 1e-12
        split = r.weights.loc[active, "EQUITY_TREND"] / q.loc[active]
        self.assertTrue(((split >= self.cfg.online_split_min - 1e-10) & (split <= self.cfg.online_split_max + 1e-10)).all())

    # 31
    def test_31_online_core_fixed(self):
        r = core.run_dynamic_overlay(self.data, self.cfg, online=True)
        self.assertTrue(np.allclose(r.weights["V10"], 1.0))

    # 32
    def test_32_future_perturbation_does_not_change_past_dynamic(self):
        cut = 850
        a = core.run_dynamic_overlay(self.data, self.cfg, online=False)
        changed = self.data.copy()
        changed.iloc[cut:, changed.columns.get_loc("EQUITY_TREND")] += 0.20
        b = core.run_dynamic_overlay(changed, self.cfg, online=False)
        date = self.data.index[cut - 1]
        past = a.weights.index[a.weights.index <= date]
        self.assertTrue(np.allclose(a.weights.loc[past], b.weights.loc[past]))

    # 33
    def test_33_future_perturbation_does_not_change_past_online(self):
        cut = 850
        a = core.run_dynamic_overlay(self.data, self.cfg, online=True)
        changed = self.data.copy()
        changed.iloc[cut:, changed.columns.get_loc("GOLD_TREND")] -= 0.20
        b = core.run_dynamic_overlay(changed, self.cfg, online=True)
        date = self.data.index[cut - 1]
        past = a.weights.index[a.weights.index <= date]
        self.assertTrue(np.allclose(a.weights.loc[past], b.weights.loc[past]))

    # 34
    def test_34_equal_average_control_matches_average_overlay(self):
        d = core.run_dynamic_overlay(self.data, self.cfg, online=False)
        c = core.run_equal_average_overlay_control(self.data, self.cfg, d, "CONTROL")
        qd = float((d.weights["EQUITY_TREND"] + d.weights["GOLD_TREND"]).mean())
        qc = float((c.weights["EQUITY_TREND"] + c.weights["GOLD_TREND"]).mean())
        self.assertAlmostEqual(qd, qc, places=10)

    # 35
    def test_35_gap_maintenance_medium_passes(self):
        rows = core.gap_stress_table()
        self.assertGreater(rows[1]["maintenance_ratio"], self.cfg.margin_min_ratio)

    # 36
    def test_36_bootstrap_is_deterministic(self):
        a = core.run_static_portable(self.data, self.cfg)
        b = core.run_v10(self.data, self.cfg)
        x = core.paired_block_bootstrap(a.returns, b.returns, 30, 20, 7)
        y = core.paired_block_bootstrap(a.returns, b.returns, 30, 20, 7)
        self.assertEqual(x, y)

    # 37
    def test_37_hac_is_finite(self):
        a = core.run_static_portable(self.data, self.cfg)
        b = core.run_v10(self.data, self.cfg)
        out = core.newey_west_mean_test(a.returns - b.returns, 20)
        self.assertTrue(math.isfinite(out["t_stat"]))

    # 38
    def test_38_dsr_probability_bounds(self):
        a = core.run_static_portable(self.data, self.cfg)
        out = core.deflated_sharpe_probability(a.returns, 250)
        self.assertGreaterEqual(out["probability"], 0.0)
        self.assertLessEqual(out["probability"], 1.0)

    # 39
    def test_39_economic_gate_schema(self):
        a = core.run_static_portable(self.data, self.cfg)
        b = core.run_v10(self.data, self.cfg)
        gate = core.economic_gates(a, b)
        self.assertIn("pass", gate)
        self.assertIn("cagr_advantage", gate["tests"])

    # 40
    def test_40_incremental_gate_schema(self):
        d = core.run_dynamic_overlay(self.data, self.cfg, online=False)
        o = core.run_dynamic_overlay(self.data, self.cfg, online=True)
        gate = core.incremental_gate(o, d, "online")
        self.assertIn("wealth_ratio", gate["tests"])

    # 41
    def test_41_baseline_identity_names_aligned(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "engine_returns.csv"
            self.data.reset_index().to_csv(p, index=False)
            identity = core.baseline_identity(self.data, self.cfg, p)
            self.assertEqual(identity["name"], "V10_ALIGNED_COMMON_OOS")
            self.assertEqual(identity["not_name"], "V10_FULL_HISTORY")

    # 42
    def test_42_manifest_detects_files(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "a.txt").write_text("a", encoding="utf-8")
            manifest = core.output_manifest(root)
            self.assertEqual(manifest["files"][0]["path"], "a.txt")

    # 43
    def test_43_deterministic_zip_bytes(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "root"
            root.mkdir()
            (root / "a.txt").write_text("hello", encoding="utf-8")
            z1 = Path(td) / "a.zip"
            z2 = Path(td) / "b.zip"
            core.deterministic_zip(root, z1)
            core.deterministic_zip(root, z2)
            self.assertEqual(z1.read_bytes(), z2.read_bytes())

    # 44
    def test_44_full_smoke_run_and_verify(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            input_path = root / "engine_returns.csv.gz"
            self.data.reset_index().to_csv(input_path, index=False, compression={"method": "gzip", "mtime": 0})
            cfg = replace(self.cfg, bootstrap_samples=10)
            output = root / "results"
            gate = cli.run_lab(input_path, output, cfg)
            self.assertIn("overall_status", gate)
            verification = cli.verify_results(output)
            self.assertTrue(verification["passed"])


if __name__ == "__main__":
    unittest.main(verbosity=2)

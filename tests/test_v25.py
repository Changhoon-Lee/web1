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

import v25_core as core
import v25_cli as cli


class V25Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        rng = np.random.default_rng(20260720)
        idx = pd.date_range("2021-01-01", periods=1150, freq="D", tz="UTC")
        common = rng.normal(0.0007, 0.010, len(idx))
        crisis = np.zeros(len(idx))
        crisis[720:728] = -0.055
        crisis[900:904] = -0.075
        v10 = common + crisis
        hedge = 0.00080 - 0.55 * common - 0.70 * crisis + rng.normal(0, 0.003, len(idx))
        bad = 0.0001 + 0.50 * common + 0.20 * crisis + rng.normal(0, 0.004, len(idx))
        cash = np.full(len(idx), 0.03 / core.ANNUALIZATION)
        cls.data = pd.DataFrame({"V10": v10, "CASH": cash, "TAIL_HEDGE": hedge, "TAIL_BAD": bad}, index=idx)
        cls.data.index.name = "date"
        cls.provenance = {
            "engines": {
                "TAIL_HEDGE": {"tradable": True, "point_in_time": True, "source_sha256": "abc", "retrieved_at": "2026-07-20", "cost_model": "17bp"},
                "TAIL_BAD": {"tradable": True, "point_in_time": True, "source_sha256": "def", "retrieved_at": "2026-07-20", "cost_model": "17bp"},
            }
        }
        cls.cfg = core.Config(warmup_days=300, minimum_tail_observations=10, core_up_confirm_days=3, bootstrap_samples=10)

    def test_01_config_valid(self):
        self.cfg.validate()

    def test_02_horizon_covers_delay(self):
        with self.assertRaises(ValueError):
            replace(self.cfg, delay=3, empirical_horizon=3).validate()

    def test_03_stress_loss_has_gap_floor(self):
        s = core.stress_loss(self.data["V10"].iloc[:500], self.cfg)
        self.assertGreaterEqual(s["stress_loss"], self.cfg.gap_loss_floor)

    def test_04_capacity_full_at_high_water(self):
        cap = core.core_capacity(1.0, 1.0, self.data["V10"].iloc[:500], self.cfg)
        self.assertEqual(cap["allowed_state"], 1.0)

    def test_05_capacity_falls_after_drawdown(self):
        cap = core.core_capacity(0.80, 1.0, self.data["V10"].iloc[:500], self.cfg)
        self.assertLess(cap["allowed_state"], 1.0)

    def test_06_fast_down(self):
        state, pending = core.hysteresis_step(1.0, 0.25, 2, self.cfg)
        self.assertEqual(state, 0.25)
        self.assertEqual(pending, 0)

    def test_07_slow_up(self):
        state, pending = core.hysteresis_step(0.25, 1.0, 0, self.cfg)
        self.assertEqual(state, 0.25)
        self.assertEqual(pending, 1)
        state, pending = core.hysteresis_step(state, 1.0, pending, self.cfg)
        state, pending = core.hysteresis_step(state, 1.0, pending, self.cfg)
        self.assertEqual(state, 0.50)

    def test_08_provenance_pass(self):
        self.assertTrue(core.provenance_pass(self.provenance["engines"]["TAIL_HEDGE"]))

    def test_09_provenance_missing_fails(self):
        self.assertFalse(core.provenance_pass({"tradable": True}))

    def test_10_negative_tail_engine_qualifies(self):
        row = core.tail_engine_statistics(self.data.iloc[:700], "TAIL_HEDGE", self.provenance["engines"]["TAIL_HEDGE"], self.cfg)
        self.assertTrue(row["qualified"], row)
        self.assertLessEqual(row["tail_beta"], 0.0)
        self.assertGreater(row["tail_mean"], 0.0)

    def test_11_positive_beta_engine_fails(self):
        row = core.tail_engine_statistics(self.data.iloc[:700], "TAIL_BAD", self.provenance["engines"]["TAIL_BAD"], self.cfg)
        self.assertFalse(row["qualified"])
        self.assertFalse(row["tests"]["negative_tail_beta"])

    def test_12_missing_provenance_blocks_engine(self):
        row = core.tail_engine_statistics(self.data.iloc[:700], "TAIL_HEDGE", {}, self.cfg)
        self.assertFalse(row["qualified"])
        self.assertFalse(row["tests"]["provenance"])

    def test_13_unverified_research_mode_is_explicit(self):
        cfg = replace(self.cfg, allow_unverified_tail=True)
        row = core.tail_engine_statistics(self.data.iloc[:700], "TAIL_HEDGE", {}, cfg)
        self.assertTrue(row["qualified"])
        self.assertFalse(row["provenance_pass"])

    def test_14_tail_weights_sum_one(self):
        weights, rows = core.qualify_tail_engines(self.data.iloc[:700], self.provenance, self.cfg)
        self.assertAlmostEqual(sum(weights.values()), 1.0)
        self.assertIn("TAIL_HEDGE", weights)
        self.assertNotIn("TAIL_BAD", weights)

    def test_15_core_policy_bounds(self):
        result = core.run_core_derisk(self.data, self.cfg)
        self.assertTrue(((result.weights["V10"] >= 0) & (result.weights["V10"] <= 1)).all())
        self.assertTrue(np.allclose(result.weights.sum(axis=1), 1.0))
        self.assertLess(result.weights["V10"].min(), 1.0)

    def test_16_dual_policy_uses_only_qualified_tail(self):
        result = core.run_dual_defense(self.data, self.cfg, self.provenance)
        self.assertGreater(float(result.weights["TAIL_HEDGE"].max()), 0.0)
        self.assertAlmostEqual(float(result.weights["TAIL_BAD"].max()), 0.0)
        self.assertTrue(np.allclose(result.weights.sum(axis=1), 1.0))
        self.assertTrue((result.weights.drop(columns=["CASH"]).abs().sum(axis=1) <= 1.0 + 1e-12).all())

    def test_17_no_provenance_falls_back_to_cash(self):
        result = core.run_dual_defense(self.data, self.cfg, {"engines": {}})
        reduced = result.weights["V10"] < 1.0
        self.assertTrue(reduced.any())
        self.assertAlmostEqual(float(result.weights.loc[reduced, ["TAIL_HEDGE", "TAIL_BAD"]].abs().sum().sum()), 0.0)
        self.assertGreater(float(result.weights.loc[reduced, "CASH"].sum()), 0.0)

    def test_18_exact_ledger_invariants(self):
        result = core.run_dual_defense(self.data, self.cfg, self.provenance)
        self.assertTrue((result.ledger["net_ppm"] == 1_000_000).all())
        self.assertTrue((result.ledger["risky_gross_ppm"] <= 1_000_000).all())
        self.assertTrue(((result.ledger["v10_ppm"] >= 0) & (result.ledger["v10_ppm"] <= 1_000_000)).all())
        self.assertTrue((result.ledger["tail_hedge_ppm"] >= 0).all())

    def test_19_future_perturbation_preserves_past_policy(self):
        original = core.run_dual_defense(self.data, self.cfg, self.provenance)
        changed = self.data.copy()
        cutoff = changed.index[850]
        changed.loc[changed.index > cutoff, ["V10", "TAIL_HEDGE", "TAIL_BAD"]] *= -3.0
        perturbed = core.run_dual_defense(changed, self.cfg, self.provenance)
        common = original.weights.index[original.weights.index <= cutoff]
        pd.testing.assert_frame_equal(original.weights.loc[common], perturbed.weights.loc[common])

    def test_20_equal_average_control_net_one(self):
        source = core.run_core_derisk(self.data, self.cfg)
        control = core.run_equal_average_control(self.data, self.cfg, source, "CONTROL")
        self.assertTrue(np.allclose(control.weights.sum(axis=1), 1.0))
        expected = abs(float(control.weights.iloc[0]["V10"]) - 1.0) + abs(float(control.weights.iloc[0]["TAIL_HEDGE"])) + abs(float(control.weights.iloc[0]["TAIL_BAD"]))
        self.assertAlmostEqual(float(control.turnover.iloc[0]), expected)

    def test_21_bootstrap_deterministic(self):
        a = core.run_core_derisk(self.data, self.cfg)
        b = core.run_v10(self.data, self.cfg)
        x = core.paired_block_bootstrap(a.returns, b.returns, 30, 20, 7)
        y = core.paired_block_bootstrap(a.returns, b.returns, 30, 20, 7)
        self.assertEqual(x, y)

    def test_22_manifest_deterministic(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "b.txt").write_text("b", encoding="utf-8")
            (root / "a.txt").write_text("a", encoding="utf-8")
            x = core.output_manifest(root)
            y = core.output_manifest(root)
            self.assertEqual(x, y)
            self.assertEqual(x["files"][0]["path"], "a.txt")

    def test_23_deterministic_zip(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "root"
            root.mkdir()
            (root / "a.txt").write_text("hello", encoding="utf-8")
            z1, z2 = Path(td) / "1.zip", Path(td) / "2.zip"
            core.deterministic_zip(root, z1)
            core.deterministic_zip(root, z2)
            self.assertEqual(z1.read_bytes(), z2.read_bytes())

    def test_24_full_smoke_run_verify_and_handoff(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            input_path = root / "v25_engine_returns.csv.gz"
            self.data.reset_index().to_csv(input_path, index=False, compression={"method": "gzip", "mtime": 0})
            provenance_path = root / "tail_provenance.json"
            provenance_path.write_text(json.dumps(self.provenance), encoding="utf-8")
            output = root / "results"
            gate = cli.run_lab(input_path, provenance_path, output, self.cfg)
            self.assertIn("overall_status", gate)
            verification = cli.verify_results(output)
            self.assertTrue(verification["passed"])
            destination = root / "handoff.zip"
            handoff = cli.build_handoff(Path(__file__).resolve().parents[1], output, destination)
            self.assertTrue(destination.exists())
            self.assertTrue(handoff["verification"]["passed"])


if __name__ == "__main__":
    unittest.main(verbosity=2)

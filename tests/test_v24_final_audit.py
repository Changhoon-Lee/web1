#!/usr/bin/env python3
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

import v24_core as core
import v24_tail_audit as audit


class V24FinalAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        rng = np.random.default_rng(2401)
        idx = pd.date_range("2021-01-01", periods=540, freq="D", tz="UTC")
        common = rng.normal(0.00025, 0.010, len(idx))
        v10 = 0.00065 + common
        equity = 0.00028 + 0.10 * common + rng.normal(0.0, 0.005, len(idx))
        gold = 0.00018 - 0.15 * common + rng.normal(0.0, 0.004, len(idx))
        cls.data = pd.DataFrame({
            "GROWTH_CRYPTO": v10 + rng.normal(0.0, 0.001, len(idx)),
            "EQUITY_TREND": equity,
            "GOLD_TREND": gold,
            "V10": v10,
            "CASH": np.full(len(idx), 0.035 / core.ANNUALIZATION),
        }, index=idx)
        cls.data.index.name = "date"
        cls.cfg = core.Config(warmup_days=252, bootstrap_samples=10, up_confirm_days=3)

    def test_45_markdown_renderer_has_no_optional_dependency(self):
        rendered = audit.markdown_table(pd.DataFrame({"a": [1], "b": [2.5]}))
        self.assertIn("| a", rendered)
        self.assertNotIn("tabulate", rendered.lower())

    def test_46_state_grid_is_complete_and_bounded(self):
        states = audit.overlay_state_grid()
        self.assertEqual(len(states), 28)
        self.assertTrue(np.all(states >= 0.0))
        self.assertTrue(np.all(states.sum(axis=1) <= 0.6000000001))
        self.assertTrue(np.any(np.all(np.isclose(states, [0.3, 0.3]), axis=1)))

    def test_47_exact_oracle_utility_is_monotone(self):
        oos = core.common_oos(self.data, self.cfg)
        utilities = []
        for switches in (0, 1, 3, 6, None):
            _, utility = audit.exact_wealth_path(oos, self.cfg, switches)
            utilities.append(utility)
        self.assertTrue(np.all(np.diff(utilities) >= -1e-9))

    def test_48_switch_limits_are_respected(self):
        oos = core.common_oos(self.data, self.cfg)
        for switches in (0, 1, 3, 6):
            path, _ = audit.exact_wealth_path(oos, self.cfg, switches)
            self.assertLessEqual(audit.count_switches(path), switches)

    def test_49_oracle_result_keeps_core_and_gross_cap(self):
        oos = core.common_oos(self.data, self.cfg)
        path, _ = audit.exact_wealth_path(oos, self.cfg, 3)
        result = audit.state_path_to_result(self.data, self.cfg, oos.index, path, "TEST_ORACLE")
        self.assertTrue(np.allclose(result.weights["V10"], 1.0))
        gross = result.weights[["V10", "EQUITY_TREND", "GOLD_TREND"]].abs().sum(axis=1)
        self.assertLessEqual(float(gross.max()), 1.6000000001)
        self.assertTrue((result.ledger["net_ppm"] == 1_000_000).all())

    def test_50_drawdown_window_is_ordered(self):
        result = core.run_v10(self.data, self.cfg)
        episode = audit.maximum_drawdown_window(result.returns)
        self.assertLessEqual(episode["peak"], episode["trough"])
        self.assertLessEqual(episode["mdd"], 0.0)

    def test_51_required_offset_is_finite_or_explicit_infinite(self):
        v10 = core.run_v10(self.data, self.cfg)
        static = core.run_static_portable(self.data, self.cfg)
        frame = audit.required_tail_offset(self.data, self.cfg, v10, static)
        self.assertEqual(set(frame["window"]), {"V10_MAX_DRAWDOWN", "V10_WORST_20D", "V10_WORST_60D", "V10_WORST_120D"})
        self.assertTrue((frame["observations"] > 0).all())

    def test_52_identified_tail_upper_bound_schema(self):
        result = core.run_v10(self.data, self.cfg)
        upper = audit.identified_tail_upper_bound(self.data, self.cfg, result)
        self.assertIn("finite_grid_upper_bound_ratio", upper)
        self.assertIn("claim_boundary", upper)
        self.assertGreater(upper["finite_grid_upper_bound_ratio"], 0.0)

    def test_53_causal_selector_future_perturbation(self):
        first = audit.causal_monthly_selector(self.data, self.cfg, 60, "FIRST")
        changed = self.data.copy()
        cutoff = changed.index[410]
        changed.loc[changed.index > cutoff, ["EQUITY_TREND", "GOLD_TREND", "V10"]] *= -7.0
        second = audit.causal_monthly_selector(changed, self.cfg, 60, "SECOND")
        comparison_end = cutoff + pd.Timedelta(days=self.cfg.delay)
        left = first.weights.loc[first.weights.index <= comparison_end]
        right = second.weights.loc[second.weights.index <= comparison_end]
        pd.testing.assert_frame_equal(left, right, check_names=False)

    def test_54_oracle_family_writes_monotone_table(self):
        table, results, _ = audit.exact_oracle_family(self.data, self.cfg)
        self.assertEqual(len(table), 5)
        self.assertEqual(len(results), 5)
        self.assertTrue(np.all(np.diff(table["log_utility"].to_numpy()) >= -1e-9))

    def test_55_causal_selector_family_count(self):
        v10 = core.run_v10(self.data, self.cfg)
        table, results = audit.causal_selector_family(self.data, self.cfg, v10)
        self.assertEqual(len(table), 4)
        self.assertEqual(len(results), 4)

    def test_56_tail_audit_smoke_and_verify(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            gate = audit.run_tail_audit(self.data, self.cfg, output)
            self.assertIn("status", gate)
            verified = audit.verify_tail_audit(output)
            self.assertTrue(verified["passed"])

    def test_57_audited_report_uses_builtin_markdown(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            pd.DataFrame({"name": ["x"], "sharpe": [1.0]}).to_csv(output / "strategy_summary.csv", index=False)
            pd.DataFrame({"name": ["oracle"], "log_utility": [1.0]}).to_csv(output / "TAIL_ORACLE_COMPARISON.csv", index=False)
            pd.DataFrame({"name": ["causal"], "cagr": [0.1]}).to_csv(output / "CAUSAL_TAIL_SELECTOR.csv", index=False)
            path = output / "FINAL_REPORT.md"
            audit.write_audited_report(path, {"overall_status": "BASE"}, {"status": "AUDIT", "claim_boundary": "bounded"}, output)
            text = path.read_text()
            self.assertIn("V24 Final Audited Handoff", text)
            self.assertIn("deterministic built-in renderer", text)


if __name__ == "__main__":
    unittest.main()

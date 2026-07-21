#!/usr/bin/env python3
from __future__ import annotations

import unittest
from pathlib import Path

import pandas as pd

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import v272_cli as cli
import v272_core as core
from tests.test_v272 import synthetic_market, test_config


class V272WrapperTests(unittest.TestCase):
    def test_26_pretrade_initial_equity_is_authoritative_baseline(self):
        cfg = test_config()
        data = core.canonicalize_market(synthetic_market(), cfg)
        result = core.run_long_gamma(data, cfg)
        self.assertFalse(result.ledger.empty)
        self.assertEqual(float(result.ledger.iloc[0]["equity_usd"]), cfg.initial_equity_usd)
        self.assertEqual(float(result.ledger.iloc[0]["cash_usd"]), cfg.initial_equity_usd)
        self.assertEqual(float(result.ledger.iloc[0]["option_value_usd"]), 0.0)
        expected_ratio = float(result.ledger.iloc[-1]["equity_usd"] / cfg.initial_equity_usd)
        self.assertAlmostEqual(result.metrics["final_wealth_ratio"], expected_ratio, places=12)

    def test_27_report_renderer_accepts_structured_metrics(self):
        frame = pd.DataFrame([
            {"variant": "primary", "live_held_symbols": ["BTC-C", "BTC-P"], "metric": 1.25},
            {"variant": "unhedged", "live_held_symbols": [], "metric": float("nan")},
        ])
        markdown = cli.manual_markdown(frame)
        self.assertIn('["BTC-C", "BTC-P"]', markdown)
        self.assertIn("primary", markdown)
        self.assertIn("unhedged", markdown)


if __name__ == "__main__":
    unittest.main()

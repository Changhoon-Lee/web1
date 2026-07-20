from __future__ import annotations

import json
import math
import tempfile
import unittest
import zipfile
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pandas as pd

from src.v271_core import (
    LabConfig,
    bootstrap_mean,
    bs_straddle,
    build_manifest,
    continuity_metrics,
    daily_market,
    deribit_option_fee_usd,
    deterministic_zip,
    exact_ledger,
    monthly_variance_anchors,
    newey_west_mean,
    normal_cdf,
    normalize_dvol_frame,
    normalize_index_frame,
    performance_metrics,
    run_open_free_lab,
    sha256_file,
    simulate_synthetic_straddle,
    verify_manifest,
    write_json,
)
from src.v271_deribit_public import DeribitPublicClient, fetch_dvol, fetch_index
from src.v271_cli import build_report, pack, verify_results


def synthetic_frames(days: int = 900, seed: int = 7) -> tuple[pd.DataFrame, pd.DataFrame]:
    rng = np.random.default_rng(seed)
    dates = pd.date_range("2022-01-01", periods=days, freq="D", tz="UTC")
    returns = rng.normal(0.0005, 0.028, days)
    prices = 30000.0 * np.exp(np.cumsum(returns))
    dvol = 55.0 + 9.0 * np.sin(np.linspace(0, 16, days)) + rng.normal(0, 1.5, days)
    return pd.DataFrame({"timestamp": dates, "index_price": prices}), pd.DataFrame({"timestamp": dates, "dvol": dvol})


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload
    def raise_for_status(self):
        return None
    def json(self):
        return self.payload


class FakeSession:
    def __init__(self, payloads):
        self.payloads = list(payloads)
        self.calls = []
    def post(self, url, json, timeout):
        self.calls.append((url, json, timeout))
        payload = self.payloads.pop(0)
        return FakeResponse(payload)


class FakeClient:
    def __init__(self, mapping):
        self.mapping = mapping
        self.calls = []
    def call(self, method, params=None):
        self.calls.append((method, params))
        value = self.mapping[method]
        return value(params) if callable(value) else value


class V271Tests(unittest.TestCase):
    def test_01_normal_cdf_zero(self):
        self.assertAlmostEqual(normal_cdf(0.0), 0.5, places=12)

    def test_02_put_call_parity(self):
        x = bs_straddle(100, 105, 30 / 365.25, 0.60)
        call_minus_put = x["call"] - x["put"]
        self.assertAlmostEqual(call_minus_put, -5.0, places=8)

    def test_03_straddle_positive(self):
        x = bs_straddle(100, 100, 30 / 365.25, 0.50)
        self.assertGreater(x["mid"], 0)

    def test_04_atm_delta_near_zero(self):
        x = bs_straddle(100, 100, 30 / 365.25, 0.50)
        self.assertLess(abs(x["delta"]), 0.10)

    def test_05_gamma_positive(self):
        self.assertGreater(bs_straddle(100, 100, 30 / 365.25, 0.50)["gamma"], 0)

    def test_06_price_increases_with_vol(self):
        low = bs_straddle(100, 100, 30 / 365.25, 0.30)["mid"]
        high = bs_straddle(100, 100, 30 / 365.25, 0.80)["mid"]
        self.assertGreater(high, low)

    def test_07_option_fee_cap(self):
        cfg = LabConfig()
        fee = deribit_option_fee_usd(100000, 10, 1, cfg)
        self.assertAlmostEqual(fee, 1.25)

    def test_08_normalize_index_duplicate(self):
        f = pd.DataFrame({"timestamp": ["2024-01-01", "2024-01-01"], "index_price": [100, 101]})
        out = normalize_index_frame(f)
        self.assertEqual(len(out), 1)
        self.assertEqual(float(out.iloc[0, 0]), 101)

    def test_09_normalize_dvol_filter(self):
        f = pd.DataFrame({"timestamp": ["2024-01-01", "2024-01-02"], "dvol": [50, -1]})
        self.assertEqual(len(normalize_dvol_frame(f)), 1)

    def test_10_daily_market_columns(self):
        idx, dv = synthetic_frames(100)
        out = daily_market(idx, dv, LabConfig())
        self.assertTrue({"index_price", "dvol", "log_return"}.issubset(out.columns))

    def test_11_monthly_anchors(self):
        idx, dv = synthetic_frames(900)
        market = daily_market(idx, dv, LabConfig())
        anchors = monthly_variance_anchors(market, LabConfig())
        self.assertGreaterEqual(len(anchors), 20)
        self.assertEqual(anchors["anchor"].dt.to_period("M").nunique(), len(anchors))

    def test_12_anchor_realized_nonnegative(self):
        idx, dv = synthetic_frames(400)
        anchors = monthly_variance_anchors(daily_market(idx, dv, LabConfig()), LabConfig())
        self.assertTrue((anchors["realized_variance"] >= 0).all())

    def test_13_anchor_future_perturbation(self):
        idx, dv = synthetic_frames(500)
        market1 = daily_market(idx, dv, LabConfig())
        a1 = monthly_variance_anchors(market1, LabConfig())
        cutoff = pd.Timestamp("2022-10-01", tz="UTC")
        idx2 = idx.copy()
        idx2.loc[pd.to_datetime(idx2["timestamp"], utc=True) > cutoff, "index_price"] *= 1.5
        a2 = monthly_variance_anchors(daily_market(idx2, dv, LabConfig()), LabConfig())
        cols = ["anchor", "implied_vol"]
        pd.testing.assert_frame_equal(a1.loc[a1["horizon_end"] <= cutoff, cols].reset_index(drop=True), a2.loc[a2["horizon_end"] <= cutoff, cols].reset_index(drop=True))

    def test_14_newey_west_positive(self):
        x = np.array([0.1, 0.2, 0.15, 0.18])
        self.assertGreater(newey_west_mean(x)["mean"], 0)

    def test_15_bootstrap_deterministic(self):
        cfg = LabConfig(bootstrap_samples=200)
        x = np.arange(10, dtype=float)
        self.assertEqual(bootstrap_mean(x, cfg), bootstrap_mean(x, cfg))

    def test_16_simulation_final_closed(self):
        idx, dv = synthetic_frames(120)
        curve, ledger, _ = simulate_synthetic_straddle(daily_market(idx, dv, LabConfig()), LabConfig())
        self.assertEqual(int(curve.iloc[-1]["position_open"]), 0)
        self.assertEqual(float(curve.iloc[-1]["option_mark"]), 0.0)
        self.assertIn("final_close", set(ledger["reason"]))

    def test_17_hedged_differs_unhedged(self):
        idx, dv = synthetic_frames(120)
        market = daily_market(idx, dv, LabConfig())
        h, _, _ = simulate_synthetic_straddle(market, LabConfig(), hedged=True)
        u, _, _ = simulate_synthetic_straddle(market, LabConfig(), hedged=False)
        self.assertNotAlmostEqual(float(h.iloc[-1]["equity"]), float(u.iloc[-1]["equity"]), places=8)

    def test_18_cost_monotonic(self):
        idx, dv = synthetic_frames(160)
        market = daily_market(idx, dv, LabConfig())
        base, _, _ = simulate_synthetic_straddle(market, LabConfig())
        high, _, _ = simulate_synthetic_straddle(market, replace(LabConfig(), option_half_spread=0.10, hedge_cost_bps=30))
        self.assertLessEqual(float(high.iloc[-1]["equity"]), float(base.iloc[-1]["equity"]))

    def test_19_trade_ledger_open_close(self):
        idx, dv = synthetic_frames(100)
        _, ledger, _ = simulate_synthetic_straddle(daily_market(idx, dv, LabConfig()), LabConfig())
        self.assertIn("open", set(ledger["event"]))
        self.assertIn("close", set(ledger["event"]))

    def test_20_performance_flat(self):
        idx = pd.date_range("2024-01-01", periods=10, freq="D", tz="UTC")
        m = performance_metrics(pd.Series(np.ones(10), index=idx))
        self.assertEqual(m["wealth"], 1.0)
        self.assertEqual(m["mdd"], 0.0)

    def test_21_continuity(self):
        idx, dv = synthetic_frames(30)
        m = daily_market(idx, dv, LabConfig())
        c = continuity_metrics(m)
        self.assertEqual(c["active_days"], 30)
        self.assertAlmostEqual(c["coverage"], 1.0)

    def test_22_sparse_status(self):
        idx, dv = synthetic_frames(120)
        result = run_open_free_lab(idx, dv, LabConfig(bootstrap_samples=100))
        self.assertEqual(result["status"]["model_status"], "OPEN_FREE_DATA_INSUFFICIENT")

    def test_23_deployable_always_blocked(self):
        idx, dv = synthetic_frames(900)
        result = run_open_free_lab(idx, dv, LabConfig(bootstrap_samples=100))
        self.assertEqual(result["status"]["deployable_status"], "BLOCKED_NO_HISTORICAL_OPTION_BID_ASK_CHAIN")

    def test_24_exact_ledger_integers(self):
        idx, dv = synthetic_frames(90)
        curve, _, _ = simulate_synthetic_straddle(daily_market(idx, dv, LabConfig()), LabConfig())
        led = exact_ledger(curve)
        self.assertTrue(pd.api.types.is_integer_dtype(led["equity"]))

    def test_25_manifest_pass(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "a.txt").write_text("a", encoding="utf-8")
            manifest = build_manifest(root)
            self.assertTrue(verify_manifest(root, manifest)[0])

    def test_26_manifest_detects_change(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            p = root / "a.txt"
            p.write_text("a", encoding="utf-8")
            manifest = build_manifest(root)
            p.write_text("b", encoding="utf-8")
            self.assertFalse(verify_manifest(root, manifest)[0])

    def test_27_deterministic_zip(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "src"
            root.mkdir()
            (root / "a.txt").write_text("hello", encoding="utf-8")
            z1, z2 = Path(td) / "1.zip", Path(td) / "2.zip"
            deterministic_zip(root, z1)
            deterministic_zip(root, z2)
            self.assertEqual(sha256_file(z1), sha256_file(z2))

    def test_28_write_json_strict(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "x.json"
            write_json(p, {"x": np.float64(1.2)})
            self.assertEqual(json.loads(p.read_text())["x"], 1.2)

    def test_29_public_client_payload(self):
        session = FakeSession([{"jsonrpc": "2.0", "id": 1, "result": {"ok": True}}])
        client = DeribitPublicClient(session=session)
        self.assertEqual(client.call("public/test"), {"ok": True})
        self.assertEqual(session.calls[0][1]["method"], "public/test")

    def test_30_public_client_error(self):
        session = FakeSession([{"jsonrpc": "2.0", "id": 1, "error": {"message": "bad"}}])
        with self.assertRaises(RuntimeError):
            DeribitPublicClient(session=session).call("public/test")

    def test_31_fetch_dvol_parser(self):
        client = FakeClient({"public/get_volatility_index_data": {"data": [[1000, 1, 2, 0, 55]], "continuation": None}})
        frame, _ = fetch_dvol(client, 0, 2000)
        self.assertEqual(float(frame.iloc[0]["dvol"]), 55)

    def test_32_fetch_index_parser(self):
        client = FakeClient({"public/get_index_chart_data": [[1000, 123.0]]})
        frame, _ = fetch_index(client)
        self.assertEqual(float(frame.iloc[0]["index_price"]), 123.0)

    def test_33_report_disclaimer(self):
        idx, dv = synthetic_frames(120)
        payload = run_open_free_lab(idx, dv, LabConfig(bootstrap_samples=50))
        payload = {k: v for k, v in payload.items() if k != "frames"}
        report = build_report(payload, {"paid_sources_used": False})
        self.assertIn("not an executable historical option-chain backtest", report)

    def test_34_report_no_paid(self):
        idx, dv = synthetic_frames(120)
        payload = run_open_free_lab(idx, dv, LabConfig(bootstrap_samples=50))
        payload = {k: v for k, v in payload.items() if k != "frames"}
        self.assertIn("Paid data used: False", build_report(payload, {"paid_sources_used": False}))

    def test_35_future_perturbation_curve(self):
        idx, dv = synthetic_frames(180)
        cutoff = pd.Timestamp("2022-04-01", tz="UTC")
        m1 = daily_market(idx, dv, LabConfig())
        c1, _, _ = simulate_synthetic_straddle(m1, LabConfig())
        idx2 = idx.copy()
        idx2.loc[pd.to_datetime(idx2["timestamp"], utc=True) > cutoff, "index_price"] *= 2
        c2, _, _ = simulate_synthetic_straddle(daily_market(idx2, dv, LabConfig()), LabConfig())
        pd.testing.assert_series_equal(c1.loc[c1.index <= cutoff, "equity"], c2.loc[c2.index <= cutoff, "equity"])

    def test_36_final_equity_equals_cash(self):
        idx, dv = synthetic_frames(100)
        curve, _, _ = simulate_synthetic_straddle(daily_market(idx, dv, LabConfig()), LabConfig())
        self.assertAlmostEqual(float(curve.iloc[-1]["equity"]), float(curve.iloc[-1]["cash"]), places=12)

    def test_37_cost3_not_better_than_cost2(self):
        idx, dv = synthetic_frames(250)
        result = run_open_free_lab(idx, dv, LabConfig(bootstrap_samples=50))
        s = result["strategies"]
        self.assertLessEqual(s["synthetic_delta_hedged_cost_3x"]["wealth"], s["synthetic_delta_hedged_cost_2x"]["wealth"])

    def test_38_all_results_model_only(self):
        idx, dv = synthetic_frames(900)
        result = run_open_free_lab(idx, dv, LabConfig(bootstrap_samples=50))
        self.assertEqual(result["status"]["historical_claim"], "MODEL_BASED_DIAGNOSTIC_ONLY")

    def test_39_pack_excludes_runtime(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "a.txt").write_text("a", encoding="utf-8")
            (root / "runtime").mkdir()
            (root / "runtime" / "old.zip").write_text("x", encoding="utf-8")
            path = pack(root)
            with zipfile.ZipFile(path) as zf:
                self.assertNotIn("runtime/old.zip", zf.namelist())

    def test_40_verify_rejects_missing(self):
        with tempfile.TemporaryDirectory() as td:
            ok, errors = verify_results(Path(td))
            self.assertFalse(ok)
            self.assertTrue(errors)

    def test_41_protocol_has_no_paid_key(self):
        files = [Path("src/v271_core.py"), Path("src/v271_deribit_public.py"), Path("src/v271_cli.py")]
        combined = "\n".join(p.read_text(encoding="utf-8") for p in files)
        self.assertNotIn("TARDIS_API_KEY", combined)

    def test_42_only_public_deribit_methods(self):
        text = Path("src/v271_deribit_public.py").read_text(encoding="utf-8")
        self.assertNotIn("private/", text)
        self.assertIn("public/get_volatility_index_data", text)


if __name__ == "__main__":
    unittest.main()

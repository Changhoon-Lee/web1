from __future__ import annotations

import json
import tempfile
import unittest
import zipfile
from dataclasses import replace
from pathlib import Path

import numpy as np
import pandas as pd

from src.v271_core import (
    LabConfig, bootstrap_mean, bs_straddle, build_manifest, continuity_metrics,
    daily_market, deribit_option_fee_usd, deterministic_zip, exact_ledger,
    monthly_variance_anchors, newey_west_mean, normal_cdf,
    normalize_dvol_frame, normalize_index_frame, performance_metrics,
    run_open_free_lab, sha256_file, simulate_synthetic_straddle,
    verify_manifest, write_json,
)
from src.v271_deribit_public import DeribitPublicClient, fetch_dvol, fetch_index
from src.v271_cli import build_report, pack, verify_results


def synthetic_frames(days: int = 900, seed: int = 7):
    rng = np.random.default_rng(seed)
    dates = pd.date_range("2022-01-01", periods=days, freq="D", tz="UTC")
    returns = rng.normal(0.0005, 0.028, days)
    prices = 30000.0 * np.exp(np.cumsum(returns))
    dvol = 55.0 + 9.0 * np.sin(np.linspace(0, 16, days)) + rng.normal(0, 1.5, days)
    return pd.DataFrame({"timestamp": dates, "index_price": prices}), pd.DataFrame({"timestamp": dates, "dvol": dvol})


class FakeResponse:
    def __init__(self, payload): self.payload = payload
    def raise_for_status(self): return None
    def json(self): return self.payload


class FakeSession:
    def __init__(self, payloads): self.payloads, self.calls = list(payloads), []
    def post(self, url, json, timeout):
        self.calls.append((url, json, timeout))
        return FakeResponse(self.payloads.pop(0))


class FakeClient:
    def __init__(self, mapping): self.mapping, self.calls = mapping, []
    def call(self, method, params=None):
        self.calls.append((method, params))
        value = self.mapping[method]
        return value(params) if callable(value) else value


class V271Tests(unittest.TestCase):
    def test_01_normal_cdf_zero(self): self.assertAlmostEqual(normal_cdf(0.0), 0.5, places=12)
    def test_02_put_call_parity(self):
        x = bs_straddle(100, 105, 30 / 365.25, 0.60)
        self.assertAlmostEqual(x["call"] - x["put"], -5.0, places=8)
    def test_03_straddle_positive(self): self.assertGreater(bs_straddle(100, 100, 30/365.25, .5)["mid"], 0)
    def test_04_atm_delta_near_zero(self): self.assertLess(abs(bs_straddle(100, 100, 30/365.25, .5)["delta"]), .10)
    def test_05_gamma_positive(self): self.assertGreater(bs_straddle(100, 100, 30/365.25, .5)["gamma"], 0)
    def test_06_price_increases_with_vol(self):
        self.assertGreater(bs_straddle(100,100,30/365.25,.8)["mid"], bs_straddle(100,100,30/365.25,.3)["mid"])
    def test_07_option_fee_cap(self): self.assertAlmostEqual(deribit_option_fee_usd(100000,10,1,LabConfig()), 1.25)
    def test_08_normalize_index_duplicate(self):
        out = normalize_index_frame(pd.DataFrame({"timestamp":["2024-01-01"]*2,"index_price":[100,101]}))
        self.assertEqual((len(out), float(out.iloc[0,0])), (1,101.0))
    def test_09_normalize_dvol_filter(self):
        self.assertEqual(len(normalize_dvol_frame(pd.DataFrame({"timestamp":["2024-01-01","2024-01-02"],"dvol":[50,-1]}))),1)
    def test_10_daily_market_columns(self):
        a,b=synthetic_frames(100); self.assertTrue({"index_price","dvol","log_return"}.issubset(daily_market(a,b,LabConfig()).columns))
    def test_11_monthly_anchors(self):
        a,b=synthetic_frames(900); x=monthly_variance_anchors(daily_market(a,b,LabConfig()),LabConfig())
        self.assertGreaterEqual(len(x),20); self.assertEqual(x["anchor"].dt.tz is not None, True)
    def test_12_anchor_realized_nonnegative(self):
        a,b=synthetic_frames(400); x=monthly_variance_anchors(daily_market(a,b,LabConfig()),LabConfig()); self.assertTrue((x.realized_variance>=0).all())
    def test_13_anchor_future_perturbation(self):
        a,b=synthetic_frames(500); cutoff=pd.Timestamp("2022-10-01",tz="UTC")
        x1=monthly_variance_anchors(daily_market(a,b,LabConfig()),LabConfig())
        a2=a.copy(); a2.loc[pd.to_datetime(a2.timestamp,utc=True)>cutoff,"index_price"]*=1.5
        x2=monthly_variance_anchors(daily_market(a2,b,LabConfig()),LabConfig())
        cols=["anchor","implied_vol"]
        pd.testing.assert_frame_equal(x1.loc[x1.horizon_end<=cutoff,cols].reset_index(drop=True),x2.loc[x2.horizon_end<=cutoff,cols].reset_index(drop=True))
    def test_14_newey_west_positive(self): self.assertGreater(newey_west_mean(np.array([.1,.2,.15,.18]))["mean"],0)
    def test_15_bootstrap_deterministic(self):
        c=LabConfig(bootstrap_samples=200); x=np.arange(10,dtype=float); self.assertEqual(bootstrap_mean(x,c),bootstrap_mean(x,c))
    def test_16_simulation_final_closed(self):
        a,b=synthetic_frames(120); curve,ledger,_=simulate_synthetic_straddle(daily_market(a,b,LabConfig()),LabConfig())
        self.assertEqual(int(curve.iloc[-1].position_open),0); self.assertEqual(float(curve.iloc[-1].option_mark),0.0)
        self.assertEqual(ledger.iloc[-1].event,"close")
    def test_17_hedged_differs_unhedged(self):
        a,b=synthetic_frames(120); m=daily_market(a,b,LabConfig()); h,_,_=simulate_synthetic_straddle(m,LabConfig(),hedged=True); u,_,_=simulate_synthetic_straddle(m,LabConfig(),hedged=False)
        self.assertNotAlmostEqual(float(h.iloc[-1].equity),float(u.iloc[-1].equity),places=8)
    def test_18_cost_monotonic(self):
        a,b=synthetic_frames(160); m=daily_market(a,b,LabConfig()); low,_,_=simulate_synthetic_straddle(m,LabConfig()); high,_,_=simulate_synthetic_straddle(m,replace(LabConfig(),option_half_spread=.10,hedge_cost_bps=30))
        self.assertLessEqual(float(high.iloc[-1].equity),float(low.iloc[-1].equity))
    def test_19_trade_ledger_open_close(self):
        a,b=synthetic_frames(100); _,l,_=simulate_synthetic_straddle(daily_market(a,b,LabConfig()),LabConfig()); self.assertTrue({"open","close"}.issubset(set(l.event)))
    def test_20_performance_flat(self):
        idx=pd.date_range("2024-01-01",periods=10,freq="D",tz="UTC"); m=performance_metrics(pd.Series(np.ones(10),index=idx)); self.assertEqual((m["wealth"],m["mdd"]),(1.0,0.0))
    def test_21_continuity(self):
        a,b=synthetic_frames(30); c=continuity_metrics(daily_market(a,b,LabConfig())); self.assertEqual(c["active_days"],30); self.assertAlmostEqual(c["coverage"],1)
    def test_22_sparse_status(self):
        a,b=synthetic_frames(120); self.assertEqual(run_open_free_lab(a,b,LabConfig(bootstrap_samples=50))["status"]["model_status"],"OPEN_FREE_DATA_INSUFFICIENT")
    def test_23_deployable_always_blocked(self):
        a,b=synthetic_frames(900); self.assertEqual(run_open_free_lab(a,b,LabConfig(bootstrap_samples=50))["status"]["deployable_status"],"BLOCKED_NO_HISTORICAL_OPTION_BID_ASK_CHAIN")
    def test_24_exact_ledger_integers(self):
        a,b=synthetic_frames(90); c,_,_=simulate_synthetic_straddle(daily_market(a,b,LabConfig()),LabConfig()); self.assertTrue(pd.api.types.is_integer_dtype(exact_ledger(c)["equity"]))
    def test_25_manifest_pass(self):
        with tempfile.TemporaryDirectory() as td:
            r=Path(td); (r/"a").write_text("a"); m=build_manifest(r); self.assertTrue(verify_manifest(r,m)[0])
    def test_26_manifest_detects_change(self):
        with tempfile.TemporaryDirectory() as td:
            r=Path(td); p=r/"a"; p.write_text("a"); m=build_manifest(r); p.write_text("b"); self.assertFalse(verify_manifest(r,m)[0])
    def test_27_deterministic_zip(self):
        with tempfile.TemporaryDirectory() as td:
            r=Path(td)/"s"; r.mkdir(); (r/"a").write_text("hello"); z1,z2=Path(td)/"1.zip",Path(td)/"2.zip"; deterministic_zip(r,z1); deterministic_zip(r,z2); self.assertEqual(sha256_file(z1),sha256_file(z2))
    def test_28_write_json_strict(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/"x.json"; write_json(p,{"x":np.float64(1.2)}); self.assertEqual(json.loads(p.read_text())["x"],1.2)
    def test_29_public_client_payload(self):
        s=FakeSession([{"jsonrpc":"2.0","id":1,"result":{"ok":True}}]); c=DeribitPublicClient(session=s); self.assertEqual(c.call("public/test"),{"ok":True}); self.assertEqual(s.calls[0][1]["method"],"public/test")
    def test_30_public_client_error(self):
        s=FakeSession([{"jsonrpc":"2.0","id":1,"error":{"message":"bad"}}]); self.assertRaises(RuntimeError,DeribitPublicClient(session=s).call,"public/test")
    def test_31_fetch_dvol_parser(self):
        c=FakeClient({"public/get_volatility_index_data":{"data":[[1000,1,2,0,55]],"continuation":None}}); f,_=fetch_dvol(c,0,2000); self.assertEqual(float(f.iloc[0].dvol),55)
    def test_32_fetch_index_parser(self):
        c=FakeClient({"public/get_index_chart_data":[[1000,123.0]]}); f,_=fetch_index(c); self.assertEqual(float(f.iloc[0].index_price),123)
    def test_33_report_disclaimer(self):
        a,b=synthetic_frames(120); p=run_open_free_lab(a,b,LabConfig(bootstrap_samples=20)); p={k:v for k,v in p.items() if k!="frames"}; self.assertIn("not an executable historical option-chain backtest",build_report(p,{"paid_sources_used":False}))
    def test_34_report_no_paid(self):
        a,b=synthetic_frames(120); p=run_open_free_lab(a,b,LabConfig(bootstrap_samples=20)); p={k:v for k,v in p.items() if k!="frames"}; self.assertIn("Paid data used: False",build_report(p,{"paid_sources_used":False}))
    def test_35_future_perturbation_curve(self):
        a,b=synthetic_frames(180); cutoff=pd.Timestamp("2022-04-01",tz="UTC"); c1,_,_=simulate_synthetic_straddle(daily_market(a,b,LabConfig()),LabConfig()); a2=a.copy(); a2.loc[pd.to_datetime(a2.timestamp,utc=True)>cutoff,"index_price"]*=2; c2,_,_=simulate_synthetic_straddle(daily_market(a2,b,LabConfig()),LabConfig()); pd.testing.assert_series_equal(c1.loc[c1.index<=cutoff,"equity"],c2.loc[c2.index<=cutoff,"equity"])
    def test_36_final_equity_equals_cash(self):
        a,b=synthetic_frames(100); c,_,_=simulate_synthetic_straddle(daily_market(a,b,LabConfig()),LabConfig()); self.assertAlmostEqual(float(c.iloc[-1].equity),float(c.iloc[-1].cash),places=12)
    def test_37_cost3_not_better_than_cost2(self):
        a,b=synthetic_frames(250); s=run_open_free_lab(a,b,LabConfig(bootstrap_samples=20))["strategies"]; self.assertLessEqual(s["synthetic_delta_hedged_cost_3x"]["wealth"],s["synthetic_delta_hedged_cost_2x"]["wealth"])
    def test_38_all_results_model_only(self):
        a,b=synthetic_frames(900); self.assertEqual(run_open_free_lab(a,b,LabConfig(bootstrap_samples=20))["status"]["historical_claim"],"MODEL_BASED_DIAGNOSTIC_ONLY")
    def test_39_pack_excludes_runtime(self):
        with tempfile.TemporaryDirectory() as td:
            r=Path(td); (r/"a").write_text("a"); (r/"runtime").mkdir(); (r/"runtime"/"old.zip").write_text("x"); z=pack(r); self.assertNotIn("runtime/old.zip",zipfile.ZipFile(z).namelist())
    def test_40_verify_rejects_missing(self):
        with tempfile.TemporaryDirectory() as td:
            ok,e=verify_results(Path(td)); self.assertFalse(ok); self.assertTrue(e)
    def test_41_protocol_has_no_paid_key(self):
        text="\n".join(Path(p).read_text() for p in ["src/v271_core.py","src/v271_deribit_public.py","src/v271_cli.py"]); self.assertNotIn("TARDIS_API_KEY",text)
    def test_42_only_public_deribit_methods(self):
        text=Path("src/v271_deribit_public.py").read_text(); self.assertNotIn("private/",text); self.assertIn("public/get_volatility_index_data",text)

if __name__ == "__main__": unittest.main()

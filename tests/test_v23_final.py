from __future__ import annotations

import json
import math
import sys
from dataclasses import replace
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import v23_final_lab as lab


def synthetic(n: int = 1200, seed: int = 7) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2018-01-01", periods=n, freq="D", tz="UTC")
    common = rng.normal(0.0002, 0.008, n)
    growth = common + rng.normal(0.0007, 0.018, n)
    equity = 0.15 * common + rng.normal(0.00025, 0.007, n)
    gold = -0.05 * common + rng.normal(0.00015, 0.006, n)
    v10 = growth * 0.75 + rng.normal(0.0001, 0.006, n)
    cash = np.full(n, 0.03 / lab.ANNUALIZATION)
    return pd.DataFrame({"GROWTH_CRYPTO":growth,"EQUITY_TREND":equity,"GOLD_TREND":gold,"V10":v10,"CASH":cash}, index=idx)


def test_01_date_column_preserved():
    f = pd.DataFrame({"date":["2024-01-01","2024-01-02"],"x":[1,2]})
    out = lab.normalize_date_frame(f)
    assert out.index.name == "date" and len(out) == 2 and "x" in out


def test_02_numeric_millisecond_timestamp():
    f = pd.DataFrame({"timestamp":[1704067200000,1704153600000],"x":[1,2]})
    out = lab.normalize_date_frame(f)
    assert out.index[0].year == 2024


def test_03_missing_date_raises():
    with pytest.raises(ValueError): lab.normalize_date_frame(pd.DataFrame({"x":[1]}))


def test_04_canonical_aliases(tmp_path: Path):
    d = synthetic(950).reset_index(names="date").rename(columns={"GROWTH_CRYPTO":"growth","EQUITY_TREND":"equity","GOLD_TREND":"gold","V10":"baseline","CASH":"cash_return"})
    p=tmp_path/"x.csv"; d.to_csv(p,index=False)
    out=lab.canonicalize_input(p)
    assert list(out.columns)==list(lab.ENGINES)+["V10","CASH"]


def test_05_price_scale_rejected(tmp_path: Path):
    d=synthetic(950); d["V10"]=100
    p=tmp_path/"x.csv"; d.reset_index(names="date").to_csv(p,index=False)
    with pytest.raises(ValueError): lab.canonicalize_input(p)


def test_06_simplex_sum():
    x=lab.bounded_simplex(np.array([.8,.1,.1]),.2,.5)
    assert abs(x.sum()-1)<1e-9


def test_07_simplex_bounds():
    x=lab.bounded_simplex(np.array([9.,-2.,1.]),np.array([.2,.2,.2]),np.array([.5,.5,.5]))
    assert np.all(x>=.2-1e-9) and np.all(x<=.5+1e-9)


def test_08_simplex_infeasible():
    with pytest.raises(ValueError): lab.bounded_simplex(np.zeros(3),.4,.5)


def test_09_metrics_final_equity():
    r=pd.Series([.1,.1], index=pd.date_range("2024-01-01",periods=2,tz="UTC"))
    assert abs(lab.performance_metrics(r)["final_equity"]-1.21)<1e-12


def test_10_metrics_mdd():
    r=pd.Series([.1,-.2,.1], index=pd.date_range("2024-01-01",periods=3,tz="UTC"))
    assert lab.performance_metrics(r)["mdd"]<-.19


def test_11_cash_default_zero(tmp_path: Path):
    d=synthetic(950).drop(columns="CASH").reset_index(names="date")
    p=tmp_path/"x.csv"; d.to_csv(p,index=False)
    assert lab.canonicalize_input(p).CASH.eq(0).all()


def test_12_anchor_bounds():
    cfg=replace(lab.Config(),warmup_days=300)
    a=lab.anchor_signals(synthetic(400),cfg)
    assert a.iloc[150:].min().min()>=cfg.anchor_min_weight-1e-9 and a.max().max()<=cfg.anchor_max_weight+1e-9


def test_13_anchor_sum():
    a=lab.anchor_signals(synthetic(400),lab.Config())
    assert np.allclose(a.sum(axis=1),1)


def test_14_online_bounds():
    cfg=lab.Config(); d=synthetic(400); a=lab.anchor_signals(d,cfg); w=lab.online_tilt_signals(d,a,cfg)
    assert w.min().min()>=cfg.final_min_weight-1e-9 and w.max().max()<=cfg.final_max_weight+1e-9


def test_15_online_sum():
    d=synthetic(400); a=lab.anchor_signals(d,lab.Config()); w=lab.online_tilt_signals(d,a,lab.Config())
    assert np.allclose(w.sum(axis=1),1)


def test_16_future_perturbation_invariance():
    d=synthetic(500); cfg=lab.Config(); a1=lab.anchor_signals(d,cfg); w1=lab.online_tilt_signals(d,a1,cfg)
    changed=d.copy(); changed.iloc[450:,0]+=0.2; a2=lab.anchor_signals(changed,cfg); w2=lab.online_tilt_signals(changed,a2,cfg)
    pd.testing.assert_frame_equal(w1.iloc[:450],w2.iloc[:450])


def test_17_execution_delay():
    idx=pd.date_range("2024-01-01",periods=5,tz="UTC"); w=pd.DataFrame([[1,0,0],[0,1,0],[0,0,1],[1,0,0],[0,1,0]],index=idx,columns=lab.ENGINES); l=pd.Series(1,index=idx)
    actual,_=lab.shifted_targets(w,l,2)
    assert actual.iloc[2,0]==1 and actual.iloc[2,1]==0


def test_18_transaction_cost_positive():
    d=synthetic(20); idx=d.index; w=pd.DataFrame(1/3,index=idx,columns=lab.ENGINES); w.iloc[5:]=[1,0,0]
    r=lab.simulate_from_signals("x",d,w,pd.Series(1,index=idx),replace(lab.Config(),delay=0))
    assert r.turnover.iloc[5]>0


def test_19_financing_only_on_borrowing():
    d=synthetic(20); w=pd.DataFrame(1/3,index=d.index,columns=lab.ENGINES)
    one=lab.simulate_from_signals("one",d,w,pd.Series(1,index=d.index),replace(lab.Config(),delay=0))
    two=lab.simulate_from_signals("two",d,w,pd.Series(1.3,index=d.index),replace(lab.Config(),delay=0))
    assert one.financing.eq(0).all() and two.financing.gt(0).all()


def test_20_static_gross_cap():
    d=synthetic(30); w=pd.DataFrame(1/3,index=d.index,columns=lab.ENGINES)
    r=lab.simulate_from_signals("x",d,w,pd.Series(1.6,index=d.index),replace(lab.Config(),delay=0))
    assert r.leverage.max()<=1.6


def test_21_covariance_nan_finite():
    d=synthetic(100); d.iloc[10:20,1]=np.nan
    s=lab.covariance_matrix(d,lab.Config())
    assert np.isfinite(s).all()


def test_22_stress_covariance_diagonal_positive():
    s=lab.covariance_matrix(synthetic(200),lab.Config(),stress=True)
    assert np.all(np.diag(s)>0)


def test_23_worst_es_negative():
    assert lab.worst_es(synthetic(400).V10)<0


def test_24_gap_margin_cap_in_states():
    cap=lab.gap_margin_cap(np.array([.5,.3,.2]),lab.Config())
    assert cap in lab.LEVERAGE_STATES


def test_25_nearest_capacity():
    assert lab.nearest_allowed_capacity(1.42,lab.Config())==1.30


def test_26_dynamic_signal_bounds():
    d=synthetic(400); a=lab.anchor_signals(d,lab.Config()); l,_=lab.dynamic_leverage_signals(d,a,lab.Config())
    assert l.min()>=1 and l.max()<=1.6


def test_27_dynamic_signal_discrete():
    d=synthetic(400); a=lab.anchor_signals(d,lab.Config()); l,_=lab.dynamic_leverage_signals(d,a,lab.Config())
    assert set(np.round(l.unique(),2)).issubset(set(lab.LEVERAGE_STATES))


def test_28_capacity_has_binding():
    d=synthetic(400); a=lab.anchor_signals(d,lab.Config()); _,c=lab.dynamic_leverage_signals(d,a,lab.Config())
    assert "binding" in c and c.binding.notna().all()


def test_29_feasibility_nonempty():
    a={"cagr":.32,"mdd":-.18}; b={"cagr":.46,"mdd":-.37}
    assert lab.feasibility_screen(a,b,lab.Config())["feasible"]


def test_30_feasibility_empty():
    a={"cagr":.20,"mdd":-.18}; b={"cagr":.46,"mdd":-.37}
    assert not lab.feasibility_screen(a,b,lab.Config())["feasible"]


def test_31_hac_probability_range():
    x=pd.Series(np.random.default_rng(1).normal(size=300))
    p=lab.hac_mean(x,20)["p_one_sided"]
    assert 0<=p<=1


def test_32_bootstrap_fields():
    idx=pd.date_range("2020-01-01",periods=200,tz="UTC"); rng=np.random.default_rng(2)
    out=lab.paired_block_bootstrap(pd.Series(rng.normal(.001,.01,200),idx),pd.Series(rng.normal(0,.01,200),idx),30,50,1)
    assert out["lower_95"]<=out["upper_95"]


def test_33_dsr_range():
    out=lab.dsr(synthetic(500).V10,100)
    assert 0<=out["dsr"]<=1


def test_34_fold_metrics_not_empty():
    d=synthetic(1100); cfg=replace(lab.Config(),warmup_days=300,bootstrap_samples=5); out=lab.slice_oos(lab.run_strategies(d,cfg),cfg)
    assert not lab.six_month_folds(out).empty


def test_35_economic_gate_pass():
    b={"sharpe":1.,"cagr":.4,"final_equity":2.,"mdd":-.4,"calmar":1.,"cvar5":-.1,"maximum_gross":1.}
    c={"sharpe":1.2,"cagr":.41,"final_equity":2.2,"mdd":-.3,"calmar":1.3,"cvar5":-.08,"maximum_gross":1.6}
    assert all(lab.economic_gate(c,b).values())


def test_36_economic_gate_fail():
    b={"sharpe":1.,"cagr":.4,"final_equity":2.,"mdd":-.4,"calmar":1.,"cvar5":-.1,"maximum_gross":1.}
    assert not all(lab.economic_gate(b,b).values())


def test_37_controller_attribution_share():
    d=synthetic(400); cfg=lab.Config(); a=lab.anchor_signals(d,cfg); l,c=lab.dynamic_leverage_signals(d,a,cfg); r=lab.simulate_from_signals("x",d,a,l,cfg); r.capacities=c
    out=lab.controller_attribution(r)
    assert abs(out.share.sum()-1)<1e-9


def test_38_manifest_verification(tmp_path: Path):
    (tmp_path/"a.txt").write_text("a")
    m=lab.build_manifest(tmp_path)
    assert m["count"]==1 and (tmp_path/"OUTPUT_MANIFEST.json").exists()


def test_39_deterministic_ledger_hash():
    d=synthetic(60); cfg=replace(lab.Config(),delay=0); w=pd.DataFrame(1/3,index=d.index,columns=lab.ENGINES); l=pd.Series(1,index=d.index)
    a=lab.simulate_from_signals("a",d,w,l,cfg); b=lab.simulate_from_signals("b",d,w,l,cfg)
    assert lab.sha256_frame(a.ledger)==lab.sha256_frame(b.ledger)


def test_40_verify_missing_raises(tmp_path: Path):
    with pytest.raises(RuntimeError): lab.verify_results(tmp_path)


def test_41_explicit_discovery(tmp_path: Path):
    p=tmp_path/"x.csv"; p.write_text("x")
    assert lab.discover_input(tmp_path,p)==p.resolve()


def test_42_full_smoke(tmp_path: Path):
    d=synthetic(1100).reset_index(names="date"); p=tmp_path/"engine_returns.csv.gz"; d.to_csv(p,index=False,compression="gzip")
    out=tmp_path/"results"; cfg=replace(lab.Config(),warmup_days=300,bootstrap_samples=10)
    payload=lab.run_lab(p,out,cfg,prior_trials=100)
    assert (out/"FINAL_GATE.json").exists() and payload["version"]==lab.VERSION
    assert lab.verify_results(out)["status"]=="PASS"

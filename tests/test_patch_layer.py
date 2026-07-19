from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import v23_final_lab as lab


def _data(n: int = 420) -> pd.DataFrame:
    rng = np.random.default_rng(23)
    index = pd.date_range("2020-01-01", periods=n, freq="D", tz="UTC")
    return pd.DataFrame({
        "GROWTH_CRYPTO": rng.normal(.0005, .02, n),
        "EQUITY_TREND": rng.normal(.0002, .008, n),
        "GOLD_TREND": rng.normal(.0001, .006, n),
        "V10": rng.normal(.0005, .018, n),
        "CASH": np.full(n, .03 / lab.ANNUALIZATION),
    }, index=index)


def test_43_fixed_controller_future_invariance():
    data = _data()
    cfg = lab.Config()
    anchor_1 = lab.anchor_signals(data, cfg)
    leverage_1, capacity_1 = lab.dynamic_leverage_signals(data, anchor_1, cfg)
    changed = data.copy()
    changed.iloc[380:, 0] += .25
    anchor_2 = lab.anchor_signals(changed, cfg)
    leverage_2, capacity_2 = lab.dynamic_leverage_signals(changed, anchor_2, cfg)
    pd.testing.assert_series_equal(leverage_1.iloc[:380], leverage_2.iloc[:380])
    pd.testing.assert_series_equal(capacity_1.controller_equity.iloc[:380], capacity_2.controller_equity.iloc[:380])


def test_44_controller_equity_matches_delayed_realized_path():
    data = _data(300)
    cfg = lab.Config(delay=2, cost_bps=0.0, financing_rate=0.0)
    weights = pd.DataFrame(1 / 3, index=data.index, columns=lab.ENGINES)
    leverage, capacity = lab.dynamic_leverage_signals(data, weights, cfg)
    expected = 1.0
    for t, date in enumerate(data.index):
        signal_index = max(0, t - cfg.delay)
        actual = float(leverage.iloc[signal_index])
        expected *= 1.0 + actual * float(data.loc[date, list(lab.ENGINES)].mean())
        assert abs(float(capacity.loc[date, "controller_equity"]) - expected) < 1e-10

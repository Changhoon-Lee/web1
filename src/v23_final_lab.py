#!/usr/bin/env python3
"""Authoritative V23.1 wrapper.

Keeps the original core visible as v23_core.py while replacing two audited parts:
1) dynamic controller equity is updated from actually delayed positions, turnover and financing;
2) handoff ZIP includes every Mac command and protocol file.
"""
from __future__ import annotations

import sys
import zipfile
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

import v23_core as core
from v23_core import *  # noqa: F401,F403


def dynamic_leverage_signals(data: pd.DataFrame, weight_signal: pd.DataFrame, cfg: Config) -> tuple[pd.Series, pd.DataFrame]:
    signal = pd.Series(1.0, index=data.index, dtype=float)
    rows: list[dict[str, Any]] = []
    current = 1.0
    up_counter = 0
    strategy_equity = 1.0
    peak = 1.0

    delayed_weights = weight_signal.shift(cfg.delay).copy()
    initial = weight_signal.iloc[0].to_dict()
    delayed_weights = delayed_weights.fillna(pd.Series(initial))
    unlevered_anchor_return = (delayed_weights * data[list(ENGINES)]).sum(axis=1)

    previous_actual_asset = np.zeros(len(ENGINES), dtype=float)
    previous_cash_weight = 1.0

    for t, date in enumerate(data.index):
        signal_index = max(0, t - cfg.delay)
        actual_leverage = float(signal.iloc[signal_index])
        actual_weight = weight_signal.iloc[signal_index].to_numpy(float)
        actual_asset = actual_leverage * actual_weight
        cash_weight = 1.0 - actual_leverage

        turnover = float(np.abs(actual_asset - previous_actual_asset).sum() + abs(cash_weight - previous_cash_weight))
        trading_cost = turnover * cfg.cost_bps / 10000.0
        financing = max(actual_leverage - 1.0, 0.0) * cfg.financing_rate / ANNUALIZATION
        engine_return = data.loc[date, list(ENGINES)].to_numpy(float)
        realized = float(actual_asset @ engine_return + cash_weight * data.loc[date, "CASH"] - trading_cost - financing)
        strategy_equity *= 1.0 + realized
        peak = max(peak, strategy_equity)
        previous_actual_asset = actual_asset
        previous_cash_weight = cash_weight

        if t < 252:
            signal.iloc[t] = current
            rows.append({
                "date": date, "unconstrained": 1.0, "cap_vol": 1.0, "cap_es": 1.0,
                "cap_corr": 1.0, "cap_gap_margin": 1.0, "cap_drawdown": 1.0,
                "final_capacity": 1.0, "selected": current, "binding": "warmup",
                "actual_leverage": actual_leverage, "realized_net_return": realized,
                "realized_turnover": turnover, "realized_financing": financing,
                "controller_equity": strategy_equity,
            })
            continue

        hist = data.iloc[: t + 1]
        w = weight_signal.iloc[t].to_numpy(float)
        anchor_hist = unlevered_anchor_return.iloc[: t + 1]
        v10_hist = data["V10"].iloc[: t + 1]

        anchor_candidates = [ewma_vol(anchor_hist, span) for span in (20, 60, 120)]
        anchor_finite = [v for v in anchor_candidates if np.isfinite(v) and v > 1e-8]
        anchor_vol = max(anchor_finite or [1.0])
        v10_candidates = [ewma_vol(v10_hist, span) for span in (20, 60, 120)]
        v10_finite = [v for v in v10_candidates if np.isfinite(v) and v > 1e-8]
        v10_vol = max(v10_finite or [anchor_vol])

        cap_vol = v10_vol / max(anchor_vol, 1e-8)
        cap_es = abs(worst_es(v10_hist)) / max(abs(worst_es(anchor_hist)), 1e-8)
        stress_sigma = covariance_matrix(hist.iloc[-252:], cfg, stress=True)
        stress_port_vol = float(np.sqrt(max(float(w @ stress_sigma @ w) * ANNUALIZATION, 1e-12)))
        cap_corr = v10_vol / max(stress_port_vol, 1e-8)
        cap_gap = gap_margin_cap(w, cfg)

        current_dd = strategy_equity / peak - 1.0
        v10_recent = (1.0 + v10_hist.iloc[-756:]).cumprod()
        v10_mdd = float((v10_recent / v10_recent.cummax() - 1.0).min())
        drawdown_limit = float(np.clip(abs(v10_mdd) - cfg.mdd_improvement_target, 0.20, 0.33))
        ten_day = anchor_hist.rolling(10).apply(lambda x: np.prod(1.0 + x) - 1.0, raw=True).dropna()
        empirical = abs(float(ten_day.iloc[-756:].quantile(0.01))) if len(ten_day) else 0.10
        parametric = 2.33 * anchor_vol * np.sqrt(10.0 / ANNUALIZATION)
        stress_loss = max(empirical, float(parametric), 0.01)
        remaining = max(0.0, drawdown_limit - abs(current_dd))
        cap_dd = float(np.clip(remaining / stress_loss, 1.0, cfg.max_leverage))

        caps = {
            "cap_vol": float(cap_vol), "cap_es": float(cap_es), "cap_corr": float(cap_corr),
            "cap_gap_margin": float(cap_gap), "cap_drawdown": float(cap_dd),
        }
        raw = min(cfg.max_leverage, *caps.values())
        target = nearest_allowed_capacity(raw, cfg)

        if target < current - 1e-12:
            current = target
            up_counter = 0
        elif target > current + 1e-12:
            up_counter += 1
            if up_counter >= cfg.leverage_up_confirm_days:
                allowed = LEVERAGE_STATES[(LEVERAGE_STATES > current + 1e-12) & (LEVERAGE_STATES <= target + 1e-12)]
                if len(allowed):
                    current = float(allowed[0])
                up_counter = 0
        else:
            up_counter = 0

        signal.iloc[t] = current
        binding = min(caps, key=caps.get)
        rows.append({
            "date": date, "unconstrained": cfg.max_leverage, **caps,
            "final_capacity": float(raw), "selected": current, "binding": binding,
            "current_drawdown": current_dd, "drawdown_limit": drawdown_limit,
            "up_counter": up_counter, "actual_leverage": actual_leverage,
            "realized_net_return": realized, "realized_turnover": turnover,
            "realized_financing": financing, "controller_equity": strategy_equity,
        })

    return signal, pd.DataFrame(rows).set_index("date")


def build_handoff(root: Path, output: Path) -> Path:
    results = root / "results"
    verify_results(results)
    files: list[Path] = []
    for base in (results, root / "src", root / "tests"):
        if base.exists():
            files.extend(p for p in base.rglob("*") if p.is_file() and "__pycache__" not in p.parts)
    for path in root.iterdir():
        if path.is_file() and (path.suffix == ".command" or path.name in {"README.md", "requirements.txt", "PROTOCOL.json", "INPUT_SCHEMA.md", "BUILD_ID.txt"}):
            files.append(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for path in sorted(set(files), key=lambda p: p.relative_to(root).as_posix()):
            info = zipfile.ZipInfo(path.relative_to(root).as_posix(), (1980, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.external_attr = (0o755 if path.suffix == ".command" else 0o644) << 16
            zf.writestr(info, path.read_bytes())
    return output


# Patch the module namespace used by functions defined in v23_core.
core.dynamic_leverage_signals = dynamic_leverage_signals
core.build_handoff = build_handoff


def main() -> None:
    core.main()


if __name__ == "__main__":
    main()

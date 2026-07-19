#!/usr/bin/env python3
"""Final V24 tail-offset audit.

The audit preserves the V24 primary result and adds:
- deterministic Markdown tables without optional ``tabulate``;
- drawdown and rolling-window attribution;
- exact finite-grid wealth oracles with 0/1/3/6 or unlimited switches;
- an ex-post upper bound for the identified V10 maximum-drawdown window;
- causal monthly selectors whose decisions are delayed by the protocol delay;
- exact ledgers and audit gates with deliberately limited claims.

"Exact" below means exact dynamic programming on the preregistered finite state
space. It does not claim continuous-state or global minimum-MDD optimality.
"""
from __future__ import annotations

import json
import math
from dataclasses import asdict
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd

from v24_core import (
    ANNUALIZATION,
    VERSION,
    Config,
    StrategyResult,
    _simulate_positions,
    common_oos,
    output_manifest,
    performance_metrics,
    run_static_portable,
    run_v10,
    sha256_file,
    write_json,
)

AUDIT_VERSION = "24.1.0"
STATE_STEP = 0.10


def _display(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if isinstance(value, (np.bool_, bool)):
        return "true" if bool(value) else "false"
    if isinstance(value, (np.integer, int)):
        return str(int(value))
    if isinstance(value, (np.floating, float)):
        x = float(value)
        if not math.isfinite(x):
            return ""
        return f"{x:.6g}"
    return str(value).replace("|", "\\|").replace("\n", " ")


def markdown_table(frame: pd.DataFrame) -> str:
    """Render a deterministic GitHub-flavoured Markdown table."""
    f = frame.copy()
    columns = [str(c) for c in f.columns]
    rows = [[_display(v) for v in row] for row in f.itertuples(index=False, name=None)]
    widths = [len(c) for c in columns]
    for row in rows:
        widths = [max(w, len(v)) for w, v in zip(widths, row)]
    header = "| " + " | ".join(c.ljust(w) for c, w in zip(columns, widths)) + " |"
    separator = "| " + " | ".join("-" * w for w in widths) + " |"
    body = ["| " + " | ".join(v.ljust(w) for v, w in zip(row, widths)) + " |" for row in rows]
    return "\n".join([header, separator, *body])


def overlay_state_grid(step: float = STATE_STEP, maximum: float = 0.60) -> np.ndarray:
    units = int(round(maximum / step))
    states: list[tuple[float, float]] = []
    for i in range(units + 1):
        for j in range(units + 1 - i):
            states.append((round(i * step, 10), round(j * step, 10)))
    states.sort(key=lambda x: (x[0] + x[1], x[0], x[1]))
    return np.asarray(states, dtype=float)


def _state_index(states: np.ndarray, equity: float, gold: float) -> int:
    distance = np.abs(states[:, 0] - equity) + np.abs(states[:, 1] - gold)
    index = int(np.argmin(distance))
    if float(distance[index]) > 1e-9:
        raise ValueError("state not present in finite grid")
    return index


def _base_returns(frame: pd.DataFrame, cfg: Config, states: np.ndarray) -> np.ndarray:
    eq = frame["EQUITY_TREND"].to_numpy(dtype=float)[:, None]
    gold = frame["GOLD_TREND"].to_numpy(dtype=float)[:, None]
    v10 = frame["V10"].to_numpy(dtype=float)[:, None]
    cash = frame["CASH"].to_numpy(dtype=float)[:, None]
    q = states[:, 0] + states[:, 1]
    financing = q[None, :] * (cash + cfg.borrow_spread_annual / ANNUALIZATION)
    return v10 + eq * states[None, :, 0] + gold * states[None, :, 1] - financing


def _transition_costs(states: np.ndarray, cfg: Config) -> np.ndarray:
    turnover = np.abs(states[:, None, 0] - states[None, :, 0]) + np.abs(states[:, None, 1] - states[None, :, 1])
    return turnover * cfg.one_way_cost_bps / 10_000.0


def _initial_costs(states: np.ndarray, cfg: Config) -> np.ndarray:
    return (states[:, 0] + states[:, 1]) * cfg.one_way_cost_bps / 10_000.0


def _log1p_valid(values: np.ndarray) -> np.ndarray:
    out = np.full_like(values, -np.inf, dtype=float)
    valid = values > -1.0
    out[valid] = np.log1p(values[valid])
    return out


def _reconstruct_limited(back_state: np.ndarray, back_k: np.ndarray, end_k: int, end_state: int) -> np.ndarray:
    path = np.zeros(back_state.shape[0], dtype=np.int16)
    state = int(end_state)
    switches = int(end_k)
    path[-1] = state
    for t in range(len(path) - 1, 0, -1):
        previous_state = int(back_state[t, switches, state])
        previous_k = int(back_k[t, switches, state])
        if previous_state < 0 or previous_k < 0:
            raise RuntimeError("broken limited-oracle backpointer")
        path[t - 1] = previous_state
        state, switches = previous_state, previous_k
    return path


def exact_wealth_path(
    frame: pd.DataFrame,
    cfg: Config,
    max_switches: int | None,
    *,
    charge_initial: bool = True,
    states: np.ndarray | None = None,
) -> tuple[np.ndarray, float]:
    """Exact terminal-log-wealth DP on the finite overlay state grid."""
    states = overlay_state_grid() if states is None else np.asarray(states, dtype=float)
    if frame.empty:
        raise ValueError("empty oracle frame")
    base = _base_returns(frame, cfg, states)
    costs = _transition_costs(states, cfg)
    initial = _initial_costs(states, cfg) if charge_initial else np.zeros(len(states), dtype=float)
    first = _log1p_valid(base[0] - initial)
    t_count, state_count = base.shape

    if max_switches is None:
        dp = first.copy()
        back = np.full((t_count, state_count), -1, dtype=np.int16)
        for t in range(1, t_count):
            transition_log = _log1p_valid(base[t][None, :] - costs)
            candidates = dp[:, None] + transition_log
            previous = np.argmax(candidates, axis=0)
            dp = candidates[previous, np.arange(state_count)]
            back[t] = previous.astype(np.int16)
        end_state = int(np.argmax(dp))
        path = np.zeros(t_count, dtype=np.int16)
        path[-1] = end_state
        for t in range(t_count - 1, 0, -1):
            path[t - 1] = back[t, path[t]]
        return path, float(dp[end_state])

    kmax = int(max_switches)
    dp = np.full((kmax + 1, state_count), -np.inf, dtype=float)
    dp[0] = first
    back_state = np.full((t_count, kmax + 1, state_count), -1, dtype=np.int16)
    back_k = np.full((t_count, kmax + 1, state_count), -1, dtype=np.int16)
    for t in range(1, t_count):
        transition_log = _log1p_valid(base[t][None, :] - costs)
        new = np.full_like(dp, -np.inf)
        for k in range(kmax + 1):
            for state in range(state_count):
                same = dp[k, state] + transition_log[state, state]
                best_value = same
                best_state = state
                best_k = k
                if k > 0:
                    switched = dp[k - 1] + transition_log[:, state]
                    switched[state] = -np.inf
                    previous = int(np.argmax(switched))
                    value = float(switched[previous])
                    if value > best_value:
                        best_value, best_state, best_k = value, previous, k - 1
                new[k, state] = best_value
                back_state[t, k, state] = best_state
                back_k[t, k, state] = best_k
        dp = new
    end_flat = int(np.argmax(dp))
    end_k, end_state = np.unravel_index(end_flat, dp.shape)
    return _reconstruct_limited(back_state, back_k, int(end_k), int(end_state)), float(dp[end_k, end_state])


def state_path_to_result(data: pd.DataFrame, cfg: Config, index: pd.Index, state_path: np.ndarray, name: str, states: np.ndarray | None = None) -> StrategyResult:
    states = overlay_state_grid() if states is None else states
    selected = states[np.asarray(state_path, dtype=int)]
    weights = pd.DataFrame({
        "V10": 1.0,
        "EQUITY_TREND": selected[:, 0],
        "GOLD_TREND": selected[:, 1],
        "CASH": -(selected[:, 0] + selected[:, 1]),
    }, index=index)
    return _simulate_positions(data, weights, cfg, name)


def count_switches(path: np.ndarray) -> int:
    values = np.asarray(path, dtype=int)
    return int(np.count_nonzero(values[1:] != values[:-1])) if len(values) > 1 else 0


def maximum_drawdown_window(returns: pd.Series) -> dict[str, Any]:
    r = pd.Series(returns, dtype=float).dropna()
    equity = (1.0 + r).cumprod()
    running = equity.cummax()
    drawdown = equity / running - 1.0
    trough = drawdown.idxmin()
    peak = equity.loc[:trough].idxmax()
    peak_value = float(equity.loc[peak])
    recovery = None
    after = equity.loc[trough:]
    recovered = after[after >= peak_value]
    if len(recovered):
        recovery = recovered.index[0]
    return {
        "peak": peak,
        "trough": trough,
        "recovery": recovery,
        "mdd": float(drawdown.loc[trough]),
        "peak_equity": peak_value,
        "trough_equity": float(equity.loc[trough]),
    }


def worst_rolling_window(returns: pd.Series, days: int) -> dict[str, Any]:
    r = pd.Series(returns, dtype=float).dropna()
    rolling = (1.0 + r).rolling(days).apply(np.prod, raw=True) - 1.0
    end = rolling.idxmin()
    end_position = r.index.get_loc(end)
    start = r.index[end_position - days + 1]
    return {"start": start, "end": end, "return": float(rolling.loc[end]), "days": int(days)}


def _window_slice_after_peak(index: pd.Index, peak: pd.Timestamp, trough: pd.Timestamp) -> pd.Index:
    peak_position = int(index.get_loc(peak))
    trough_position = int(index.get_loc(trough))
    if trough_position <= peak_position:
        return index[peak_position : peak_position + 1]
    return index[peak_position + 1 : trough_position + 1]


def _window_attribution(label: str, strategy: StrategyResult, start: pd.Timestamp, end: pd.Timestamp) -> dict[str, Any]:
    returns = strategy.returns.loc[start:end]
    contributions = strategy.contributions.loc[start:end]
    row: dict[str, Any] = {
        "window": label,
        "strategy": strategy.name,
        "start": start,
        "end": end,
        "observations": int(len(returns)),
        "exact_compounded_return": float((1.0 + returns).prod() - 1.0),
    }
    for column in contributions.columns:
        row[f"sum_{column.lower()}"] = float(contributions[column].sum())
    return row


def drawdown_attribution(v10: StrategyResult, static: StrategyResult) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    v10_mdd = maximum_drawdown_window(v10.returns)
    static_mdd = maximum_drawdown_window(static.returns)
    windows: list[tuple[str, pd.Timestamp, pd.Timestamp]] = [
        ("V10_MAX_DRAWDOWN", v10_mdd["peak"], v10_mdd["trough"]),
        ("STATIC_MAX_DRAWDOWN", static_mdd["peak"], static_mdd["trough"]),
    ]
    for days in (20, 60, 120):
        window = worst_rolling_window(v10.returns, days)
        windows.append((f"V10_WORST_{days}D", window["start"], window["end"]))
    for label, start, end in windows:
        for strategy in (v10, static):
            rows.append(_window_attribution(label, strategy, start, end))
    return pd.DataFrame(rows)


def _required_constant_sleeve_return(v10: pd.Series, cash: pd.Series, target_ratio: float, cfg: Config, overlay: float = 0.60) -> float:
    if len(v10) == 0:
        return 0.0
    cost = overlay * cfg.one_way_cost_bps / 10_000.0
    spread = cfg.borrow_spread_annual / ANNUALIZATION

    def ratio(sleeve_daily: float) -> float:
        values = v10.to_numpy(dtype=float) + overlay * sleeve_daily - overlay * (cash.to_numpy(dtype=float) + spread)
        values = values.copy()
        values[0] -= cost
        if np.any(values <= -1.0):
            return 0.0
        return float(np.prod(1.0 + values))

    if ratio(0.0) >= target_ratio:
        return 0.0
    low, high = -0.99, 0.01
    while ratio(high) < target_ratio and high < 5.0:
        high *= 2.0
    if ratio(high) < target_ratio:
        return float("inf")
    for _ in range(120):
        middle = (low + high) / 2.0
        if ratio(middle) >= target_ratio:
            high = middle
        else:
            low = middle
    return float(high)


def required_tail_offset(data: pd.DataFrame, cfg: Config, v10: StrategyResult, static: StrategyResult) -> pd.DataFrame:
    episode = maximum_drawdown_window(v10.returns)
    windows: list[tuple[str, pd.Timestamp, pd.Timestamp, float]] = [
        ("V10_MAX_DRAWDOWN", episode["peak"], episode["trough"], float(episode["mdd"])),
    ]
    for days in (20, 60, 120):
        window = worst_rolling_window(v10.returns, days)
        windows.append((f"V10_WORST_{days}D", window["start"], window["end"], float(window["return"])))
    rows = []
    for label, start, end, baseline_return in windows:
        if label == "V10_MAX_DRAWDOWN":
            index = _window_slice_after_peak(v10.returns.index, start, end)
        else:
            index = v10.returns.loc[start:end].index
        target_return = min(0.0, baseline_return + cfg.target_mdd_improvement)
        target_ratio = 1.0 + target_return
        required_daily = _required_constant_sleeve_return(data.loc[index, "V10"], data.loc[index, "CASH"], target_ratio, cfg)
        required_cumulative = float("inf") if not math.isfinite(required_daily) else float((1.0 + required_daily) ** len(index) - 1.0)
        actual_static = float((1.0 + static.returns.loc[index]).prod() - 1.0)
        actual_sleeve = 0.5 * data.loc[index, "EQUITY_TREND"] + 0.5 * data.loc[index, "GOLD_TREND"]
        rows.append({
            "window": label,
            "start": start,
            "end": end,
            "observations": int(len(index)),
            "baseline_return": baseline_return,
            "target_return": target_return,
            "required_constant_daily_sleeve_return": required_daily,
            "required_constant_sleeve_cumulative_return": required_cumulative,
            "actual_equal_split_sleeve_cumulative_return": float((1.0 + actual_sleeve).prod() - 1.0),
            "actual_static_strategy_return": actual_static,
            "method": "constant daily sleeve return solved by bisection with financing and initial turnover",
        })
    return pd.DataFrame(rows)


def exact_oracle_family(data: pd.DataFrame, cfg: Config) -> tuple[pd.DataFrame, dict[str, StrategyResult], dict[str, np.ndarray]]:
    oos = common_oos(data, cfg)
    states = overlay_state_grid()
    results: dict[str, StrategyResult] = {}
    paths: dict[str, np.ndarray] = {}
    rows = []
    specifications: Iterable[tuple[str, int | None]] = (
        ("BEST_FIXED_GRID", 0),
        ("EXACT_1_SWITCH_WEALTH", 1),
        ("EXACT_3_SWITCH_WEALTH", 3),
        ("EXACT_6_SWITCH_WEALTH", 6),
        ("EXACT_UNLIMITED_SWITCH_WEALTH", None),
    )
    previous_utility = -math.inf
    for name, switches in specifications:
        path, utility = exact_wealth_path(oos, cfg, switches, states=states)
        if utility + 1e-10 < previous_utility:
            raise RuntimeError("oracle utility monotonicity violation")
        previous_utility = utility
        result = state_path_to_result(data, cfg, oos.index, path, name, states)
        metrics = performance_metrics(result.returns, result.weights[["V10", "EQUITY_TREND", "GOLD_TREND"]].abs().sum(axis=1))
        rows.append({"name": name, "maximum_switches": -1 if switches is None else switches, "realized_switches": count_switches(path), "log_utility": utility, **metrics})
        results[name] = result
        paths[name] = path
    return pd.DataFrame(rows), results, paths


def identified_tail_upper_bound(data: pd.DataFrame, cfg: Config, v10: StrategyResult) -> dict[str, Any]:
    episode = maximum_drawdown_window(v10.returns)
    index = _window_slice_after_peak(v10.returns.index, episode["peak"], episode["trough"])
    frame = data.loc[index]
    path, utility = exact_wealth_path(frame, cfg, None, charge_initial=False)
    upper_ratio = float(math.exp(utility))
    target_return = min(0.0, float(episode["mdd"]) + cfg.target_mdd_improvement)
    target_ratio = 1.0 + target_return
    return {
        "peak": episode["peak"],
        "trough": episode["trough"],
        "observations": int(len(index)),
        "v10_window_ratio": float(1.0 + episode["mdd"]),
        "target_window_ratio": target_ratio,
        "finite_grid_upper_bound_ratio": upper_ratio,
        "upper_bound_passes_target": bool(upper_ratio >= target_ratio - 1e-12),
        "realized_switches": count_switches(path),
        "initial_turnover_charged": False,
        "claim_boundary": "exact terminal-wealth upper bound on finite grid for the identified fixed peak-to-trough window; not a global minimum-MDD oracle",
    }


def _static_history_metrics(history: pd.DataFrame, cfg: Config, state: np.ndarray) -> tuple[float, float, float]:
    q = float(state.sum())
    returns = history["V10"] + state[0] * history["EQUITY_TREND"] + state[1] * history["GOLD_TREND"] - q * (history["CASH"] + cfg.borrow_spread_annual / ANNUALIZATION)
    metrics = performance_metrics(returns)
    return float(metrics["mdd"]), float(metrics["cagr"]), -q


def causal_monthly_selector(data: pd.DataFrame, cfg: Config, horizon: int | None, name: str) -> StrategyResult:
    states = overlay_state_grid()
    zero = _state_index(states, 0.0, 0.0)
    signal = pd.Series(zero, index=data.index, dtype=int)
    current = zero
    previous_month: tuple[int, int] | None = None
    for position in range(cfg.warmup_days, len(data)):
        date = data.index[position]
        month = (date.year, date.month)
        if month != previous_month:
            start = 0 if horizon is None else max(0, position - int(horizon) + 1)
            history = data.iloc[start : position + 1]
            if len(history) >= 20:
                scores = [_static_history_metrics(history, cfg, state) for state in states]
                current = max(range(len(states)), key=lambda i: scores[i])
            previous_month = month
        signal.iloc[position] = current
    executed = signal.shift(cfg.delay).fillna(zero).astype(int)
    oos = common_oos(data, cfg)
    path = executed.reindex(oos.index).to_numpy(dtype=int)
    return state_path_to_result(data, cfg, oos.index, path, name, states)


def causal_selector_family(data: pd.DataFrame, cfg: Config, v10: StrategyResult) -> tuple[pd.DataFrame, dict[str, StrategyResult]]:
    specifications = (
        ("CAUSAL_PAST_20D_DEFENSIVE", 20),
        ("CAUSAL_PAST_60D_DEFENSIVE", 60),
        ("CAUSAL_PAST_120D_DEFENSIVE", 120),
        ("CAUSAL_EXPANDING_DEFENSIVE", None),
    )
    results: dict[str, StrategyResult] = {}
    rows = []
    baseline = performance_metrics(v10.returns)
    for name, horizon in specifications:
        result = causal_monthly_selector(data, cfg, horizon, name)
        metrics = performance_metrics(result.returns, result.weights[["V10", "EQUITY_TREND", "GOLD_TREND"]].abs().sum(axis=1))
        rows.append({
            "name": name,
            "horizon": -1 if horizon is None else horizon,
            "cagr_at_least_v10": bool(metrics["cagr"] >= baseline["cagr"]),
            "mdd_improvement_at_least_8pp": bool(metrics["mdd"] - baseline["mdd"] >= cfg.target_mdd_improvement),
            **metrics,
        })
        results[name] = result
    return pd.DataFrame(rows), results


def _save_strategy(output: Path, result: StrategyResult) -> None:
    safe = result.name.lower()
    pd.DataFrame({"date": result.returns.index, "return": result.returns.values, "equity": result.equity.values}).to_csv(output / f"audit_{safe}_returns.csv.gz", index=False, compression="gzip", float_format="%.12g")
    result.weights.reset_index().rename(columns={result.weights.index.name or "index": "date"}).to_csv(output / f"audit_{safe}_weights.csv.gz", index=False, compression="gzip", float_format="%.12g")
    result.ledger.to_csv(output / f"audit_{safe}_exact_ledger.csv.gz", index=False, compression="gzip", float_format="%.12g")


def run_tail_audit(data: pd.DataFrame, cfg: Config, output: Path) -> dict[str, Any]:
    output.mkdir(parents=True, exist_ok=True)
    v10 = run_v10(data, cfg)
    static = run_static_portable(data, cfg)
    attribution = drawdown_attribution(v10, static)
    required = required_tail_offset(data, cfg, v10, static)
    oracle_table, oracle_results, _ = exact_oracle_family(data, cfg)
    causal_table, causal_results = causal_selector_family(data, cfg, v10)
    upper_bound = identified_tail_upper_bound(data, cfg, v10)

    attribution.to_csv(output / "DRAWDOWN_ATTRIBUTION.csv", index=False, float_format="%.12g")
    required.to_csv(output / "REQUIRED_TAIL_OFFSET.csv", index=False, float_format="%.12g")
    oracle_table.to_csv(output / "TAIL_ORACLE_COMPARISON.csv", index=False, float_format="%.12g")
    causal_table.to_csv(output / "CAUSAL_TAIL_SELECTOR.csv", index=False, float_format="%.12g")
    write_json(output / "IDENTIFIED_TAIL_UPPER_BOUND.json", upper_bound)
    write_json(output / "TAIL_ORACLE_PROTOCOL.json", {
        "audit_version": AUDIT_VERSION,
        "base_version": VERSION,
        "state_step": STATE_STEP,
        "maximum_overlay": cfg.max_overlay,
        "states": overlay_state_grid(),
        "objective": "maximum terminal log wealth with actual financing and turnover; finite-grid exact DP",
        "claim_boundary": "not a continuous-state or global minimum-MDD oracle",
    })
    for result in [*oracle_results.values(), *causal_results.values()]:
        _save_strategy(output, result)

    baseline = performance_metrics(v10.returns)
    oracle_pass = bool(((oracle_table["cagr"] >= baseline["cagr"]) & (oracle_table["mdd"] - baseline["mdd"] >= cfg.target_mdd_improvement)).any())
    causal_pass = bool(((causal_table["cagr"] >= baseline["cagr"]) & (causal_table["mdd"] - baseline["mdd"] >= cfg.target_mdd_improvement)).any())
    if not upper_bound["upper_bound_passes_target"]:
        status = "CURRENT_GRID_LONG_ONLY_OVERLAY_CANNOT_OFFSET_IDENTIFIED_V10_MAX_DRAWDOWN_WINDOW"
    elif causal_pass:
        status = "IMPLEMENTABLE_TAIL_OFFSET_OPPORTUNITY_EXISTS"
    elif oracle_pass:
        status = "TAIL_OFFSET_EXISTS_EX_POST_BUT_IS_NOT_CAUSALLY_PREDICTABLE"
    else:
        status = "TAIL_OFFSET_NOT_OBSERVED_IN_EXACT_WEALTH_ORACLE_FAMILY"
    gate = {
        "audit_version": AUDIT_VERSION,
        "base_version": VERSION,
        "status": status,
        "identified_tail_upper_bound": upper_bound,
        "full_oos_oracle_family_contains_pareto_path": oracle_pass,
        "causal_selector_family_contains_pareto_path": causal_pass,
        "claim_boundary": "failure of the wealth-oracle family is not proof of continuous-state global MDD impossibility unless the identified-window upper bound also fails",
    }
    write_json(output / "V24_FINAL_AUDIT_GATE.json", gate)
    return gate


def verify_tail_audit(output: Path) -> dict[str, Any]:
    required = [
        "DRAWDOWN_ATTRIBUTION.csv",
        "REQUIRED_TAIL_OFFSET.csv",
        "TAIL_ORACLE_COMPARISON.csv",
        "CAUSAL_TAIL_SELECTOR.csv",
        "IDENTIFIED_TAIL_UPPER_BOUND.json",
        "TAIL_ORACLE_PROTOCOL.json",
        "V24_FINAL_AUDIT_GATE.json",
    ]
    failures = [f"missing:{name}" for name in required if not (output / name).exists()]
    if not failures:
        oracle = pd.read_csv(output / "TAIL_ORACLE_COMPARISON.csv")
        utilities = oracle["log_utility"].to_numpy(dtype=float)
        if np.any(np.diff(utilities) < -1e-9):
            failures.append("oracle_utility_nonmonotone")
        causal = pd.read_csv(output / "CAUSAL_TAIL_SELECTOR.csv")
        if len(causal) != 4:
            failures.append("causal_selector_count")
        ledgers = sorted(output.glob("audit_*_exact_ledger.csv.gz"))
        if len(ledgers) < 9:
            failures.append("audit_ledger_count")
        for path in ledgers:
            frame = pd.read_csv(path, compression="gzip")
            if not (frame["net_ppm"] == 1_000_000).all():
                failures.append(f"net_ppm:{path.name}")
            if not (frame["v10_ppm"] == 1_000_000).all():
                failures.append(f"v10_core:{path.name}")
            if (frame["risky_gross_ppm"] > 1_600_000).any():
                failures.append(f"gross_cap:{path.name}")
    result = {"audit_version": AUDIT_VERSION, "passed": not failures, "failures": failures}
    if failures:
        raise RuntimeError(json.dumps(result, indent=2))
    return result


def write_audited_report(path: Path, base_gate: dict[str, Any], audit_gate: dict[str, Any], output: Path) -> None:
    strategy = pd.read_csv(output / "strategy_summary.csv")
    oracle = pd.read_csv(output / "TAIL_ORACLE_COMPARISON.csv")
    causal = pd.read_csv(output / "CAUSAL_TAIL_SELECTOR.csv")
    lines = [
        "# V24 Final Audited Handoff",
        "",
        f"Base protocol: `{VERSION}`  ",
        f"Tail audit: `{AUDIT_VERSION}`",
        "",
        "## Base strategy results",
        "",
        markdown_table(strategy),
        "",
        "## Exact finite-grid wealth oracles",
        "",
        markdown_table(oracle),
        "",
        "## Causal monthly selectors",
        "",
        markdown_table(causal),
        "",
        "## Status",
        "",
        "```text",
        f"BASE_OVERALL: {base_gate.get('overall_status')}",
        f"TAIL_AUDIT:   {audit_gate.get('status')}",
        "```",
        "",
        "## Claim boundary",
        "",
        str(audit_gate.get("claim_boundary")),
        "",
        "This package removes the optional `tabulate` dependency. All Markdown tables are generated by the deterministic built-in renderer in `v24_tail_audit.py`.",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def refresh_manifest(output: Path) -> dict[str, Any]:
    manifest = output_manifest(output, exclude={"OUTPUT_MANIFEST.json"})
    write_json(output / "OUTPUT_MANIFEST.json", manifest)
    return manifest

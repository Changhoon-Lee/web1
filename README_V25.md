# V25 Dual Causal Defense

V25 implements two distinct defensive mechanisms without claiming future-return certainty.

## Path A — Causal V10 core reduction

The aligned V10 core is moved only among `0 / 25 / 50 / 75 / 100%` exposure states. The controller uses information available through close `t`, schedules the decision for `t+2`, and computes the maximum allowed state from:

- a 29% high-water drawdown floor,
- the worst observed 3-day loss over the expanding lookback,
- 3-day 5% expected shortfall,
- a 99% Gaussian loss estimate,
- a hard 25% loss floor.

Risk reductions are immediate in signal space. Recovery is one state at a time after 20 consecutive qualifying days.

## Path B — Negative-tail-beta engine substitution

Any input column beginning with `TAIL_` is treated as a candidate engine. A candidate is official only when the monthly expanding audit confirms:

- negative beta on the worst 5% of V10 days,
- positive mean return on those tail days,
- positive mean return on the 20 worst V10 days,
- positive expanding CAGR,
- immutable point-in-time provenance and a declared cost model.

Reduced V10 exposure is replaced by qualified tail engines. The strategy does not borrow:

```text
V10 + qualified tail engines + cash = 100% net
risky gross <= 100%
```

If no engine qualifies, the reduced allocation remains in cash.

## Input

Required daily decimal-return columns:

```csv
date,V10,CASH
2021-01-01,0.0012,0.00008
```

Candidate engines are optional columns with the prefix `TAIL_`:

```csv
date,V10,CASH,TAIL_TREASURY_TREND,TAIL_MANAGED_FUTURES,TAIL_CRISIS_FX
```

Values must be decimal daily returns, not prices or whole percentages.

## Provenance

Official tail qualification requires a JSON file such as:

```json
{
  "engines": {
    "TAIL_TREASURY_TREND": {
      "tradable": true,
      "point_in_time": true,
      "source_sha256": "...",
      "retrieved_at": "2026-07-20T00:00:00Z",
      "cost_model": "17bp one-way plus instrument financing"
    }
  }
}
```

Set:

```bash
export V25_ENGINE_RETURNS_FILE="/absolute/path/v25_engine_returns.csv.gz"
export TAIL_PROVENANCE_FILE="/absolute/path/tail_provenance.json"
```

## Run on macOS

```bash
chmod +x RUN_V25_EVERYTHING.command V25_*.command
./RUN_V25_EVERYTHING.command
```

The command creates:

```text
v25_results/FINAL_REPORT.md
v25_results/FINAL_GATE.json
v25_results/strategy_summary.csv
v25_results/bootstrap_results.csv
v25_results/*_exact_ledger.csv.gz
v25_results/OUTPUT_MANIFEST.json
runtime/V25_Dual_Causal_Defense_Handoff.zip
```

## Interpretation

A historical pass is capped at `*_NEEDS_NEW_OOS`. The package proves code-level and protocol-level invariants, not future market performance. The drawdown floor is conditional on the registered stress set and cannot protect against losses outside that set or losses arriving before the delayed order executes.

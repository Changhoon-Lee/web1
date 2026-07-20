# V27 Deribit Long Gamma

V27 is a fail-closed research package for a real options-based lightning-rod hypothesis:

```text
Buy a same-strike ATM call and put
Pay executable asks
Delta-hedge with BTC perpetual
Receive executable bids on exit
Charge option fees, hedge fees, spread, funding, and delivery fees
Reject sparse or non-contiguous data
```

It does not convert the rejected V26 spot/perpetual FOLLOW/FADE rules into a synthetic option claim. It evaluates actual option premiums and Greeks.

## One-command Mac run

```bash
chmod +x RUN_V27_EVERYTHING.command V27_*.command

# Preferred: point at existing Tardis options_chain files
export V27_OPTIONS_DATA_DIR="/absolute/path/to/deribit/options_chain"

# Or permit the package to download continuous Tardis data
export TARDIS_API_KEY="your-key"
export V27_FROM="2022-01-01"
export V27_TO="2026-07-20"

./RUN_V27_EVERYTHING.command
```

The completed handoff is written to:

```text
runtime/V27_Deribit_Long_Gamma_Handoff.zip
```

## No historical-data key

Without `TARDIS_API_KEY`, the package downloads the publicly available first-day-of-month samples. Those files validate parsing, pricing units, Greeks, fees, causal ledger logic, and deterministic outputs. They cannot pass the economic gate because the active-day coverage and maximum-gap tests fail.

The result will be:

```text
INSUFFICIENT_CONTIGUOUS_OPTIONS_DATA
```

This is intentional. The package never interpolates missing option chains and never treats separated monthly samples as a continuous delta-hedging history.

## Forward OOS recorder

A public Deribit WebSocket recorder is included:

```bash
./V27_RECORD_FORWARD_OOS.command
```

It subscribes only to active BTC options around the current index and saves new point-in-time option-chain snapshots. It cannot backfill prior dates.

## Frozen primary policy

- BTC ATM straddle, identical strike and expiry
- target 30 DTE; allowed 21–45 DTE
- close or roll at 7 DTE or every 7 days
- 5% premium budget
- ask entry and bid exit
- 30-minute snapshots
- delta band 0.10 per contract
- hedge at least every 30 minutes
- one-bar execution latency
- current standard option fee formula
- 5 bp perpetual taker fee plus 1 bp half-spread
- conservative 3% annual funding charge on absolute hedge notional

No optimizer is included. The package does not search DTE, hedge bands, roll periods, or premium budgets after observing results.

## Fixed diagnostics

```text
UNHEDGED_STRADDLE
COST_2X
COST_3X
LATENCY_2_BARS
LATENCY_3_BARS
```

A historical pass requires every registered stress to retain terminal wealth above one, positive primary CAGR, no liquidation, and limited return concentration. Any pass remains capped at `NEEDS_NEW_OOS`.

## Main outputs

```text
v27_results/FINAL_GATE.json
v27_results/FINAL_REPORT.md
v27_results/DATA_COVERAGE.json
v27_results/strategy_summary.csv
v27_results/*_exact_ledger.csv.gz
v27_results/*_trades.csv.gz
v27_results/INPUT_MANIFEST.json
v27_results/OUTPUT_MANIFEST.json
```

## Research boundary

V27 can reject or provisionally pass this specific ATM-straddle gamma-scalping policy. It cannot prove that every possible options strategy is impossible. A new hypothesis requires a new pre-registration and genuinely new data or economic construction.

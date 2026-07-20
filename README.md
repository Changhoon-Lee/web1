# V27.1 Open-Free Deribit Long-Variance Lab

This package uses **only unauthenticated, free Deribit public market-data endpoints**. No Tardis, paid archive, private account endpoint, API key, or subscription is used.

## What it can verify

1. Historical BTC DVOL versus the next 30-day realized variance, using non-overlapping monthly anchors.
2. A Black–Scholes/DVOL synthetic 30-day ATM straddle with daily delta hedging.
3. Base, unhedged, 2× cost, and 3× cost diagnostics.
4. Exact accounting ledgers, input/output SHA-256 manifests, and deterministic ZIP creation.
5. Real public bid/ask/Greeks collection from now onward using the Deribit public WebSocket.

## What it cannot claim

Deribit public endpoints do not provide a complete historical option bid/ask chain. Therefore the historical straddle is a **model-based feasibility/falsification diagnostic**, not an executable option backtest. The code permanently enforces:

```text
BLOCKED_NO_HISTORICAL_OPTION_BID_ASK_CHAIN
```

A positive model result is at most:

```text
OPEN_FREE_MODEL_FEASIBILITY_POSITIVE_EXECUTION_UNVERIFIED
```

## One-command Mac execution

```bash
chmod +x *.command
./RUN_V271_EVERYTHING.command
```

Outputs:

```text
v271_results/FINAL_REPORT.md
v271_results/FINAL_GATE.json
v271_results/monthly_variance_anchors.csv
v271_results/*_exact_ledger.csv.gz
v271_results/OUTPUT_MANIFEST.json
runtime/V27_1_Open_Free_Deribit_Handoff.zip
```

## Public forward chain recorder

```bash
export V271_RECORD_MINUTES=1440
./V271_RECORD_PUBLIC_CHAIN.command
```

This records active BTC options around ATM, BTC perpetual ticker data, DVOL, bid/ask, Greeks, and funding through public WebSocket channels. No authentication is required.

## Interpretation

- `OPEN_FREE_DATA_INSUFFICIENT`: not enough public DVOL/index history.
- `OPEN_FREE_LONG_GAMMA_MODEL_REJECTED`: the model-based long-variance and stressed delta-hedge diagnostics do not survive.
- `OPEN_FREE_MODEL_FEASIBILITY_POSITIVE_EXECUTION_UNVERIFIED`: the model survives, but historical execution remains unverified.
- `BLOCKED_NO_HISTORICAL_OPTION_BID_ASK_CHAIN`: always retained for deployment claims.

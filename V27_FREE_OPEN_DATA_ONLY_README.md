# V27 Free/Open-Data-Only Deribit Long Gamma

This package is the free-data-only execution profile for the pre-registered V27 Deribit long-gamma study.

## What it does

- Uses only Deribit's public JSON-RPC endpoints.
- Requires no exchange account, API key, paid data subscription, or private credential.
- Records executable option bid/ask quotes, IV, Greeks, underlying price, and open interest prospectively.
- Selects one same-expiry/same-strike ATM call and put inside the frozen 21–45 DTE range.
- Writes deterministic, checksum-tracked compact option-chain files.
- Runs the unchanged V27 accounting engine only after the continuity gate passes.
- Produces a verified handoff ZIP even when data are insufficient; in that case it blocks all economic claims.

## What it never does

- It never interpolates missing historical option quotes.
- It never backfills current Greeks into old timestamps.
- It never treats mark price as an executable entry or exit.
- It never accepts paid-data credentials or private Deribit credentials.
- It never annualizes a sparse or discontinuous sample.

## One-command use

```bash
chmod +x RUN_V27_FREE_ONLY.command V27_FREE_*.command
./RUN_V27_FREE_ONLY.command
```

This performs tests, records a public snapshot, audits coverage, runs the economic engine only if eligible, verifies outputs, and creates:

```text
runtime/V27_Free_Open_Data_Only_Handoff.zip
```

## Continuous free collection

Run in a Terminal session or service:

```bash
./V27_FREE_RECORD_CONTINUOUS.command
```

A one-hour recording block can be run with:

```bash
V27_FREE_RECORD_MINUTES=60 ./V27_FREE_RECORD.command
```

The economic gate requires at least 90 active days, 80% active-day coverage, and no timestamp gap above 48 hours. Until then the required status is:

```text
FREE_OPEN_DATA_CONTINUITY_NOT_READY
```

## Data source

The recorder calls only these public Deribit methods:

- `public/get_index_price`
- `public/get_instruments`
- `public/ticker`

The resulting file manifest records source, endpoint, file hashes, sizes, and an aggregate tree hash.

## Interpretation

A successful software verification means the collector, continuity gate, accounting invariants, and deterministic packaging work. It does not mean long gamma is profitable. A future historical pass remains capped at `HISTORICAL_DERIBIT_LONG_GAMMA_PASS_NEEDS_NEW_OOS`.

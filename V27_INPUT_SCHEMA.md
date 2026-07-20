# V27 Input Schema

V27 consumes normalized Deribit option-chain snapshots. The preferred source is the Tardis `options_chain` daily dataset with grouped symbol `OPTIONS`.

## Required columns

```text
timestamp
symbol
type
strike_price
expiration
bid_price
ask_price
underlying_price
```

Accepted aliases are implemented in `src/v27_core.py`. Timestamps may be ISO strings or epoch seconds, milliseconds, microseconds, or nanoseconds. They are normalized to UTC.

## Strongly recommended columns

```text
mark_price
mark_iv
bid_iv
ask_iv
open_interest
delta
gamma
vega
theta
underlying_index
bid_amount
ask_amount
```

When `delta` is absent, V27 recomputes Black-Scholes delta from `mark_iv`. If both delta and usable IV are absent, the timestamp cannot generate a hedge signal.

## Pricing units

- Inverse BTC/ETH options: bid, ask, and mark are quoted in the base coin. V27 converts them to USD using the row's underlying price.
- Symbols containing `_USDC-`: option prices are interpreted as USD/USDC linear premiums.
- Prices, percentages, and IV units must match the source schema. Tardis `mark_iv`, `bid_iv`, and `ask_iv` are percentage values, so V27 divides by 100 only when recomputing Greeks.

## Executability rules

- Entries always pay the ask.
- Exits always receive the bid.
- Missing bid or ask is not replaced by mark price.
- Stale quotes older than the configured age limit cannot be traded.
- Monthly free sample files are useful for parser and accounting validation only. They fail the contiguous-data gate.

## Environment variables

```bash
export V27_OPTIONS_DATA_DIR="/absolute/path/to/options_chain_files"
export V27_CURRENCY="BTC"
export V27_FROM="2022-01-01"
export V27_TO="2026-07-20"
export TARDIS_API_KEY="..."       # optional; needed for continuous historical download
```

The downloader writes a provenance manifest with file sizes and SHA-256 hashes.

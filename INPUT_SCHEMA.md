# Input schema

Required columns: `date`, `GROWTH_CRYPTO`, `EQUITY_TREND`, `GOLD_TREND`, `V10`.
Optional: `CASH`.

Each engine column is the net or gross daily decimal return of a fully defined causal shadow engine on a common calendar. The lab applies its own portfolio turnover and leverage financing costs; do not include those portfolio-level costs twice.

The input must be immutable and accompanied outside this package by source paths, source URLs, retrieval timestamps, adjustment methods, hashes and the official V10 decision-ledger hash.

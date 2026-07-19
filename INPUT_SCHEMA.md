# Input schema

Required columns: `date`, `GROWTH_CRYPTO`, `EQUITY_TREND`, `GOLD_TREND`, `V10`. Optional: `CASH`.

Each engine column is a causal daily decimal return on a common calendar. The lab applies portfolio turnover and leverage financing costs; do not include those portfolio-level costs twice.

The input must be accompanied externally by source paths, URLs, retrieval timestamps, adjustment methods, file hashes and the official V10 decision-ledger hash.

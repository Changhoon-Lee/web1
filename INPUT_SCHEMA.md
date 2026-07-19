# Input schema and accounting contract

## Required columns

```text
date
GROWTH_CRYPTO
EQUITY_TREND
GOLD_TREND
V10
```

Optional: `CASH`.

All return columns are decimal daily **funded sleeve total returns** on one common calendar. Example: `0.01` means +1% for that day. Do not provide prices or whole percentages.

The portfolio accounting is:

```text
portable_return
= 1.00 * V10
+ equity_overlay * EQUITY_TREND
+ gold_overlay * GOLD_TREND
- total_overlay * CASH
- total_overlay * borrow_spread / 365.25
- portfolio_turnover_cost
```

Therefore:

- `EQUITY_TREND` and `GOLD_TREND` must be funded total-return sleeves, not already cash-subtracted excess returns.
- Engine-level transaction costs may be included inside each engine return.
- Do not include V24 portfolio overlay turnover or borrowing spread inside the engine returns; V24 applies those itself.
- `V10` must be the authoritative V10 daily return on the same aligned dates.
- Weekend and ETF-holiday handling must be resolved upstream and documented in the external provenance manifest.

## External provenance required

The package records the input file SHA-256 but cannot prove its upstream creation. Preserve externally:

- source URLs and paths
- retrieval timestamps
- adjusted/total-return methodology
- timezone and holiday alignment rules
- engine code/version hashes
- official V10 full-history ledger hash
- aligned V10 daily-return hash

`V10_ALIGNED_COMMON_OOS` and `V10_FULL_HISTORY` are different evaluation identities and must never be merged in one metric label.

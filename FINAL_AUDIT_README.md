# V24 Final Audited Handoff

This package preserves the V24 portable-overlay research result and adds a final tail-offset opportunity audit.

## One-command Mac execution

```bash
chmod +x *.command
export ENGINE_RETURNS_FILE="/absolute/path/engine_returns.csv.gz"
./RUN_EVERYTHING.command
```

The final single handoff file is written to:

```text
runtime/V24_Final_Audited_Handoff.zip
```

## Input

Required daily decimal-return columns:

```text
date,GROWTH_CRYPTO,EQUITY_TREND,GOLD_TREND,V10,CASH
```

`CASH` is optional and defaults to zero. The input must be a common-calendar, point-in-time causal engine-return table. Portfolio turnover and borrowing costs are applied by this package and must not be included twice.

## Base strategies

- `V10_ALIGNED_COMMON_OOS`
- `STATIC_PORTABLE_30_30`: V10 100% + Equity 30% + Gold 30% - Cash 60%
- dynamic overlay without online split
- dynamic overlay with bounded online split
- equal-average controls

## Final tail audit

- deterministic Markdown output with no `tabulate` dependency
- maximum-drawdown and 20/60/120-day window attribution
- exact finite-grid wealth DP with 0/1/3/6 or unlimited switches
- identified V10 peak-to-trough terminal-wealth upper bound
- causal 20/60/120-day and expanding monthly defensive selectors
- exact integer ledgers for every oracle and selector
- strict claim boundaries in `AUDIT_PROTOCOL.json`

The wealth oracles are exact only on the preregistered 0.10 overlay grid. They are not continuous-state or global minimum-MDD optimizers.

## Key results

```text
results/FINAL_REPORT.md
results/FINAL_GATE.json
results/V24_FINAL_AUDIT_GATE.json
results/DRAWDOWN_ATTRIBUTION.csv
results/REQUIRED_TAIL_OFFSET.csv
results/TAIL_ORACLE_COMPARISON.csv
results/CAUSAL_TAIL_SELECTOR.csv
results/IDENTIFIED_TAIL_UPPER_BOUND.json
results/OUTPUT_MANIFEST.json
```

The package refuses to create the final handoff ZIP unless the base manifest, base ledgers, audit ledgers, oracle monotonicity and final audit schema all verify.

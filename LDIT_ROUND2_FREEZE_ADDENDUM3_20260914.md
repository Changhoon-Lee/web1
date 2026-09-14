# LDIT Round-2 Freeze Addendum 3

Committed before APiCS language-value outcomes were inspected.

Deterministic APiCS parser/tie rules:
- nearest-set equality tolerance: absolute `1e-12`;
- use nonempty `Code_ID` as category key, otherwise nonempty literal `Value`;
- duplicate language–feature–category rows have numeric Frequency summed before normalization;
- if every retained category has finite nonnegative Frequency and total >0, normalize aggregated frequencies; otherwise use uniform mass over distinct retained categories;
- rows with neither category key nor nonempty Value are ignored;
- the holdout script must assert that IDs 1–130 are exactly 130 `Type=primary` features with nonempty `Area`; if not, the frozen holdout is inconclusive and no post-outcome replacement selector is allowed;
- no language-value row may be manually inspected before the holdout script is frozen and committed.

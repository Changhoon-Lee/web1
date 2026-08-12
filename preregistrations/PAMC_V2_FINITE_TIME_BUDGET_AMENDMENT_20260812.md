# PAMC v2 finite-time budget amendment

Date: 2026-08-12 (Asia/Singapore)

This is a transparent protocol repair after the v1 result committed at `ab49fde39c0bb433dfb0bf1c8197929f4765398c`. It is not an independent replication and must never be described as one.

No input, preprocessing, operator, forcing, threshold, safe/fail parameter, dominant mode, relaxation parameter, or spectral prediction is changed. The complete frozen prediction payload remains SHA-256 `265e93d259ff115411bf299a798f582b7523704eef1081167f28537d2e5e2b2e` and GitHub commit `1c81262a6befc49bf126c418174ecde504e2dd8e`.

The v1 design contained two implementation mistakes:

1. it chose fixed iteration counts without checking them against its own certified contraction rates;
2. the prediction builder swapped the written family tolerance rule by using dimension rather than family identity.

The authoritative written tolerances are restored: `5e-6` for F1/F2 and `2e-4` for F3.

For a frozen contraction bound `r<1` and zero initialization, the normalized initial fixed-point error is exactly one. The theorem gives `||e_k||_G/||e_0||_G <= r^k`. The corrected budget is therefore computed only from the already-public prediction by

`N = ceil(log(tolerance)/log(r)) + 10`.

The resulting budgets are frozen as:

- F1: safe 61, repaired 68, fail 120;
- F2: safe 42, repaired 34, fail 80;
- F3: safe 1668, repaired 1320, fail 120.

All other v1 gates remain unchanged. Passing this amendment demonstrates the finite-time consequence of the original frozen spectral prediction; it does not erase the v1 failure.

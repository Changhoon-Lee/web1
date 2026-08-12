# FPPL T3 nonnegative-Rayleigh scope amendment

Date: 2026-08-13 (Asia/Singapore)

Design commit: `d21524c164f848926d614ffd55a616d6f94c40bf`
Prediction commit: `32383ce9e52da42d1db81d24b1c5596d63cae7f5`

## Defect found by post-prediction theorem red team

The design stated, for a completely-positive matrix zero pattern and arbitrary range basis `U`, that the worst clique-supported nonnegative factor has value

`lambda_max(U_S^T D_S^{-1} U_S)`.

This is too broad. A CP factor is entrywise nonnegative, while the leading generalized eigenvector of `U_S U_S^T` relative to `D_S` need not be nonnegative. The unconstrained eigenvalue can therefore overestimate the physical nonnegative-factor optimum.

## Correct general theorem

For graph zero pattern `G`, every nonnegative CP factor is supported on a clique. The exact matrix-pattern-only phase constant is

`kappa_G^+ = max_(S clique of G) sup_(0 != y >= 0, supp y subset S) (y^T U U^T y)/(y^T D y)`.

For a given clique, this is a nonnegative generalized Rayleigh-quotient problem. It equals

`lambda_max(U_S^T D_S^{-1} U_S)`

when a top generalized eigenvector can be chosen nonnegative; a sufficient condition is that `D_S^{-1/2} U_S U_S^T D_S^{-1/2}` is entrywise nonnegative, by Perron--Frobenius.

The uniform rank-one reduction used for the exact complexity result has `U=n^{-1/2} 1`, so the condition holds and

`kappa_G^+=omega(G)/n`

remains exact. The coNP-hard robust-stability reduction and NP-complete destabilizing-factor witness are unchanged.

## Scope and authority

This correction does not alter the factor-resolved T1 theorem, the support-family T2 theorem for signed/native factors, the identical-normal provenance theorem, the attenuation theorem, any PIV operator, prediction, threshold, trajectory, or repair. The original unrestricted T3 formula is retained as a failed claim and is not used in the final authority chain.

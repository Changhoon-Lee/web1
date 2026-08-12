# PAMC F4 clean prospective replication design

Date: 2026-08-12 (Asia/Singapore)

This replication is created after the disclosed v1 SPE10 finite-iteration failure and after the v2 protocol amendment. It is therefore not evidence that the amendment was conceived blindly. Its purpose is narrower: test the corrected theorem-derived budget rule on a new operator and new public scientific input in one first-shot design → prediction → trajectory sequence.

No trajectory may be executed before a public prediction commitment records all input/operator hashes, the PAMC defects, threshold bracket, safe/fail points, dominant mode, spectral rates, fixed-point-preserving repair, and theorem-derived iteration counts.

## Public input and preprocessing

Use the `statsmodels.datasets.sunspots` annual sunspot-activity table (years 1700–2008). Freeze the first 250 records as training and the remaining 59 as held-out forcing. Build an 11-phase solar-cycle state. Each phase has two channels: training-standardized activity and training-standardized first difference. Training statistics alone define the graph, metrics, and physics. The held-out phase mean enters only the affine forcing.

## Operator

Build an 11-node open scientific phase graph consisting of the 11-cycle plus fixed chords `(0,5)`, `(2,7)`, and `(4,9)`. Edge weights are `0.40 + 0.60 abs(training phase correlation)`. Use lazy reversible spatial mixing with `tau=0.28`.

Use the fixed positive nonsymmetric channel mixer

`T=[[0.92,0.08],[0.16,0.84]]`

with channel metric `C_ch=diag(2,1)`. Set

`W=P kron T`, `M=D kron C_ch`, `L=D^{-1} kron I_2`.

The physics normal is the sum of training-only diagonal observation precision, channel-separate cycle second-difference penalties with weights `(0.12,0.05)`, and ridge `0.04`. All channel factors are diagonal in the `C_ch` eigenbasis. A January/phase-zero cross-channel rank-one factor is reserved only as a symmetry breaker and is not used to tune the compatible threshold.

## Frozen update and predictions

Use the affine iteration

`x_{k+1}=W[x_k-beta L(Bx_k-h)]`.

Predict the first `-1` crossing from the generalized symmetric pencil `G+M-beta MLB`, with `G=M W^{-1}`. Freeze `beta_safe=0.8 beta_star` and `beta_fail=1.2 beta_star`. At the fail point freeze the exact floating spectral interval and minimax fixed-point-preserving scalar relaxation.

Unlike v1, the iteration counts must be included in the prediction commitment and computed before trajectories as

`N=ceil(log(tolerance)/log(r))+10`

using tolerance `5e-6` and the frozen safe/repaired contraction rates. The fail run uses the smaller of 100 iterations and the number needed for the dominant-mode error to grow by at least `10^4`.

## Confirmatory gates

1. input, preprocessed and operator hashes match the public prediction commitment;
2. full-BHMC defect exceeds `1e-8`, while PAMC mixing and physics residuals are below `1e-10`;
3. safe and repaired runs reach the direct fixed point within `5e-6` in the G norm using no more than the frozen budgets;
4. fail dominant-mode growth and observed rate agree with prediction to relative error below `2e-8`;
5. repair preserves the fail fixed point to relative error below `1e-10`;
6. native held-out phase-state residual decreases by at least `10^3` in safe and repaired runs and diverges in the fail run;
7. the cross-channel breaker has a nonzero commutator with `ML`.

No failed gate may be relabeled. Any change after trajectory execution makes the run exploratory.

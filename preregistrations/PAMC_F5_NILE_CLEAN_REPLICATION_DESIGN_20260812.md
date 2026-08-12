# PAMC F5 Nile hydrology clean replication design

Date: 2026-08-12 (Asia/Singapore)

This is a new-input clean prospective computational replication following the disclosed F4 gate-design failure. It does not erase either prior failure. Its purpose is to test a corrected consequence protocol whose finite-time and native-science targets are logically implied by the frozen direct fixed point and the PAMC contraction law.

No iterative trajectory may be executed before a public prediction commitment records input/operator hashes, closure defects, threshold, safe/fail/repair spectra, theorem-derived iteration budgets, direct-fixed-point hydrological metrics, and the expected stationary residual targets.

## Input and split

Use the `statsmodels.datasets.nile` annual Nile-flow table (100 annual records). Freeze the first 60 years as training and the final 40 years as held-out hydrological observations. Construct a 40-node open time chain. Each node has two channels: training-standardized annual volume and training-standardized annual increment. Training statistics alone determine metrics and regularization. Held-out values enter only the affine forcing and frozen native target metrics.

## Operator

Use an open time-chain graph with unit nearest-neighbor edges and three fixed long-range edges `(0,10)`, `(10,20)`, `(20,30)` of weight `0.35`. Use lazy reversible spatial mixing with `tau=0.30`.

Use the positive nonsymmetric channel mixer

`T=[[0.94,0.06],[0.18,0.82]]`

with channel metric `C_ch=diag(3,1)`. Set `W=P kron T`, `M=D kron C_ch`, and `L=D^{-1} kron I_2`.

Physics is the sum of training-only channel observation precision, open-chain second-difference penalties `(0.10,0.035)`, and ridge `0.05`. All physics factors commute with `ML=I kron C_ch`. The affine forcing is the observation-normal applied to the held-out level/increment state.

A local cross-channel rank-one observation at the first held-out year is reserved as a symmetry breaker and is not used to tune the compatible threshold.

## Frozen phase and repair prediction

Use `x_{k+1}=W[x_k-beta L(Bx_k-h)]`.

Compute `G=M W^{-1}`. Predict the first `-1` crossing from `G+M-beta MLB`, freeze `beta_safe=0.8 beta_star`, `beta_fail=1.2 beta_star`, the fail spectral interval, the dominant mode, and the minimax fixed-point-preserving scalar relaxation.

The safe and repair iteration counts must be frozen before trajectories as

`N=ceil(log(5e-6)/log(r))+10`.

The fail count must be frozen as the smaller of 100 and the number sufficient for predicted dominant-mode growth of at least `10^4`, plus ten iterations.

## Native consequence targets

Before trajectories, solve the safe and fail affine fixed-point equations directly and freeze:

- held-out level-channel RMSE against the actual Nile volumes in standardized and physical units;
- held-out increment-channel RMSE;
- observation-normal residual;
- fixed-point stationary-equation residual;
- hashes of the direct fixed points.

The confirmatory trajectory does not require a regularized fixed point to interpolate observations. It must instead reproduce the frozen direct-fixed-point native metrics within relative error `1e-6`, while its stationary-equation residual and G-norm fixed-point error meet the theorem-derived tolerance. The fail run must diverge at the frozen dominant rate and its scientific metrics must depart from the frozen fail fixed point by the predicted growing error.

## Gates

1. all public hashes and commit ancestry match;
2. PAMC residuals below `1e-10`, full-BHMC defect above `1e-8`;
3. safe/repaired G-error below `5e-6` within frozen budgets;
4. safe and repaired native metrics agree with their respective direct fixed-point metrics to relative error below `1e-6`;
5. fail dominant rate relative error below `2e-8` and growth at least `10^4` or 99% of the frozen finite-horizon prediction;
6. scalar repair preserves the fail fixed point below `1e-10` relative;
7. the local cross-channel breaker has nonzero `ML` commutator;
8. no operator, metric, forcing, threshold, budget, native target, or tolerance changes after the public prediction commit.

Any failed gate remains failed. A serialization-only implementation error may be corrected only if all numerical payloads and gate definitions remain byte-identical and the incident is logged.

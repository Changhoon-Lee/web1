# Factor-Graph Metric Closure and Coherence Acceleration — clean CO2 replication design

Date: 2026-08-12 (Asia/Singapore)

Parent authority artifact:
`NCS_PHYSICS_ALGEBRA_METRIC_CLOSURE_RESULT_20260812_v1R.zip`

Parent SHA-256:
`d43d4284babe5856247c129f829147673e9f6edb7456b3c4ad9c8c7255b85a95`

This campaign is designed after the parent PAMC campaign and after its disclosed SPE10 and Sunspot protocol failures. It is therefore not evidence that the new factor-connectivity theorem or finite-time consequence protocol was conceived blindly. Its narrower confirmatory purpose is to test, on a new public scientific input and a new operator, a first-shot sequence from a public design commitment to a public numerical prediction commitment and only then to trajectories.

No CO2 data may be loaded, inspected, summarized, plotted, or used numerically before this design commitment is committed. No iterative trajectory may be executed before the second public prediction commitment.

## Frozen public input and split

Use the official `statsmodels.datasets.co2` weekly atmospheric CO2 record from Mauna Loa. Preserve the source index and values exactly as delivered by the installed statsmodels dataset loader and freeze their canonical SHA-256 after loading.

Missing observations are filled by time interpolation followed by nearest endpoint filling. Let `N` be the number of resulting weekly observations. The first `floor(0.70 N)` observations form the training segment and the remaining observations form the held-out forcing segment. Training statistics alone define all graph weights, local metrics, physics factors, and regularization parameters. Held-out values enter only the affine forcing and frozen scientific target metrics.

Construct a 52-phase seasonal state. Each phase has two channels:

1. training-standardized CO2 level;
2. training-standardized first weekly difference.

For each segment, aggregate observations by zero-based week-of-year phase `index mod 52`. Empty phases, if any, use the global training mean for operator construction and the nearest available held-out phase mean for forcing only.

## Frozen scientific operator

Build a 52-node cycle with fixed chords `(0,13)`, `(13,26)`, `(26,39)`, and `(39,0)`. For every graph edge `(i,j)`, set the symmetric spatial affinity to

`0.40 + 0.60 exp(-abs(mu_i-mu_j)/s)`

where `mu_i` is the two-channel training phase mean reduced to its Euclidean norm and `s` is the median positive edge difference, with `s=1` only if all differences vanish. Let `A` be this affinity matrix, `D=diag(A 1)`, and use the lazy reversible spatial walk

`P=(1-tau)I + tau D^{-1}A`, with `tau=0.30`.

Use the positive nonsymmetric channel mixer

`T=[[0.93,0.07],[0.21,0.79]]`

and channel metric `C_ch=diag(3,1)`, for which `C_ch T=T^T C_ch`.

Set

`W=P kron T`,
`M=D kron C_ch`,
`L=D^{-1} kron I_2`,
`C=M L=I_52 kron C_ch`,
`G=M W^{-1}`.

The physics normal is assembled as an independently weighted local factor family. Its nominal member is the sum of:

- coordinate observation factors in both channels, with phase/channel weights equal to inverse training phase variances clipped to `[0.25,4]` after normalization by their median;
- channel-separate 52-cycle first-difference factors, with nominal weights `0.10` for level and `0.035` for weekly difference;
- coordinate ridge factors of weight `0.04` in both channels.

Every admissible factor weight varies independently in the closed interval `[0.8 w_nominal, 1.2 w_nominal]`. The level and weekly-difference factor supports are disjoint in channel coordinates. Consequently, before any data are loaded, the factor-support hypergraph is predicted to have exactly two full-span connected components and its compatible symmetric closure cone is predicted to have dimension two. A single reserved cross-channel factor supported on phase zero with vector `e_(0,level)+e_(0,difference)` is not part of the compatible family; when added, it is predicted to merge the two sectors and reduce the factor-compatible commutant dimension from two to one.

The strict-extension condition is frozen as

`||W L-(W L)^T||_F / ||W L||_F > 1e-8`.

## Frozen theorem-level predictions

For the nominal compatible physics normal `B`, use the affine iteration

`x_(k+1)=W [x_k-beta L(B x_k-h)]`.

The second public commitment, made before any trajectory, must record:

- input, preprocessed-data, factor-list, operator, forcing, and direct-fixed-point hashes;
- factor count, state dimension, factor-support component count and component sizes;
- exact predicted component count after adding the reserved bridge;
- PAMC mixing and physics residuals and the full-BHMC defect;
- the first `-1` threshold interval from `G+M-beta M L B`;
- `beta_safe=0.8 beta_star` and `beta_fail=1.2 beta_star`;
- safe and fail generalized spectral intervals and spectral radii;
- the fail dominant eigenvector hash and phase/channel mode descriptor;
- the fixed-point-preserving optimal scalar relaxation `alpha_star` and contraction rate `r_scalar`;
- the degree-varying Chebyshev semi-iteration spectral interval for `A=I-P_fail`, its predicted minimax error bound, and a theorem-derived iteration budget;
- a theorem-derived scalar-relaxation iteration budget using the same fixed-point tolerance;
- the direct fixed-point native metrics for both the safe and fail equations.

Use fixed-point tolerance `5e-6` in the G norm. For zero initialization, freeze scalar and Chebyshev budgets as the smallest positive integer whose certified worst-case polynomial bound is below `5e-6`, plus ten guard iterations. The fail dominant-mode run uses the smaller of 100 iterations and the count sufficient for predicted growth by at least `10^4`, plus ten guard iterations.

The static Chebyshev method must use the standard three-term semi-iteration recurrence on the fixed fail equation and preserve exactly the same affine fixed point. It may use only the frozen endpoint bounds of the self-adjoint fail operator. No conjugate-gradient residual adaptation or trajectory-dependent parameter change is permitted.

## Frozen confirmatory gates

After the public prediction commitment, one confirmatory runner must establish all of the following without changing any frozen numerical object, tolerance, or iteration count:

1. all public commit ancestry and SHA-256 values match;
2. the factor-support union-find algorithm returns two components for the compatible family and one after the reserved bridge;
3. a dense commutant calculation on the 104-dimensional state agrees with the factor graph in dimension and sector projectors to relative residual below `1e-10`;
4. the PAMC mixing and physics residuals are below `1e-10`, while the full-BHMC defect exceeds `1e-8`;
5. the safe affine iteration reaches its frozen direct fixed point within `5e-6` in the G norm;
6. the unrelaxed fail iteration grows at the frozen dominant spectral rate to relative error below `2e-8` on the frozen dominant eigenvector and by at least `10^4` or 99% of its finite-horizon prediction;
7. the frozen scalar repair reaches the fail direct fixed point within `5e-6` in the G norm;
8. the frozen static Chebyshev semi-iteration reaches the same fail direct fixed point within `5e-6` and uses strictly fewer predicted and observed iterations than scalar relaxation;
9. scalar and Chebyshev fixed-point discrepancies relative to the direct fail solution are below `1e-10` when their affine equations are evaluated exactly at the direct solution;
10. safe, scalar-repaired, and Chebyshev trajectories reproduce their frozen direct-fixed-point CO2 level RMSE, weekly-difference RMSE, and stationary-equation residual to relative error below `1e-6`;
11. the reserved cross-channel bridge has nonzero commutator with `C` and collapses the factor-compatible sector count as predicted;
12. no failed gate is relabeled or removed.

## Scalability and exact-theory obligations

The final artifact must independently prove the factor-overlap closure theorem by exact rational arithmetic in at least two implementations and by a separately compiled C++ implementation. It must also include a deterministic union-find benchmark with at least one million state coordinates and fixed-support factors, showing the predicted sector count before and after one bridge. Wall-clock timing is informative only and is not an authority gate.

The final artifact must prove the static-versus-switching acceleration boundary. For a fixed G-self-adjoint operator with spectrum in `[a,b]`, the degree-k minimax fixed-point-preserving polynomial is the normalized Chebyshev polynomial. For arbitrary switching among the full interval class under a predetermined scalar-relaxation schedule, the minimax rate is the product of the one-step scalar minimax rates and no Chebyshev improvement is available. An exact rational two-step witness on `[a,b]=[-3/2,1/2]` must certify static rate `2/7` versus switching rate `4/9`.

## Authority boundary

A successful run is an externally timestamped prospective computational validation of a theorem-to-workflow prediction. It is not a blind atmospheric discovery, not an external human proof review, not an external novelty review, and not a journal acceptance decision. Existing parent failures and every new failure remain in the final ledger.

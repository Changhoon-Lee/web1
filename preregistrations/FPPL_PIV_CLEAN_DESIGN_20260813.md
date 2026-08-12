# Factor-Provenance Phase Law — clean PIV design freeze

Date: 2026-08-13 (Asia/Singapore)

Parent artifact: `NCS_MULTIMODE_COHERENCE_GRAPH_RESPONSE_RESULT_20260812_v1R.zip`

Actual parent SHA-256: `af935366a0b77fa804c16827dcb5368674ae6ff31b0a7a1d8e9b2f05ddca57df`

## Stage-A authority correction

The prior user-visible summary printed a different ZIP digest and incorrect entry counts. The actual uploaded ZIP, sidecar, final-verification JSON, and public Git commit all agree on the digest above. In addition, an arbitrary-path replay on 2026-08-13 found that `07_CODE/derive_complex_gamma_exact.py` hard-codes `/mnt/data/mcgr_build/...`; consequently the parent `run_all.sh` fails outside that path. The new artifact must retain both defects, verify the sealed parent manifest, and reproduce the parent exact route through a path-independent repaired copy. The parent’s previous path-independent `FINAL_REPRODUCTION_PASS` claim is demoted.

## Sequencing and authority

This design is committed before loading or numerically inspecting the arrays returned by `skimage.data.vortex()`. Package-file names and public documentation were inspected, but no pixel value, gradient, factor leverage, threshold, mode, fixed point, or trajectory was read.

After this commit, one deterministic builder may load the PIV pair and construct the frozen factor list. It must publish a second commitment containing all hashes and numerical predictions before any safe, fail, repaired, or random-mixture trajectory is executed. No factor, metric, projector, tolerance, step, repair, or gate may change after the prediction commitment.

A successful campaign is an externally timestamped theorem-to-workflow computational confirmation. It is not a blind fluid-mechanics discovery, external human proof review, comprehensive external novelty review, independent third-party replication, or journal decision.

# Frozen theorem targets

## T1 — finite native-factor extremizer

Let `U in R^(n x r)` satisfy `U^T U=I`, let `W=U U^T`, let `D` be positive diagonal, and let native nonzero factor rows be `y_1,...,y_m`. Define the factor-resolved normalized uncertainty class

`C_F={sum_j alpha_j y_j y_j^T : alpha_j>=0, sum_j alpha_j y_j^T D y_j=1}`.

Define the local projected leverage

`ell_j=||U^T y_j||_2^2/(y_j^T D y_j)` and `kappa_F=max_j ell_j`.

Prove exactly that

`sup_(C in C_F) lambda_max(U^T C U)=kappa_F`,

and that a single native factor attaining the maximum is an exact extremizer. The proof must include necessity, equality, and all zero-leverage edge cases.

For `delta>0`, prove the full robust Schur phase law for

`P_C(t)=W[I-t(C+delta I)]`:

`P_C(t)` is Schur stable for every `C in C_F` if and only if

`0<t<2/(delta+kappa_F)`.

The worst-case threshold must be attained by one native factor, not merely bounded by it.

## T2 — support-family continuum

For a downward-closed family of admissible supports `A`, allow every nonzero factor vector supported in one `S in A`. Prove

`kappa_A=max_(S in A) lambda_max(U_S^T D_S^{-1} U_S)`.

Give the explicit maximizing factor from the top local generalized eigenvector. This is the sharp finite-extremizer theorem; a loose norm bound is a failure.

## T3 — provenance-loss complexity transition

If only an aggregate CP matrix zero pattern `G` is retained and native factor identities are discarded, prove that every nonnegative CP factor is supported on a clique of `G`, and hence

`kappa_G=max_(S clique of G) lambda_max(U_S^T D_S^{-1} U_S)`.

For `r=1`, `U=1/sqrt(n) 1`, and `D=I`, prove `kappa_G=omega(G)/n`. Use an exact rational threshold reduction to prove that deciding uniform robust stability is coNP-hard and that producing a destabilizing physical factor is NP-complete via CLIQUE. Do not claim maximum-clique or copositive formulations themselves as new.

The final package must sharply distinguish:

- factor-resolved input: exact scan over the supplied native factors/supports;
- matrix-sparsity-only input: maximum-weight-clique closure and worst-case intractability.

## T4 — identical nominal normal, divergent phase

For every `n>=4`, prove the exact identity

`sum_(i<j) (e_i+e_j)(e_i+e_j)^T = 11^T+(n-2)I`.

Treat the left side as an edge-local native factorization and the right side as a global-plus-singleton native factorization of the identical nominal CP normal `B0`.

With `U=1/sqrt(n)1`, `D=I`, and zero ridge in the scalar projected case, prove

`kappa_edge=2/n`, `kappa_global=1`,

so the exact robust phase thresholds are `t_edge=n` and `t_global=2`. At `t=3`, every edge-factor uncertainty is stable for every `n>=4`, while the global factor is unstable. Thus the same `B0`, spectrum, support, nominal iteration, and all matrix-only summaries are insufficient: factorization provenance is an irreducible state variable. The threshold ratio `n/2` must be certified exactly.

Also prove the fixed-support corollary: if every admissible factor support has cardinality at most `R`, then for uniform `U` and `D=I`, `kappa<=R/n`, with equality for an equal-amplitude factor on `R` coordinates.

## T5 — exact factor-preserving repair

For attenuation variables `0<=a_j<=1`, the repaired uncertainty uses factors `sqrt(a_j)y_j`. Prove that its phase constant is `max_j a_j ell_j`. For a target `kappa_target`, prove the unique componentwise-largest and minimum weighted-L1 attenuation

`a_j^*=min(1,kappa_target/ell_j)`

for every positive edit weight, with zero-leverage convention `a_j^*=1`. Separate this physics-changing factor repair from fixed-point-preserving scalar relaxation of a sealed operator.

## T6 — prior-art kill gate

The final mapping must kill each of the following as standalone novelty:

- convex hull/extreme-ray arguments;
- Rayleigh quotients, leverage scores, E-optimality, and local generalized eigenvalues;
- projected Richardson or block-Jacobi stability;
- completely-positive cone and clique-number formulations;
- maximum clique and weighted clique complexity;
- polytopic/atomic robust stability;
- factor-model nonuniqueness and CP-rank;
- scalar minimax relaxation.

Only the corrected conjunction — exact factor-provenance phase, identical-normal nonidentifiability, representation-dependent complexity, physical factor repair, and failure-retaining prospective validation — may remain an internal novelty candidate.

# Clean PIV workflow

## Input and preprocessing

Use the official `skimage.data.vortex()` pair from the first PIV Challenge. Preserve both original arrays and canonical NumPy SHA-256 values. Resize each image with anti-aliasing to `32 x 32`, convert to `float64`, and standardize both jointly using the mean and standard deviation of their average image.

Let `Ibar=(I0+I1)/2` and `It=I1-I0`. Compute centered finite-difference spatial gradients `Ix,Iy` of `Ibar`, using one-sided differences only at the open boundary.

The displacement state has two coordinates `(u_p,v_p)` per pixel, hence `n=2048`.

## Projected scientific iteration

Partition the `32 x 32` grid into nonoverlapping `4 x 4` blocks. For every block and every displacement component create one normalized block-indicator column. These 128 columns form `U`; verify `U^T U=I`. Set `W=U U^T`.

Define positive coordinate-energy weights before seeing the data by the fixed formula

`D_(u,p)=0.60+1.40 q_x(p)`,
`D_(v,p)=0.60+1.40 q_y(p)`,

where `q_x=abs(Ix)/max(abs(Ix))` and `q_y=abs(Iy)/max(abs(Iy))`, with a zero maximum replaced by one. Set `delta=0.05`.

The native uncertain factor list contains exactly one optical-flow data row per pixel:

`y_p=Ix(p)e_(u,p)+Iy(p)e_(v,p)`.

Rows with Euclidean norm below `1e-12` are excluded and counted. The normalized atom is `C_p=y_p y_p^T/(y_p^T D y_p)`. Its affine right-hand side is

`g_p=-It(p)y_p/(y_p^T D y_p)`.

No smoothness or ridge row is included in the uncertainty simplex; `delta I` is the only fixed regularization in the phase experiment.

## Prediction commitment before trajectories

The builder must publicly commit:

- input, preprocessing, `U`, `D`, factor-list, worst-factor, forcing, direct-fixed-point, and operator hashes;
- included/excluded factor counts;
- every factor leverage hash, `kappa_F`, maximizing factor ID and pixel;
- an independent dense/local calculation of the same maximizing leverage;
- exact predicted threshold `t_star=2/(delta+kappa_F)` for the sealed IEEE-754 factor list, with residual/ulp-inflated interval;
- `t_safe=0.9 t_star`, `t_fail=1.1 t_star`;
- full and reduced safe/fail spectral endpoints;
- the fail dominant projector hash and predicted finite-horizon growth;
- the scalar fixed-point-preserving minimax relaxation and its rate;
- a factor-attenuation target `kappa_target=0.8 kappa_F` and the exact attenuation vector from T5;
- direct fixed-point PIV brightness residual, coarse-flow norm, stationary residual, and hashes;
- theorem-derived safe and scalar-repair iteration budgets for G-norm tolerance `5e-6`;
- 256 deterministic Dirichlet mixtures, generated with `default_rng(20260820)`, whose coefficients are frozen by hash but whose trajectories are not executed before commitment.

The threshold statement is a residual-certified statement about the sealed IEEE-754 factors. It is not a rational exact claim about the original images.

## Confirmatory gates

After the prediction commitment, one runner must establish without any change:

1. all hashes and public commit ancestry match;
2. `U^T U=I`, `W^2=W`, and the nonzero spectrum reduction agree below `1e-11`;
3. the worst native factor attains `kappa_F` and all 256 frozen mixtures satisfy the exact upper bound;
4. the residual-certified threshold endpoints have opposite `-1` margins with the required inflation;
5. the safe trajectory reaches its direct fixed point within `5e-6` in Euclidean/G norm;
6. the fail dominant-mode error grows at the frozen rate to relative error below `2e-8` and by at least 99 percent of its finite-horizon prediction;
7. scalar relaxation preserves the fail fixed point below `1e-10` and reaches it within `5e-6`;
8. factor attenuation produces the frozen reduced phase constant and raises the robust threshold by the predicted amount;
9. PIV brightness residual, coarse-flow norm, and stationary residual agree with direct fixed-point values below `1e-6` relative;
10. no factor, metric, support, step, tolerance, budget, or gate changes after prediction;
11. every parent and new failure remains in the final ledger;
12. fresh extraction from an arbitrary non-authority path reproduces all markers with exit zero and no hard-coded `/mnt/data` dependency.

# Independent implementation and packaging obligations

The final artifact must contain exact symbolic proofs, an independent standard-library `Fraction` route, GCC/Clang O0/O3 exact implementations, randomized property tests, brute-force graph/clique checks for small graphs, the path-independent repaired parent exact replay, prior-art primary-source mapping, a harsh-red-team ledger, immutable manifest, and fresh-extraction replay from at least two distinct directory depths.

Internal G1-G12 may pass only if every corrected frozen obligation passes. External proof review, comprehensive novelty review, independent third-party replication, and journal acceptance remain unresolved unless actually performed.

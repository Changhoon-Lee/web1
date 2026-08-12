# Sector-Coherence Metric Closure — clean retina design freeze

Date: 2026-08-12 (Asia/Singapore)

Parent artifact: `NCS_FACTOR_GRAPH_METRIC_CLOSURE_ACCELERATION_RESULT_20260812_v1R.zip`

Parent SHA-256: `a477f6c4233894e3c9fa291a2774ddf137bdf789e98cd595a0955eb2eb87ba31`

## Sequencing and authority

This file is committed before loading or numerically inspecting the pixel array returned by `skimage.data.retina()`. The local package-file existence was checked, but no pixel values, image statistics, operator spectra, threshold, trajectory, or reconstruction result were inspected.

After this commit, one builder may load the image and construct the frozen operator. It must publish a second commitment containing all hashes and numerical predictions before any iterative trajectory or repair trajectory is executed. No operator, tolerance, continuation path, repair family, or success gate may change after the prediction commitment.

A successful run is an externally timestamped theorem-to-workflow computational confirmation. It is not a blind medical discovery, an external human proof review, an external novelty review, or a journal decision.

## Theorem targets frozen before data

The successor theory must prove all of the following or retain a FAIL verdict.

### T1 — weighted quantitative factor closure

For coordinate-anchored independently weighted rank-one factors `v_r v_r^T`, define `q_r=v_r∘v_r` and

`L_F = Σ_r omega_r [ (1^T q_r) Diag(q_r) - q_r q_r^T ]`.

For every diagonal metric state `S=Diag(s)`, prove the identity

`Σ_r omega_r ||[S,v_r v_r^T]||_F^2 = 2 s^T L_F s`.

Prove that the kernel is exactly the sector-constant metric space induced by factor supports, and that the smallest positive eigenvalue gives the sharp closure-Poincare constant, including an equality witness. Do not claim graph-Laplacian or Poincare machinery itself as new.

### T2 — mixing-constrained quantitative closure

Let `R sigma=0` be the reduced mixing-compatibility equations on the old sector metrics and let `U` span `ker R`. For new bridge factors, prove that the least normalized closure defect among mixing-compatible metrics is the smallest positive generalized eigenvalue of the bridge quotient restricted to `U`. Prove zero if and only if an exact positive metric survives, and give the unique-ray formula.

### T3 — rank-one-block completion collapse

Let disjoint sector vectors `h_a` be nonzero and `H=[h_1,...,h_c]`. Characterize every positive-semidefinite matrix `X` whose diagonal sector blocks equal `h_a h_a^T` as

`X = H C H^T`, where `C` is a correlation matrix (`C>=0` PSD and `diag C=1`).

Prove, with explicit left inverses, that:

- `X` is entrywise nonnegative iff `C` is entrywise nonnegative;
- `X` is completely positive iff `C` is completely positive.

Thus the state-dimensional physical completion problem must reduce exactly to a sector-dimensional completely-positive correlation problem.

For two sectors, prove the exhaustive one-parameter form

`C_theta=[[1,theta],[theta,1]], 0<=theta<=1`,

and obtain the exact global distortion/closure Pareto frontier. For three or four sectors, record the classical DNN=CP boundary rather than claiming it as new. For five or more sectors, explicitly retain the CP-hardness boundary.

### T4 — exact coherence-to-stability phase law

For the two-sector physical completion path

`X_theta=(1-theta) X_split + theta h h^T`,

prove exact formulas for commutator fracture and physical distortion. For the frozen rational four-state motif inherited from the parent theory, derive an exact algebraic first Schur crossing in `theta`, certify one rational safe point and one rational fail point by exact arithmetic, and certify a fixed-point-preserving stabilization.

No perturbation bound alone is sufficient. The small motif must include an exact necessary-and-sufficient crossing certificate.

### T5 — minimum physical factor split

For coordinate sectors and nonnegative factors, prove that sectorwise factor splitting is the unique Frobenius projection preserving each diagonal sector block, PSD, complete positivity, entrywise nonnegativity, nonincreased support, and locality.

Show that the total squared distortion for a fixed partition is exactly twice the cut weight in the factor-induced weighted graph. Treat graph cut itself as classical. State precisely which optimization variants are polynomial and which are not; do not claim a generic new min-cut algorithm.

### T6 — prior-art kill gate

The final ledger must separately map and kill as standalone novelty claims:

- commutants and simultaneous block diagonalization;
- graph and hypergraph connectivity;
- graph Poincare inequalities and Laplacian spectral gaps;
- double-commutator/dephasing semigroups;
- PSD/correlation-matrix completion;
- completely-positive matrix completion and approximation;
- DNN=CP in order at most four;
- graph cuts;
- common-metric stability, Richardson iteration, Chebyshev acceleration, and structured singular-value methods.

Only the full corrected conjunction may remain as a novelty candidate.

## Clean retina workflow

### Input and preprocessing

Use the official `skimage.data.retina()` RGB image. Preserve the returned uint8 array and its canonical NumPy SHA-256. Center-crop the largest square, resize with anti-aliasing to `14 x 14 x 3`, and transform RGB to optical-density channels

`z=-log((rgb+1)/256)`.

Standardize each channel using image-wide mean and standard deviation. These three standardized channels are the frozen truth.

Generate observations with an open-boundary anisotropic Gaussian PSF applied independently to all channels, using `(sigma_x,sigma_y,angle)=(1.05,0.70,18 degrees)`, then add Gaussian noise of standard deviation `0.008` times the truth standard deviation using NumPy `default_rng(20260815)`.

### Mixer and base physics

Build an open four-neighbor bilateral spatial graph from the three-channel optical-density truth. Edge affinity is

`exp(-||z_i-z_j||^2/(2 s^2))`,

where `s` is the median positive neighboring distance and `s=1` only when all distances vanish. Use lazy reversible spatial mixing with `tau=0.31`.

Use the positive nonsymmetric channel mixer

`T=[[0.93,0.04,0.03],[0.12,0.84,0.04],[0.18,0.08,0.74]]`.

The builder must solve for and freeze a positive diagonal channel metric `C_ch` satisfying `C_ch T=T^T C_ch`; if no positive solution exists, the campaign fails without changing `T`.

Set

`W=P kron T`,
`M=D kron C_ch`,
`L=D^{-1} kron I_3`,
`C=M L=I kron C_ch`,
`G=M W^{-1}`.

The compatible base physics contains, separately in each channel:

- every PSF row factor;
- open four-neighbor first-difference factors with nominal weight `0.040`;
- coordinate ridge factors with nominal weight `0.025`.

All weights are frozen at nominal values for the coherence-path experiment. Before adding cross-channel bridges, the factor-support sectors are predicted to be three full channel sectors of size 196 each.

### Frozen bridge and physical coherence path

At the center spatial pixel, use one nonnegative bridge factor with equal normalized energy in all three channels:

`h = (e_R + e_G + e_B)/sqrt(3)`.

Let `h_a` be its three sector restrictions and `H=[h_1,h_2,h_3]`. Use the one-parameter completely-positive correlation path

`C_theta=(1-theta) I_3 + theta 11^T`, `0<=theta<=1`,

and bridge normal `X_theta=H C_theta H^T`.

The full physics is

`B(theta)=B_base + eta X_theta`,

with bridge strength fixed at `eta=1.0` before data. The path preserves all diagonal sector blocks, PSD, complete positivity, entrywise nonnegativity, and support.

The builder must freeze, before trajectories:

- input, preprocessed-data, factor-list, operator, forcing, truth, and direct-fixed-point hashes;
- sector counts `3 -> 1` and independent dense commutant dimensions;
- weighted closure Laplacian spectrum and sharp closure gap;
- mixing-compatible closure cone dimension and bridge-restricted defect eigenvalue;
- exact formulas evaluated at the frozen channel metric for fracture and distortion along theta;
- a residual-certified interval for the first `theta_star in (0,1)` at which the raw update loses Schur stability, or a predeclared FAIL if no crossing exists;
- frozen points `theta_safe=0.9 theta_star` and `theta_fail=min(1,1.1 theta_star)`; if `theta_fail=theta_star`, fail;
- crossing branch and dominant mode;
- safe and fail spectral radii;
- the minimal coherence reduction `theta_repair` chosen solely from the frozen certified phase law to obtain target spectral radius at most `0.98`, without changing any other physics factor;
- direct fixed points and retinal-channel RMSE/PSNR/residual metrics for safe, fail, and repaired equations;
- theorem-derived iteration budgets from certified contraction rates.

### Threshold certification

The stored IEEE-754 operator threshold is numerically certified, not rational exact. Use two independent symmetric generalized-eigenvalue reductions, residual inflation, outward rounding by at least 32 ulps, and endpoint sign checks whose margins exceed 100 times the reconstructed eigensolver residual. If these conditions fail, the threshold subclaim fails rather than widening or moving the continuation after trajectories.

### Confirmatory gates

After the public prediction commitment, one deterministic runner must establish all of the following:

1. all public hashes and commit ancestry match;
2. sector union-find and independent dense commutant dimensions agree before and after the bridge;
3. the weighted closure identity and sharp-gap equality witness hold numerically to `1e-10` relative;
4. the mixing-restricted bridge defect agrees with its reduced generalized eigenproblem to `1e-10` relative;
5. the CP-correlation parameterization reconstructs the state matrix and the predicted distortion/fracture curves to `1e-10` relative at theta values `0,1/4,1/2,3/4,1`;
6. the certified threshold interval has opposite endpoint signs with required residual margins;
7. safe iteration reaches the frozen direct fixed point within `5e-6` in G norm;
8. fail dominant-mode growth agrees with the frozen spectral rate to `2e-8` relative and grows by at least `10^4` or 99% of the finite-horizon prediction;
9. the coherence repair reaches the repaired direct fixed point within `5e-6`, has spectral radius at most `0.98`, and uses the largest theta certified to meet that target;
10. retinal RMSE, PSNR, observation residual, and stationary residual agree with their frozen direct-fixed-point values to `1e-6` relative;
11. no threshold, theta, budget, metric, factor, tolerance, or gate changes after prediction;
12. every implementation or protocol failure remains in the failure ledger.

## Independent implementation and packaging obligations

The final artifact must contain:

- symbolic/rational proof scripts;
- an independent Python `Fraction` implementation;
- a compiled C++ exact implementation under GCC/Clang and O0/O3;
- randomized property tests of rank-one-block completion and weighted closure identities;
- a million-coordinate streaming factor-graph test with deterministic authority output and timing separated into non-authoritative diagnostics;
- a prior-art mapping corpus and harsh red-team ledger;
- deterministic manifest and fresh extraction replay.

The final authority may state internal G1-G12 pass only if every frozen obligation passes. External human proof review, comprehensive novelty review, and journal acceptance remain undetermined unless actually performed.

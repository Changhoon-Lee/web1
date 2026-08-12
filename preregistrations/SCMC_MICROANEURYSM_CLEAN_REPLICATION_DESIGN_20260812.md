# SCMC clean microaneurysm replication design

Date: 2026-08-12 (Asia/Singapore)

This new-input campaign follows the publicly retained retina builder failure at commit `71a246ba3fb59c84e3b1a4b0fddda94cbb993ec4`. It does not erase that failure. The protocol changes are motivated by it and are therefore not blind innovations.

The pixel array returned by `skimage.data.microaneurysms()` has not been loaded or numerically inspected before this commit. No iterative trajectory may be executed before a second public prediction commitment.

## Input and two-channel scientific state

Use the official gray-level retinal microaneurysm crop. Preserve the returned uint8 array and canonical NumPy SHA-256. Resize with anti-aliasing to `16 x 16`.

Construct two training-free deterministic channels:

1. standardized inverted green intensity `x_1 = -(I-mean I)/std I`, so dark lesions are positive;
2. standardized difference-of-Gaussians response `x_2 = Gaussian(I,0.8)-Gaussian(I,1.8)`.

The two-channel array is the frozen truth.

Generate observations by applying an open-boundary isotropic Gaussian PSF with sigma `0.85` independently to both channels and add Gaussian noise with standard deviation `0.006` times the truth standard deviation using NumPy `default_rng(20260816)`.

## Degree-robust mixer

Build a four-neighbor bilateral affinity graph from the two-channel truth. Let `A_off` contain the symmetric off-diagonal affinities

`exp(-||x_i-x_j||^2/(2 s^2))`,

where `s` is the median positive neighboring distance and `s=1` only if all distances vanish.

Set `A=I+A_off`, `D=diag(A 1)`, and

`P=(1-tau)I+tau D^{-1}A`, with `tau=0.32`.

The self-mass makes every degree at least one before seeing the data.

Use channel mixer

`T=[[0.94,0.06],[0.12,0.88]]`

with `C_ch=diag(2,1)`. Set

`W=P kron T`, `M=D kron C_ch`, `L=D^{-1} kron I_2`, `C=M L`, and `G=M W^{-1}`.

## Base physics and coherence path

The compatible base physics contains, separately in each channel:

- every row of the open-boundary sigma-0.85 PSF;
- four-neighbor first-difference factors with nominal weight `0.035`;
- coordinate ridge factors with nominal weight `0.030`.

At the center pixel define the nonnegative equal-energy bridge `h=(e_1+e_2)/sqrt(2)`. Let `X_split` contain only its two diagonal sector blocks and let `X_full=h h^T`.

Use fixed bridge strength `eta=3.0` and

`B(theta)=B_base+eta[(1-theta)X_split+theta X_full]`, `0<=theta<=1`.

This is the exhaustive two-sector PSD, entrywise-nonnegative, completely-positive completion family that preserves the bridge diagonal sector blocks.

## Deterministic theorem-designed challenge rule

Before any trajectory, the builder must independently certify the first Schur-loss beta threshold at `theta=0` and at `theta=1` for the stored IEEE-754 operators.

If the full-coherence threshold is not strictly smaller than the split threshold by at least 1% of the split threshold, the campaign fails.

Otherwise freeze

`beta = (beta_split + beta_full)/2`.

This rule is fixed before data and uses no trajectory. It intentionally places the split and full endpoints on opposite sides of the phase boundary when the physical bridge has a genuine destabilizing effect.

At this beta, certify the first coherence threshold `theta_star in (0,1)`, and freeze

`theta_safe=0.9 theta_star`,
`theta_fail=min(1,1.1 theta_star)`.

If `theta_fail<=theta_star` or the endpoint signs are not opposite, fail.

Freeze the largest coherence value `theta_repair<theta_star` certified to have spectral radius at most `0.98`; if no such value exists, use the split endpoint only if its spectral radius is at most `0.98`, otherwise fail.

## Numerical certification

Every beta and theta threshold interval must be produced by two independent eigenvalue/root routes, residual inflation, at least 32 ulps of outward rounding, and direct opposite-sign boundary checks whose margins exceed 100 times the reconstructed eigensolver residual. These are numerical certificates for the stored IEEE-754 operators, not rational exact proofs.

## Prediction commitment

Before trajectories, publicly commit:

- input, preprocessed-data, factor-list, operator, forcing, truth, and fixed-point hashes;
- factor sectors and dense commutant dimensions before/after the bridge;
- weighted closure Laplacian spectrum, sharp closure gap, equality witness residual;
- unique positive mixing-compatible metric ray and normalized bridge defect;
- exact sector-correlation distortion/fracture formulas evaluated at `theta=0,1/4,1/2,3/4,1`;
- certified endpoint beta thresholds, challenge beta, coherence threshold, safe/fail/repair theta values;
- crossing branch and dominant mode;
- safe/fail/repair spectral radii;
- direct fixed-point lesion-channel RMSE, PSNR, observation residual, and stationary residual;
- theorem-derived iteration budgets from frozen contraction rates.

## Confirmatory gates

1. all public hashes and ancestry match;
2. no parameter differs from this design or the prediction commitment;
3. sector union-find and independent dense commutant dimensions agree `2 -> 1`;
4. degree lower bound is at least one;
5. weighted closure identity, sharp gap, and equality witness pass at `1e-10` relative;
6. rank-one-block CP-correlation parameterization and five-point Pareto formulas pass at `1e-10` relative;
7. all residual-certified threshold brackets have valid endpoint signs and margins;
8. safe trajectory reaches its frozen direct fixed point within `5e-6` in G norm;
9. fail dominant-mode rate agrees to `2e-8` relative and grows by at least `10^4` or 99% of prediction;
10. coherence repair is the largest frozen theta meeting rho<=0.98 and reaches its direct fixed point within `5e-6`;
11. lesion-channel native metrics agree with frozen direct values to `1e-6` relative;
12. every failure remains in the final ledger.

## Authority

A pass is a clean externally timestamped computational confirmation of the corrected degree-robust protocol and sector-coherence phase law. It is not a blind medical finding, external proof review, external novelty review, or journal acceptance.

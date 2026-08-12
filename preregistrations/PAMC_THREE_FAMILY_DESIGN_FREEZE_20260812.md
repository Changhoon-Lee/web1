# PAMC three-family design freeze

Date: 2026-08-12 (Asia/Singapore)

Parent authority artifact SHA-256:
`d5bd5282615f4bcd58efb499a003728e83bbf952dd26a70386c48a123046a423`

## Sequencing and authority

This file freezes the new campaign before any safe/fail/repaired iterative trajectory is executed. The input files were already present in the parent campaign and are therefore not blind or unseen. The only prospective claim permitted is an externally timestamped theorem-to-workflow computational prediction. No natural-world blind-discovery claim is permitted.

A prediction payload must be publicly committed after operator construction and generalized spectral analysis but before any iterative trajectory, reconstruction, assimilation run, PDE stationary solve, or repair run. After that commit, the confirmatory runner may execute without changing operators, parameters, forcing, iteration counts, or tolerances.

A family is confirmatory only if all frozen checks pass. Any modification after observing a trajectory demotes that family to exploratory evidence.

## Inputs

- Hubble deep-field NumPy source: `e89799cfa894159ee2b74b8d2c324c7f934755f7f99e8cb37fe0f847a455d70e`.
- NOAA El Niño CSV source: `943c737c7430447b21cc819212e97c7e4aa895042043c129f8d4f04d465bff36`.
- MOOSE SPE10 case-1 source: `b127cc7cf1cedbc48c6c2ba685339a846b91ea119bd3b57adb19948a56b3f864`.

All random numbers use NumPy `default_rng(20260812)` with family-specific deterministic seed offsets 1, 2, and 3.

## Common theorem-level protocol

Each family has state dimension `n*d` with `d=2`, a positive nonsymmetric mixer `W`, a fixed SPD local scaling `L`, a symmetric PSD physics normal `B`, and affine update

`x_{k+1} = W [x_k - beta L (B x_k - h)]`.

The operator is assembled independently of any stability threshold. A block-diagonal physical metric `M` must satisfy `W.T M = M W`, and `C=M L` must satisfy `C B = B C.T`. The derived iteration metric is `G=M W^{-1}`.

The strict-extension condition is frozen as `||W L-(W L).T||_F/||W L||_F > 1e-8`; otherwise the family is not evidence beyond full-physics BHMC.

The compatible threshold is predicted only from the generalized symmetric pencil

`G + M - beta C B`.

The predicted first loss must be the `-1` branch. The threshold interval is the floating value inflated by residual and one-ulp outward rounding. Frozen points are `beta_safe=0.80 beta_star` and `beta_fail=1.20 beta_star`.

At `beta_fail`, let `[a,b]` be the full generalized spectral interval of `M-beta C B` relative to `G`. Freeze the fixed-point-preserving minimax relaxation

`alpha=2/(2-a-b)`, `r=(b-a)/(2-a-b)`.

For every family, the prediction payload must include input, preprocessed-data and operator SHA-256 values; dimensions; closure residuals; full-BHMC defect; threshold interval; safe/fail spectral radii; dominant mode descriptor; repair alpha/rate; forcing hash; direct fixed-point hash; and trajectory tolerances.

The confirmatory run must establish:

1. safe affine iteration converges to the direct fixed point;
2. fail affine iteration grows at the frozen dominant spectral rate;
3. the frozen relaxation converges to the identical fixed point;
4. fixed-point discrepancy between unrepaired and repaired equations is below `1e-10` relative;
5. a domain-native residual and data-error metric show safe/repaired success and fail divergence;
6. a symmetry-breaking physics factor has a nonzero commutator with `C` and destroys the exact algebraic closure class, without being used to tune the compatible threshold.

## Family F1 — multichannel astronomical inverse imaging

- Center-crop the Hubble RGB image to a square, resize to `16 x 16 x 3`, and compute a deterministic two-component PCA of the RGB pixels. Orient each component by making its largest-magnitude RGB loading positive.
- Build an open four-neighbor bilateral graph from the two PCA channels. Edge weights use the median nonzero neighboring PCA distance. The spatial mixer is the lazy reversible walk `(1-tau)I+tau D^{-1}A` with `tau=0.35`.
- Use the fixed positive nonsymmetric spectral mixer `T=[[0.96,0.04],[0.08,0.92]]`, whose channel metric is `C_ch=diag(2,1)`. Set `W=P kron T`, `M=D kron C_ch`, and `L=D^{-1} kron I_2`.
- Physics is an anisotropic open-boundary Gaussian PSF normal plus four-neighbor quadratic regularization and ridge, applied identically to both PCA channels. Freeze PSF `(sigma_x,sigma_y,angle)=(1.15,0.75,20 degrees)`, regularization `0.04`, ridge `0.03`.
- Generate observations by applying the PSF to the frozen PCA truth and adding Gaussian noise with standard deviation `0.01` times the truth standard deviation, seed offset 1.
- Native consequences: reconstruction residual, relative fixed-point error, and PSNR against the frozen PCA truth.
- Symmetry breaker: add a cross-channel rank-one color factor proportional to `[1,1][1,1]^T` at the center pixel; report the exact/nonzero commutator with `C_ch`.

## Family F2 — NOAA El Niño seasonal vector assimilation

- Use years 1950–1994 as the training panel and 1995–2010 as the held-out forcing panel. Form two monthly state channels: standardized SST level and standardized year-to-year tendency. Standardization is learned only from the training panel.
- Build a 12-node cycle with three fixed opposite-month chords. Edge weights are `0.35+0.65*abs(training correlation)` and the lazy reversible spatial walk uses `tau=0.30`.
- Use `T=[[0.91,0.09],[0.27,0.73]]`, `C_ch=diag(3,1)`, `W=P kron T`, `M=D kron C_ch`, `L=D^{-1} kron I_2`.
- Physics is the sum of diagonal month/channel observation precision, separate-channel cyclic second-difference regularization, and ridge. All channel matrices are diagonal in the `C_ch` basis. Freeze regularization weights `(0.10,0.04)` and ridge `0.05`.
- The held-out panel mean supplies the affine observation forcing only; it must not enter `W`, `M`, `L`, or `B`.
- Native consequences: held-out state RMSE, observation-normal residual, and relative fixed-point error.
- Symmetry breaker: add a cross-channel covariance observation factor at January.

## Family F3 — heterogeneous porous-media coupled PDE

- Parse the immutable SPE10 case-1 source and aggregate its 2,000 permeability values to an open `10 x 20` grid by geometric averaging, as in the parent parser.
- Build a two-species finite-volume block graph. Node mass is `m_i C_ch`, with `m_i` the local median-normalized permeability to power `0.10` and `C_ch=diag(5/2,1)`.
- Each edge uses harmonic permeability and a symmetric positive `2 x 2` flux block whose off-diagonal and second-channel coefficient depend only on the frozen edge orientation and normalized local log-permeability. The flux blocks are not all proportional, so the global mixer is not a Kronecker product. Choose the largest `tau` equal to `0.30/lambda_max(M^{-1/2} A M^{-1/2})`; set `W=M^{-1}(M-tau A)`.
- Set `L=diag(m_i^{-1} I_2)`, so `C=M L=I_n kron C_ch` is non-scalar.
- Physics is a heterogeneous finite-volume diffusion-reaction normal with diagonal species mobility `(1,0.55)`, open no-flow boundaries, ridge `0.02`, and two fixed source/sink forcing patterns. It commutes with `C` but is assembled independently of `W`.
- Native consequences: finite-volume residual, energy-norm fixed-point error, and source-to-production flux balance.
- Symmetry breaker: add one local cross-species reaction factor at the maximum-permeability cell.

## Frozen iteration protocol

For F1 and F3, run 600 iterations for safe and repaired cases and 120 iterations for the fail case. For F2, run 300 iterations for safe/repaired and 80 for fail. Store the complete log-error and native residual histories.

Success tolerances:

- predicted versus observed spectral rate: relative error below `2e-8` when measured on the frozen dominant eigenvector, and below `5e-3` on a generic initial state tail;
- safe/repaired final relative fixed-point error below `5e-6` for F1/F2 and `2e-4` for F3;
- fail dominant-eigenvector error growth at least `10^3` from its initial value or the predicted finite-horizon factor, whichever is smaller;
- repaired/native residual smaller than the initial residual by at least `10^3` for F1/F2 and `10^2` for F3;
- all frozen SHA values and public commit ancestry match.

## Gate policy

Three successful workflows support breadth and prospective computational consequence only. They do not establish that every scientific workflow has PAMC, and they do not constitute a blind natural discovery. The final NCS-level verdict additionally requires the theorem and novelty kill gates, independent exact implementations, failure ledger, and an explicit comparison against simultaneous symmetrization, commutant block diagonalization, common-inner-product switching theory, Richardson iteration, and standard robust-control stability radii.

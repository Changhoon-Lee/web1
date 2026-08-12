# MCGR clean Adirondack stereo replication design

Date: 2026-08-12 (Asia/Singapore)

This campaign follows the public Motorcycle design/prediction/result chain and a later red-team finding: the packaged scikit-image disparity map is indexed in right-image coordinates, while the first anchor builder treated it as left-indexed. The first campaign remains valid as a frozen operator prediction but its physical-correspondence subclaim is demoted. This new campaign uses the explicit Middlebury left-view disparity file `disp0.pfm` and does not erase the earlier defect.

No Adirondack image or disparity bytes have been downloaded or inspected before this commit. Directory names and public file sizes were visible on the official Middlebury index only. No trajectory may run before a second public prediction commitment.

## Immutable public source

Download exactly these official files from `Adirondack-perfect`:

- `im0.png` — left image;
- `im1.png` — right image;
- `disp0.pfm` — left-indexed ground-truth disparity;
- `calib.txt` — calibration receipt.

Freeze byte SHA-256 values before preprocessing. Parse PFM according to its header, dimensions, endian scale, and bottom-to-top row convention. Positive finite `disp0(r,c)` maps a left coordinate to right column `c-disp0(r,c)` on the same rectified row.

## Frozen preprocessing and operator

Resize both RGB images to `16 x 16`, convert to grayscale, and standardize each view independently. Resize `disp0` by masked numerator/denominator interpolation and multiply disparity by `16/original_width`.

Use the concatenated two-view standardized state. Generate observations with the same open-boundary Gaussian PSF sigma `0.80` in both views and Gaussian noise `0.006` times each truth standard deviation with NumPy `default_rng(20260819)`.

Build a four-neighbor bilateral graph from the average view intensity, add unit self-mass, and use lazy reversible spatial mixing with `tau=0.31`. Use view mixer `T=[[0.94,0.06],[0.12,0.88]]`, view metric `diag(2,1)`, and the same definitions `W=P kron T`, `M=D kron C_view`, `L=D^{-1} kron I_2`, `G=M W^{-1}`.

Base physics is view-separated PSF rows, four-neighbor differences of weight `0.035`, and coordinate ridge factors of weight `0.030`.

## Correct left-disparity anchors

The two left anchors are fixed at resized coordinates `(5,5)` and `(10,10)`. For each anchor, if the resized left disparity is invalid, choose the nearest valid left coordinate by Manhattan distance, breaking ties by row then column. Map to the right coordinate by `round(c_left-disp0_left)` and clip to the grid. Log every fallback. If either left or right anchor pair collides, fail.

Use two-column coordinate anchor matrices and target internal coherence `K_*=[[4/5,1/5],[1/5,4/5]]`. Use `C(alpha)=[[I_2,alpha K_*],[alpha K_*^T,I_2]]`, bridge strength `eta=3`, and `B(alpha)=B_base+eta H C(alpha) H^T`.

## Deterministic challenge and prediction rule

Before trajectories, independently certify the first Schur-loss beta threshold of `alpha=0` and `alpha=1`. If the full-coherence threshold is not at least one percent below the split threshold, fail. Otherwise freeze their midpoint as beta.

At that beta, independently determine the first alpha crossing with both the full 512-state operator and the four-dimensional response determinant. Use residual-inflated brackets with at least 32 ulps outward rounding and direct endpoint signs. Freeze `alpha_safe=0.9 alpha_star`, `alpha_fail=min(1,1.1 alpha_star)`, and the globally largest `alpha_repair<alpha_star` with spectral radius at most `0.98`, certified from all response roots at `z=-0.98`.

Before trajectories, publish all source/preprocessing/operator/factor/fixed-point hashes; parsed calibration and PFM receipts; anchors; completion and metric residuals; beta and alpha brackets; full/response winding counts; safe/fail/repair spectra; direct fixed-point stereo metrics; canonical dominant projector; and theorem-derived iteration budgets.

## Confirmatory gates

1. every source, operator, prediction, mode, and fixed-point hash matches;
2. the PFM parser is independently replayed and the left-to-right anchor equation is satisfied within one resized pixel;
3. high-rank PSD/nonnegative/CP completion and contraction certificates pass;
4. full determinant and four-dimensional response determinant agree at fixed complex test points below `1e-9` relative;
5. full and response threshold routes overlap and give the same first crossing and unstable count;
6. safe trajectory reaches its fixed point within `5e-6` in G norm;
7. fail dominant-mode rate agrees below `2e-8` relative and grows by at least 99 percent of the finite-horizon prediction;
8. the globally largest frozen repair reaches its fixed point within `5e-6` and has rho at most `0.98`;
9. direct and iterative left/right RMSE, PSNR, disparity consistency, and stationary residual agree below `1e-6` relative;
10. no source, anchor, parameter, threshold, budget, tolerance, or gate changes after prediction;
11. the first Motorcycle coordinate-convention defect remains in the final failure ledger;
12. fresh extraction reproduces all markers with exit zero.

A pass is an externally timestamped clean computational replication using the correct left-disparity convention. It is not a blind physical discovery, external proof review, comprehensive novelty review, independent third-party replication, or journal acceptance.

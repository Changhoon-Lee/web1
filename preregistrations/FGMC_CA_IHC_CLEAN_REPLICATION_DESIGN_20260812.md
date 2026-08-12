# FGMC-CA clean immunohistochemistry microscopy replication design

Date: 2026-08-12 (Asia/Singapore)

This is a new-input clean replication created after the Mauna Loa CO2 run and after discovering that the CO2 public threshold interval used one-ulp outward rounding without actually adding the residual inflation required by its design. The CO2 safe/fail and trajectory results remain valid computational evidence, but its narrow threshold-interval subclaim is demoted. This IHC replication is intended to test the corrected interval protocol in a first-shot design → prediction → trajectory sequence.

The `skimage.data.immunohistochemistry()` pixel array must not be loaded or numerically inspected before this design is committed. Package-file existence has been checked, but no pixel values have been read. No iterative trajectory may be executed before the public prediction commitment.

## Input and scientific preprocessing

Use the local scikit-image immunohistochemistry RGB image. Preserve the exact uint8 array as a NumPy file and freeze its SHA-256. Convert RGB to HED optical-density coordinates with `skimage.color.rgb2hed`; use the hematoxylin and DAB channels. Center-crop the largest square, resize to `16 x 16 x 2` with anti-aliasing, and standardize each stain channel by its image-wide mean and standard deviation.

The standardized two-stain image is the frozen truth. Generate observations by applying an open-boundary anisotropic Gaussian PSF with `(sigma_x,sigma_y,angle)=(1.0,0.65,15 degrees)` independently to both stains, then add Gaussian noise with standard deviation `0.008` times the truth standard deviation using NumPy `default_rng(20260814)`.

## Mixing and physics

Build an open four-neighbor bilateral graph from the two standardized stain channels. Spatial affinity is `exp(-||x_i-x_j||^2/(2 s^2))`, where `s` is the median positive neighboring stain distance and `s=1` only if all distances vanish. Use lazy reversible mixing with `tau=0.32`.

Use channel mixer `T=[[0.95,0.05],[0.15,0.85]]` and channel metric `C_ch=diag(3,1)`. Set `W=P kron T`, `M=D kron C_ch`, `L=D^{-1} kron I_2`, `C=M L`, and `G=M W^{-1}`.

Physics is the independently weighted local factor family consisting of:

- every row of the open-boundary PSF operator in each stain channel;
- four-neighbor first-difference factors within each stain channel, nominal weight `0.045`;
- coordinate ridge factors in each stain channel, nominal weight `0.025`.

The nominal normal is the weighted Gram sum. All factor weights vary independently over `[0.8 w_nominal,1.2 w_nominal]`. The two stain channels are predicted a priori to form exactly two full-span factor-support sectors. A reserved center-pixel cross-stain factor `e_H+e_DAB` must merge them to one sector and have nonzero commutator with `C`.

The affine update is `x_(k+1)=W[x_k-beta L(Bx_k-h)]`, where `h` is the PSF adjoint applied to the noisy observation.

## Corrected threshold certification

Before trajectories, compute the largest generalized eigenvalue of `(C B,G+M)` in two independent symmetric reductions. Let `beta_hat` be its reciprocal. Compute a transformed standard-symmetric eigenpair residual `epsilon_lambda`, the top spectral gap, and the implied first-order beta residual `epsilon_beta=epsilon_lambda/lambda_max^2`.

Freeze the public numerical bracket with half-width

`delta_beta=max(1e-10*max(1,abs(beta_hat)),1000*epsilon_beta,16*ulp(beta_hat))`.

At both endpoints, independently evaluate the smallest eigenvalue of `G+M-beta C B`; the low endpoint must be positive and the high endpoint negative by at least `100` times the full eigensolver reconstruction residual. Record all residuals and endpoint margins. This is a numerical certification of the stored IEEE-754 operator, not an exact rational theorem.

Freeze `beta_safe=0.8 beta_hat`, `beta_fail=1.2 beta_hat`, all spectral endpoints, dominant mode, scalar minimax repair, fixed-point hashes, direct microscopy metrics, and static Chebyshev parameters before trajectories.

Use G-norm tolerance `5e-6`. Scalar and Chebyshev iteration counts are the smallest certified degrees meeting the tolerance plus ten guard iterations. The fail dominant run uses the smaller of 100 and the count for predicted growth of `10^4`, plus ten guard iterations.

## Confirmatory gates

1. all input/preprocessing/operator/factor/forcing/fixed-point hashes match the prediction commitment;
2. the public threshold bracket satisfies the corrected residual and endpoint-sign rules;
3. factor union-find and independent dense commutant calculations return sectors `2→1` after the reserved bridge;
4. PAMC residuals are below `1e-10`, full-BHMC defect above `1e-8`;
5. safe iteration reaches the frozen fixed point within `5e-6`;
6. raw fail dominant mode grows at the frozen rate with relative error below `2e-8`;
7. scalar repair and Chebyshev semi-iteration preserve and reach the fail fixed point within `5e-6`;
8. Chebyshev uses strictly fewer predicted and observed iterations than scalar repair;
9. reconstructed hematoxylin/DAB RMSE, PSNR, and stationary residual agree with frozen direct-fixed-point values to relative error below `1e-6`;
10. the reserved bridge collapses the sector count and the coordinate-sector factor-splitting repair is PSD, completely positive, entrywise nonnegative, support-nonincreasing, and has the predicted exact Frobenius projection distance;
11. no failed gate is relabeled.

A serialization-only error may be corrected only if the incident is publicly logged before the corrected rerun and no numerical object or gate changes.

## Authority

A pass is a clean externally timestamped computational replication of factor-topology, phase, and acceleration predictions on a biomedical microscopy workflow. It is not a blind biological discovery, external human proof review, external novelty review, or journal acceptance decision.

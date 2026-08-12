# FCPL clean data-dependent MIT-BIH record-101 design

Date: 2026-08-13 (Asia/Singapore)

This campaign is created after the following red-team finding: in the record-100 confirmation, the ECG values determine the target and native metrics, but the resolved DCT subspace—and therefore the phase constants—was fixed independently of the ECG. Record 100 remains a valid controlled factorization experiment, but it is insufficient by itself as a data-dependent scientific phase consequence.

No byte of PhysioNet MIT-BIH record 101 (`101.hea`, `101.dat`) has been downloaded, read, parsed, or numerically inspected before this commit. Only public database-level documentation was inspected. No trajectory may be executed before a separate public prediction commitment.

## Immutable official source

Fetch exactly:

- `https://physionet.org/files/mitdb/1.0.0/101.hea`;
- `https://physionet.org/files/mitdb/1.0.0/101.dat`.

Freeze byte SHA-256 values. Parse WFDB format 212 independently in two implementations. Use the signal labelled `MLII`; if no channel has that exact label, the campaign fails without substituting another lead. Verify the header-declared sample rate, sample count, gain, baseline, initial values, and checksums.

No annotation file, beat label, diagnosis, or outcome is used.

## Frozen training/held-out split

Use the first 100,000 MLII samples as the training segment and the immediately following 4,096 samples as the held-out computational segment. Convert ADC values to physical units using the header gain and baseline.

Compute the training mean and standard deviation from the training segment only. Standardize both training and held-out data with those frozen training statistics. If the training standard deviation is zero, fail.

## Data-dependent morphology subspace

From the standardized training segment, form every length-256 window with stride 64. Do not subtract a per-window mean. Let `Z` be the resulting window matrix, with one row per window. Form

`C_train = Z^T Z / number_of_windows`.

Compute its leading 16-dimensional eigenspace by two independent routes:

1. symmetric eigendecomposition of `C_train`;
2. right singular subspace of `Z`.

Canonicalize the projector, not individual eigenvectors. Require the two rank-16 projectors to agree below `1e-10` in relative Frobenius norm. Require a relative spectral gap

`(lambda_16-lambda_17)/max(lambda_16,1) > 1e-8`.

If either condition fails, the campaign fails without changing the window length, stride, rank, split, or source record.

Choose a deterministic orthonormal basis `U_local` of the common rank-16 projector by projecting coordinate axes in increasing index order and applying modified Gram--Schmidt with positive-pivot sign convention. The global resolved basis is block diagonal with 16 copies of `U_local`, one for each consecutive 256-sample held-out block. Thus the state dimension is 4096 and the resolved rank is 256.

The phase operator `A=U U^T` now depends on the training ECG morphology. This dependence must be recorded by source, covariance, projector, basis, and eigenspectrum hashes.

## Same-normal factorization families

Set `D=I_4096`, aggregate normal `B=I_4096`, ridge `delta=0.05`, and complement damping `eta=0.25`.

Within every 256-coordinate held-out block construct exactly 256 unit-norm factors and preserve the block normal `I_256`:

1. **Native coordinate factors.** Their phase constant is the largest diagonal of the data-learned projector `U_local U_local^T`.
2. **Balanced factors.** Complete `U_local` deterministically to an orthogonal basis `Q_local`; multiply `Q_local` by the normalized 256-by-256 Sylvester--Hadamard matrix. Every factor quotient must equal `16/256=1/16`.
3. **Pessimal factors.** Use `Q_local` itself. It contains the learned resolved modes and therefore attains quotient one.

Every family has 4,096 unit-norm factors, the same 16 block normals, the same global normal, and the same batch least-squares objective when right-hand sides are transformed by the same orthogonal maps.

The complete nested provenance hierarchy uses local coordinate block sizes `1,2,4,8,16,32,64,128,256`, plus the global group. Every lower and upper endpoint must be constructively realized before trajectory.

## Common held-out target

Let the standardized held-out segment be `s_hold`. The common target is the data-adaptive projection

`x_star = U U^T s_hold`.

All native, balanced, and pessimal affine factor maps have this exact target. The experiment is a controlled morphology-adaptive computational iteration, not a clinical estimator or arrhythmia detector.

## Frozen challenge and finite-time rule

Compute the native phase constant independently from direct projector diagonals and 80-digit evaluation of the frozen basis. Freeze

`T_native=2/(delta+kappa_native)`,

`t_challenge=0.9 T_native`.

Before trajectory, verify that the native and balanced worst-factor maps are Schur stable and the pessimal worst-factor map is unstable. Otherwise fail.

Use a single relative state target `1e-12`. For every stable or repaired rate `q<1`, freeze

`N=ceil(log(1e-12)/log(q))+10`.

The fail budget is the smallest integer giving predicted dominant-mode growth at least `10^4`, plus five guard iterations.

Before accepting the public prediction, compute deterministic sensitivity bounds showing that the state target implies relative error below `1e-9` or absolute error below `1e-12` for all frozen held-out metrics. If it does not, fail before trajectory.

## Prediction commitment before trajectories

The public prediction must include:

- source/header/parser hashes and receipts;
- training/held-out arrays, training statistics, window matrix, covariance, spectrum, projector, basis, factorization, hierarchy, target, schedules, modes, and fixed-point hashes;
- independent subspace agreement and eigengap;
- factor counts, norms, block/global normal residuals, objective invariance residuals;
- data-dependent native `kappa`, balanced `1/16`, pessimal `1`;
- complete factorization interval and every provenance-partition endpoint;
- challenge step, spectra, dominant projector, scalar fixed-point-preserving repair, and theorem-derived budgets;
- 256 deterministic 40-step schedules per family from `default_rng(20260824)`;
- held-out signal RMSE in physical and standardized units, first-difference RMSE, morphology-subspace energy fraction, stationary residual, and metric-sensitivity bounds;
- `trajectory_executed=false`.

## Confirmatory gates

After the prediction commit, one deterministic runner must establish all of the following without changing any source, split, subspace, factorization, step, budget, metric, tolerance, or gate:

1. all public hashes and commit ancestry match;
2. the two WFDB-212 parsers agree sample-for-sample and satisfy header checksums;
3. covariance-eigen and window-SVD projectors agree below `1e-10`, and the frozen eigengap passes;
4. all three factorization families have identical count, unit norms, block/global normals, and batch objective;
5. the data-dependent native phase constant agrees by both routes, balanced equals `1/16`, and pessimal equals one;
6. every nested provenance endpoint is constructively attained and obeys refinement monotonicity;
7. native and balanced worst-factor maps are stable while pessimal is unstable at the frozen challenge step;
8. worst-factor rates agree below `2e-8` relative and fail growth reaches at least 99 percent of prediction;
9. all 256 frozen schedules remain below their certified product envelope;
10. scalar relaxation preserves the common target below `1e-10` and reaches it below `1e-12` relative state error;
11. native and balanced runs reach the target below `1e-12` relative state error;
12. all held-out metrics pass their frozen relative/absolute error gates;
13. groupwise balancing preserves the objective and target below `1e-11`;
14. the earlier record-100 limitation and every protocol/implementation failure remain in the ledger;
15. two arbitrary-path fresh extractions reproduce all authority markers with exit zero.

## Authority

A pass is a clean externally timestamped computational confirmation that a phase law learned from ECG morphology predicts same-normal factorization-dependent stability on a held-out ECG segment. It is not a clinical discovery, external proof review, comprehensive novelty review, independent third-party replication, or journal acceptance.

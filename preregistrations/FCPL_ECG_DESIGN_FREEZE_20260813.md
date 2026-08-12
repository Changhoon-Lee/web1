# Factorization-Complete Phase Law — clean ECG design freeze

Date: 2026-08-13 (Asia/Singapore)

Parent artifact: `NCS_FACTOR_PROVENANCE_PHASE_LAW_RESULT_20260813_v1R.zip`

Parent SHA-256: `40c4eb77235b8f70d33711d17189c207c0a853ae098e765d75103353aca3a7ea`

Independent Stage-A replay before this design:

- exit code: `0`;
- stderr bytes: `0`;
- stdout SHA-256: `45708c4c1815fff3f78702883341d6f828eadbf3f4f86a2c55252c7e80583482`;
- markers include exact, Fraction, C++, exhaustive-graph, PIV, parent-repair, semantic-compare, and `FINAL_REPRODUCTION_PASS`.

## Sequencing and authority

This design is committed before loading, downloading, numerically inspecting, plotting, or summarizing the array returned by `scipy.datasets.electrocardiogram()`. Only the public dataset documentation was inspected.

After this commit, one deterministic builder may load the data, construct the frozen operators, and publish a second commitment containing all input/operator hashes and every numerical prediction. No native, balanced, pessimal, repaired, random-mixture, or affine trajectory may be executed before that prediction commitment.

Any scientific parameter, factorization, support partition, step, repair, budget, tolerance, target metric, or gate changed after observing a trajectory demotes that run to exploratory evidence. Every theorem, implementation, source-fetch, serialization, or protocol failure remains in the final ledger.

A successful campaign is an externally timestamped theorem-to-workflow computational confirmation. It is not a blind cardiac discovery, external human proof review, comprehensive external novelty review, independent third-party replication, or journal acceptance.

# Frozen theorem targets

Let `A=A^T>=0` and `X=X^T>=0`, `X!=0`. A finite factorization is a family of nonzero vectors `F={x_j}` such that

`X=sum_j x_j x_j^T`.

Define

`kappa(F)=max_j (x_j^T A x_j)/(x_j^T x_j)`,

`mu(A,X)=tr(A X)/tr(X)`,

and

`lambda(A,X)=lambda_max(A restricted to range(X))`.

### T1 — factorization-complete interval theorem

Prove exactly that the set of all attainable phase constants over every finite real rank-one factorization of `X` is the closed interval

`{kappa(F): F factorizes X}=[mu(A,X),lambda(A,X)]`.

The proof must establish:

1. the universal lower bound `kappa(F)>=mu`;
2. a constructive factorization with every factor Rayleigh quotient exactly `mu`;
3. a constructive factorization attaining `lambda`;
4. constructive attainment of every intermediate `k in [mu,lambda]`;
5. all singular, zero-leverage, rank-one, repeated-eigenvalue, and range-restricted edge cases.

The lower construction must use a path-independent finite algorithm that produces an orthogonal basis with zero diagonal for the trace-zero compression `V^T(A-mu I)V`, where `X=V V^T`. The exact theorem may cite Schur--Horn or a rank-one decomposition theorem as prior art, but the final artifact must also contain a direct inductive construction and independent exact implementations.

### T2 — generalized-metric version and exact phase interval

For the FPPL projected iteration, define

`A=D^(-1/2) U U^T D^(-1/2)` and `X=D^(1/2) B D^(1/2)`.

Prove

`mu=tr(U^T B U)/tr(D B)`

and the exact factorization-uncertainty threshold interval

`T(F)=2/(delta+kappa(F)) in [2/(delta+lambda),2/(delta+mu)]`.

Every threshold in this interval must be attainable by a factorization of the same aggregate normal `B`. Do not compare different aggregate matrices or different budgets.

### T3 — provenance-partition lattice theorem

Suppose only group aggregates `X_g>=0` are retained and factorization is free within each group. Prove that the exact attainable global phase interval is

`[max_g mu(A,X_g), max_g lambda(A,X_g)]`.

Prove that every value in this interval is attained. Prove monotonicity under provenance coarsening:

- merging groups cannot increase the lower endpoint;
- merging groups cannot decrease the upper endpoint;
- therefore information loss can only widen the phase interval.

At the finest rank-one partition, the interval collapses to the native factor constant. At the coarsest partition, it becomes the global factorization-complete interval.

### T4 — equal-count, equal-norm, same-normal separation

For every `n>=2` and every rank `1<=r<n`, construct two factorizations of `X=I_n`, each consisting of exactly `n` unit-norm factors, such that for a rank-`r` orthogonal projector `A`:

- one factorization has `kappa=1`;
- a balanced factorization has `kappa=r/n`.

Prove that the phase-threshold ratio tends to `n/r` as `delta->0`. This theorem must eliminate critiques based on factor count, factor norm, aggregate normal, spectrum, support of the aggregate normal, or amplitude normalization.

### T5 — groupwise phase-optimal balancing

Given group aggregates `X_g`, construct within each group a factorization whose every factor has quotient `mu_g`. Prove that this preserves every `X_g`, hence preserves the full aggregate normal, all group-local supports, and the corresponding quadratic least-squares objective under the same orthogonal mixing of factor rows and right-hand sides.

Prove that the resulting global `kappa=max_g mu_g` is the minimum possible under the frozen provenance partition. State explicitly that the balancing factors may be signed even when a physical sensor factorization was nonnegative; the result is an exact computational residual refactorization, not automatically a realizable hardware redesign.

### T6 — CP/nonnegative boundary

For entrywise-nonnegative or completely-positive factor restrictions, do not claim the unrestricted interval theorem remains exact. Prove only statements actually certified. The final red team must distinguish:

- unrestricted real residual refactorization;
- nonnegative factorization;
- CP factorization with fixed support;
- native hardware provenance.

Any equality requiring a nonnegative balancing basis must include its exact sufficient conditions. General CP-factorization optimization remains outside the theorem unless separately proved.

### T7 — prior-art exact-mapping kill gate

The final corpus must separately kill as standalone novelty claims:

- Schur--Horn and prescribed diagonal theorems;
- trace-zero rank-one decompositions;
- frame equal-norm or tight-frame balancing;
- leverage-score equalization;
- orthogonal row mixing and least-squares invariance;
- randomized and block Kaczmarz preconditioning;
- matrix paving and Kadison--Singer consequences;
- convex-hull extremizers;
- projected Richardson stability;
- atomic or polytopic robust stability;
- CP-factorization nonuniqueness.

Only the corrected conjunction — factorization-complete phase interval, provenance-lattice information law, same-normal equal-norm separation, phase-optimal balancing, exact stability consequences, and failure-retaining prospective validation — may remain an internal novelty candidate.

# Clean ECG computational campaign

## Public input and deterministic preprocessing

Use the official `scipy.datasets.electrocardiogram()` record. Freeze the raw array and its canonical NumPy SHA-256. Use exactly the first 4096 samples. Standardize this segment by its own mean and standard deviation; if the standard deviation is zero, fail.

Partition the 4096-sample segment into 16 consecutive nonoverlapping groups of length 256. No QRS detection, label inspection, peak selection, or outcome-dependent window choice is permitted.

## Frozen resolved subspace and aggregate normal

For each 256-sample group, form the orthonormal DCT-II basis with deterministic sign convention. Retain the first 16 modes. The global resolved matrix `U` is block diagonal with 16 modes per group, total rank 256. Verify `U^T U=I`.

Set `D=I_4096`, aggregate normal `B=I_4096`, and `delta=0.05`. The resolved low-frequency ECG target is `x_star=U U^T s`, where `s` is the standardized segment.

Every compared factorization must have exactly 4096 factors, each of Euclidean norm one, and must reproduce exactly the same aggregate normal `I_4096` and the same group aggregates `I_256`.

## Three frozen provenance levels

### Native coordinate factorization

Within every group, use the 256 coordinate vectors. Its phase constant is the largest diagonal leverage of the 16-mode DCT projector. Freeze the exact floating value and maximizing sample index before trajectories.

### Group-balanced factorization

Within every group, construct an orthogonal factor matrix whose 256 columns all have quotient exactly `16/256=1/16`. Use the deterministic zero-diagonal recursion from T1 with fixed tie-breaking and sign conventions. Verify group aggregate identity and all 4096 quotients.

### Group-pessimal factorization

Within every group, use the full DCT basis, which includes the 16 resolved modes. Its phase constant is exactly one.

These three factorizations have identical factor count, factor norms, group aggregates, global normal, and batch least-squares objective. Only provenance changes.

## Affine fixed-point construction

For each factor `z_j` and the common target `x_star`, define the affine single-factor map so that `x_star` is its exact fixed point:

`x^+ = Pi[x - t(delta(x-x_star) + z_j z_j^T(x-x_star))] + x_star`,

where `Pi=U U^T` and the complement is damped by the frozen scalar `eta=0.25`.

This is a controlled error-propagation experiment preserving the same target. It is not claimed to be the original clinical estimator used to generate the ECG.

## Prediction commitment before trajectories

The builder must publicly commit:

- source, segment, standardized data, `U`, all three factorization, target, operator, mode, random-schedule, and direct-fixed-point hashes;
- factor counts, norms, aggregate and group reconstruction residuals;
- exact/theorem values `mu_g=1/16`, global `mu=1/16`, `lambda=1`;
- native, balanced, and pessimal `kappa` values;
- exact threshold interval `[2/(delta+1),2/(delta+1/16)]`;
- every provenance-partition endpoint from finest native factors through 16 groups to one global group;
- a challenge step fixed by the data-independent rule `t_challenge=0.9*T_native`;
- a required straddling check: native and balanced must be stable, pessimal must be unstable; otherwise the campaign fails before trajectories;
- safe/fail spectral radii and dominant projector hashes;
- fixed-point-preserving scalar repair for the pessimal operator;
- theorem-derived iteration budgets for relative error `5e-6`;
- 256 deterministic factor schedules for each provenance level using `default_rng(20260821)`, frozen by hash;
- ECG-domain metrics at the common target: signal RMSE, first-difference RMSE, resolved-band energy, stationary residual.

## Confirmatory gates

After the public prediction commitment, a deterministic runner must establish all of the following without changing any frozen object:

1. every public hash and commit ancestor matches;
2. every factorization reconstructs each group identity and the global identity below `1e-11` relative;
3. all factor counts and norms are identical;
4. every balanced factor quotient equals `1/16` below `1e-11`, and the pessimal factorization attains one;
5. the native value agrees with direct leverage scanning;
6. all provenance-partition interval endpoints agree with direct factorization experiments and obey refinement monotonicity;
7. at the challenge step, native and balanced worst-factor maps are Schur stable while the pessimal worst-factor map is unstable;
8. worst-factor homogeneous trajectories agree with their frozen rates to relative error below `2e-8`;
9. all 256 frozen schedules remain below their certified worst-factor envelope;
10. the scalar repair preserves the common target below `1e-10` and reaches it within `5e-6`;
11. groupwise balancing preserves the batch least-squares objective and affine target to relative error below `1e-11`;
12. ECG metrics agree with their frozen target values below `1e-8` relative;
13. every failure remains in the ledger;
14. two arbitrary-path fresh extractions reproduce all authority markers with exit zero and no absolute-path dependency.

# Exact implementation and packaging obligations

The final artifact must include:

- symbolic/rational proofs and certificates;
- an independent Python standard-library `Fraction` route;
- GCC and Clang builds under O0 and O3;
- exhaustive small-dimensional factorization and provenance-partition checks;
- randomized property tests through at least dimension 12;
- a path-independent replay of the parent FPPL authority;
- targeted primary-source prior-art mapping;
- theorem, novelty, breadth, power, and interest red-team ledgers;
- immutable manifest and two fresh-extraction replays.

Internal G1--G12 may pass only if every corrected frozen obligation passes. External human proof review, comprehensive external novelty review, independent third-party replication, publication-grade priority, and journal acceptance remain unresolved unless actually performed.

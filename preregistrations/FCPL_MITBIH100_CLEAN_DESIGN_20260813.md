# FCPL clean MIT-BIH record-100 replication design

Date: 2026-08-13 (Asia/Singapore)

This campaign follows the publicly aborted SciPy-ECG campaign at commit `3a8b809bcf2e1059f4ea64517954c9c0eb760920`. That failure is not erased. The correction is made before downloading or inspecting the new record and is therefore tested on a new untouched scientific input.

No byte of PhysioNet MIT-BIH record 100 (`100.hea`, `100.dat`) has been downloaded, read, parsed, or numerically inspected before this commit. Only public database documentation and file listings were inspected. No trajectory may be executed before a separate public prediction commitment.

## Immutable official source

Fetch exactly:

- `https://physionet.org/files/mitdb/1.0.0/100.hea`;
- `https://physionet.org/files/mitdb/1.0.0/100.dat`.

Freeze byte SHA-256 values. Parse the header without changing its declared channel format, gain, baseline, sampling rate, or signal names. Parse WFDB format 212 independently in two implementations. Use the first channel labelled MLII and exactly its first 4096 samples. Convert ADC values to physical units using the header gain and baseline. If the header, format, lead label, sample rate, sample count, or independent parser agreement fails, the campaign fails.

## Signal preprocessing and resolved subspace

Standardize the 4096-sample MLII segment by its own mean and standard deviation. Partition it into 16 consecutive nonoverlapping groups of length 256.

For each group use the deterministic orthonormal DCT-II basis with the first 16 modes retained. The global resolved projector has rank 256. Set `D=I`, aggregate normal `B=I`, ridge `delta=0.05`, and complement damping `eta=0.25`.

The common target is the blockwise low-frequency projection of the standardized ECG.

## Identical-normal factorization families

Every family must contain exactly 4096 unit-norm factors, preserve every 256-coordinate group identity, preserve the global normal `I_4096`, and preserve the batch least-squares objective when right-hand sides are mixed by the same orthogonal transformation.

1. **Native:** coordinate factors.
2. **Balanced:** within each group, DCT followed by the normalized Sylvester-Hadamard transform, so every quotient is exactly `16/256=1/16`.
3. **Pessimal:** full DCT factors, including every resolved mode, so the maximum quotient is one.

The prediction builder must also freeze the complete nested provenance hierarchy for local block sizes `1,2,4,8,16,32,64,128,256` and the global group.

## Frozen phase challenge

For the native factorization compute the maximum projected leverage independently by direct row norms and 80-digit trigonometric evaluation. Freeze

`T_native=2/(delta+kappa_native)`

and the data-independent rule

`t_challenge=0.9 T_native`.

Before trajectories, the builder must verify that native and balanced worst-factor maps are Schur stable and the pessimal worst-factor map is unstable. If not, fail.

All affine maps share the common target. Use the same factor map and scalar minimax repair definitions as the first ECG design.

## Corrected finite-time budget rule

The first ECG campaign failed because its state budget did not imply its native-metric tolerance. This campaign freezes a single stronger state bound before data:

`relative G/error target = 1e-12`.

For each stable or repaired rate `q<1`, freeze

`N=ceil(log(1e-12)/log(q))+10`.

The fail budget is the smallest count giving predicted dominant-mode growth at least `10^4`, plus five guard iterations.

At the frozen budgets, trajectory ECG metrics must agree with direct-target metrics to relative error below `1e-9` or absolute error below `1e-12`, whichever is less restrictive. This metric gate is now implied by the stronger state target for all nondegenerate frozen metrics and must be checked numerically before the public prediction is accepted. If the builder cannot certify that implication using deterministic interval/Lipschitz bounds, it must fail before trajectory rather than amend the budget.

## Prediction commitment before trajectories

Publicly commit:

- source/header/parser, segment, standardized data, DCT, all factorization, hierarchy, target, schedule, mode, and fixed-point hashes;
- header fields, physical conversion, parser agreement, input mean/std;
- factor counts, norms, group/global normal residuals, least-squares invariance residuals;
- factorization-complete and provenance-hierarchy intervals;
- native/balanced/pessimal phase constants and threshold interval;
- challenge step, spectra, dominant projector, repair, and iteration budgets;
- 256 deterministic 40-step schedules per factorization using `default_rng(20260823)`;
- direct ECG target metrics and certified metric-sensitivity bounds;
- `trajectory_executed=false`.

## Confirmatory gates

1. all public commit ancestry and hashes match;
2. the two independent WFDB-212 parsers agree sample-for-sample;
3. the header, lead label, sample rate, gain, and baseline match the frozen receipt;
4. all three factorizations have identical count, unit norms, group normals, global normal, and batch objective;
5. balanced quotients equal `1/16`, pessimal attains one, native agrees by two routes;
6. every provenance endpoint agrees with a direct constructive factorization and obeys refinement monotonicity;
7. native and balanced worst-factor maps are stable and pessimal is unstable at the challenge step;
8. worst-factor trajectory rates agree below `2e-8` relative;
9. all frozen random schedules remain below their certified product envelope;
10. scalar repair preserves the common target below `1e-10` and reaches it below `1e-12` relative state error;
11. native and balanced runs reach the common target below `1e-12` relative state error;
12. ECG trajectory metrics pass the frozen relative/absolute metric gate;
13. groupwise balancing preserves the batch objective and common target below `1e-11`;
14. the first ECG budget failure and every new failure remain in the final ledger;
15. two arbitrary-path fresh extractions reproduce all markers with exit zero.

## Authority

A pass is a clean externally timestamped computational replication of the factorization-complete phase and provenance-lattice predictions on a new official ECG record. It is not a clinical finding, external proof review, comprehensive external novelty review, third-party replication, or journal acceptance.

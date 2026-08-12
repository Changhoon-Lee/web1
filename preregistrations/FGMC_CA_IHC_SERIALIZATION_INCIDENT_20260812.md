# FGMC-CA IHC confirmatory serialization incident

Date: 2026-08-12 (Asia/Singapore)

Prediction commit: `640034e85caf3ae7e1231cc355241f92eb92c277`

The first confirmatory invocation completed the frozen numerical trajectories and constructed a result whose original gates were all true, but the final human-readable `json.dumps` call failed because one or more diagnostic values were NumPy `int64` scalars:

`TypeError: Object of type int64 is not JSON serializable`

The result file had been written through a serializer that handled NumPy scalars, but the invocation returned nonzero and is therefore not counted as a confirmatory PASS.

No input, preprocessing, operator, factor list, forcing, threshold certificate, safe/fail point, dominant mode, scalar repair, Chebyshev recurrence, iteration count, trajectory, tolerance, numerical gate, or authority rule may change. The only permitted correction is to use the same NumPy-scalar conversion in the final diagnostic print. The corrected rerun must reproduce the existing deterministic result payload and exit zero. This incident remains in the final failure ledger.

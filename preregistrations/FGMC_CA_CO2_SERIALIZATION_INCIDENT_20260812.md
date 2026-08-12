# FGMC-CA CO2 confirmatory serialization incident

Date: 2026-08-12 (Asia/Singapore)

Prediction commit: `a53474c893c3ba1e6b989e4082fba7f1c4442855`

The first confirmatory invocation executed the frozen numerical trajectories and gates but failed while serializing the result JSON because several gate values were NumPy boolean scalars rather than built-in Python booleans:

`TypeError: Object of type bool is not JSON serializable`

No input, preprocessing, operator, factor list, forcing, threshold, spectral interval, dominant vector, scalar relaxation, Chebyshev recurrence, iteration count, numerical trajectory, tolerance, or gate definition will be changed. The only permitted code correction is explicit conversion of gate values to built-in `bool` before JSON serialization.

The failed invocation is not counted as a confirmatory PASS. The corrected rerun must reproduce all deterministic numerical arrays and pass the originally frozen gates. This incident remains in the final failure ledger.

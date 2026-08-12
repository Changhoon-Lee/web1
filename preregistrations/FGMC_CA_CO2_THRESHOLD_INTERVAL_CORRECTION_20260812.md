# FGMC-CA CO2 threshold-interval authority correction

Date: 2026-08-12 (Asia/Singapore)

Design commit: `68bf468d8fd47c239a27f384f10d912e546d4866`
Prediction commit: `a53474c893c3ba1e6b989e4082fba7f1c4442855`
Result commit: `f09eda87484dcabc2189099e4e049a124d5fc498`

A later red-team replay found that the CO2 builder froze its threshold interval by one-ulp outward rounding but did not implement the residual inflation required by the public design. The replayed transformed eigenpair residual implies a first-order beta uncertainty of approximately `2.9e-16`, larger than one ulp at the stored threshold (approximately `1.1e-16`). Therefore the very narrow public CO2 threshold interval is not retained as a rigorous numerical certificate.

The following CO2 claims remain supported because their frozen parameters lie far from the boundary and were directly confirmed:

- factor-sector prediction `52+52 -> 104` after one bridge;
- compatible PAMC residuals and full-BHMC strict-extension defect;
- safe spectral radius below one;
- fail spectral radius above one;
- frozen dominant rate and fail-side growth;
- scalar fixed-point-preserving repair;
- static Chebyshev acceleration and native fixed-point metrics.

The claim that the public one-ulp interval itself contains the exact threshold of the stored floating-point operator is demoted to `NOT_CERTIFIED`.

No CO2 gate is retroactively relabeled. The clean IHC replication, designed and publicly committed after this defect was found, uses an explicit residual-inflated interval and independently checks opposite endpoint signs with margins exceeding 100 times the eigensolver reconstruction residual.

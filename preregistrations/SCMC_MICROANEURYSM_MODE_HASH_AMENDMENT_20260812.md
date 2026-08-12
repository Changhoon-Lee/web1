# SCMC microaneurysm dominant-mode hash amendment

Date: 2026-08-12 (Asia/Singapore)

Prediction commit: `c9f4e6fc0f698ac1afb71b70544e9578f500fd96`

No iterative safe, fail, or repair trajectory had been executed when this defect was found.

## Defect

The public prediction payload stored a raw-byte SHA-256 for an ARPACK eigenvector:

`6f5b5da9432ec5f4a9ca57796e7c25e791cb88c8a67ae695db40a77fe1e83d42`.

That gate is not reproducible because a simple eigenvector is defined only up to nonzero scale and sign, and independently valid eigensolver invocations may return different byte representations of the same one-dimensional eigenspace. The original raw-vector hash is retained as a failed representation gate and is not treated as authoritative.

## Representation-only correction

No input, preprocessing, operator, beta, theta, threshold interval, spectral radius, fixed point, forcing, iteration budget, tolerance, native metric, or confirmatory gate is changed.

The fail operator is diagonalized independently with a dense eigensolver. The real eigenvector associated with the unique eigenvalue of largest modulus is Euclidean-normalized. Its sign is fixed by requiring the largest-magnitude coordinate to be positive. For portable identity comparison, the normalized vector is rounded to 14 decimal digits and its rank-one orthogonal projector is rounded to 13 decimal digits.

Frozen canonical data:

- fail eigenvalue: `-1.0424686141920123`;
- normalized eigenpair residual: `1.1415388872157971e-16`;
- canonical vector SHA-256: `8a3611784b221af1a1100a60c7ba5249908750c820247b015d392b5a40926b52`;
- canonical projector SHA-256: `1fc50d70c2e627c87a6e54c88d0b412b2cfe8dad07be4118cc9e462f4fbc2d76`;
- canonical NPZ SHA-256: `69a9be30041fa3497f5b9dbb991849570e48f952845e5d4f1c378a31c9a37de0`.

The confirmatory identity gate is the canonical projector hash plus the eigenvalue and residual checks. The vector hash is retained only as a deterministic implementation receipt under the stated sign convention.

## Authority

This is a correction of a non-invariant evidence representation before trajectory execution. It does not repair or tune any scientific prediction. If the canonical projector, eigenvalue, residual, or frozen trajectory prediction fails, the campaign fails.

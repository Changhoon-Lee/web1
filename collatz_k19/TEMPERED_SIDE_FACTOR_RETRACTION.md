# Retraction: tempered sixteen-side factor interpretations

The following **Collatz-side interpretations are retracted**:

- `197713451 / 172186884 > 8/7` as the actual `w^(1/16)`-tempered sixteen-side factor;
- `30645584905 / 16529940864 > 9/5` as the actual `w^(1/256)`-tempered sixteen-side factor;
- the corresponding frontier thresholds derived from those two factors.

The Lean arithmetic identities compiled, but the numerical model supplied to the
arithmetic omitted the factor

```text
2^j / 3^(j+1) = (1/2) * (2/3)^(j+1).
```

Therefore compilation did not authenticate the intended Collatz interpretation.

## Valid replacement

The independently certified unweighted finite-sixteen-side theorem gives a strict
factor `8/7`. The isolated, valid 256th-root K19 coefficient-range theorem gives a
global ratio strictly larger than `31/32`. Hence the conservative same-potential
factor is

```text
(31/32) * (8/7) = 31/28 > 1,
```

with reciprocal frontier threshold `28/31`.

The corrected arithmetic/composition surface is
`CorrectedUltraTemperedSideContract.lean`. The valid K19 weight-range statement is
isolated in `UltraTemperedWeightRange.lean`.

No proof or diagnostic should cite the retracted constants as Collatz-side factors.

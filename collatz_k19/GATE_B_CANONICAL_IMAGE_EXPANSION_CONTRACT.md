# Gate B — canonical image expansion contract

## Closed reductions

For the deterministic shortcut-Collatz map and a fixed target, every reachable
numerical source has a unique canonical first-hit record. The map from reachable
sources to canonical records is injective, and the projection from canonical
records back to numerical sources is also injective.

Consequently:

1. the K19 numerical predecessor reservoir lifts to a canonical first-hit word
   reservoir with **exactly zero cardinality loss**;
2. after output canonicalization, collisions between different total hit
   lengths have **exactly zero numerical-output load**;
3. fixed-word affine source uniqueness is already arithmetic cancellation.

Thus neither a new source-residue distribution theorem nor a separate
cross-length numerical-collision exponent belongs in Gate B.

## Exact remaining finite relation

Fix a target `t`, a height parameter `X`, and a finite canonical K19 reservoir
`U_X(t)`.  For a macrodepth `m`, let `E_m` be the finite set of labeled legal
T089 alternatives issued from inputs in `U_X(t)`, and let

```text
out_m : E_m -> CanonicalHit(T,t)
```

be the canonical full output record.

A valid paid certificate must provide explicit quantities `B_m`, `D_m`, and
`H_m` with:

```text
EDGE MASS:       |E_m| >= B_m * |U_X(t)|
REPRESENTATION:  every canonical output has at most D_m labeled preimages
HEIGHT:          source(out_m(e)) <= H_m * X + O_t(1)
```

The representation load should preferably be certified by a finite rank map

```text
rank_m : E_m -> Fin D_m
```

such that `(out_m, rank_m)` is injective.  This makes the load proof purely
finite and exact.

Because canonical source projection is injective, double counting gives

```text
|numerical output sources|
  = |range(out_m)|
  >= |E_m| / D_m
  >= (B_m / D_m) * |U_X(t)|.
```

There is no further arithmetic collision divisor.

## Positive-pressure criterion

Write `gamma = 14551/16000`.  The remaining deficit is

```text
1 - gamma = 1449/16000.
```

For an iterated stationary macrocertificate, the decisive strict inequality is

```text
B > D * H.
```

Equivalently, the canonical image entropy exceeds the sum of the only two
remaining charges:

```text
log B - log D - log H > 0.
```

Under this inequality, choose the macrodepth as a linear function of `log X` so
that

```text
(B / (D*H))^m > X^(1449/16000).
```

Combined with the K19 lower bound, this pays the complete terminal deficit.
The remaining research object is therefore a finite-state branching/height/rank
certificate with a strict positive rational margin.  No source-residue state
and no numerical-collision state should be reintroduced.

## Kill criterion

A proposed Gate B certificate is rejected unless it simultaneously supplies:

- canonical full output words;
- target admissibility;
- positivity;
- exact affine height control;
- an explicit reverse-representation rank or equivalent exact load proof;
- a strict verified margin `B - D*H > 0` (or its weighted-potential analogue).

This is now the single active arrow.

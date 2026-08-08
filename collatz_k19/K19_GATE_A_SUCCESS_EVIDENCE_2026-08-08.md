# K19 Gate A success evidence — 2026-08-08

## Exact workflow identity

- Repository: `Changhoon-Lee/web1`
- Branch: `collatz-k19-gate-clean-20260808`
- Workflow run: `31249565370`
- Final job: `93083633455`
- Head SHA: `24806b5570743e8c955f11a6822246f3ecaccf14`
- Final artifact: `k19-final-direct-lean-31249565370`
- Artifact ID: `9019689967`
- Artifact ZIP digest: `sha256:9002ee34e86a7ca81acb0f2edffef073bb94cc7787bd366e23afcd445c2282bc`

## Raw final verdict

```text
K19_SOURCE_CHUNKED_VALID=PASS
K19_ADAPTIVE_CHUNKED_VALID=PASS
K19_CERTIFICATE_DEPENDENT_BRIDGES_DIRECT_LEAN=PASS
K19_ALL_SEVEN_BRIDGES_BUILD=PASS
K19_ALL_TARGET_THEOREM_BUILD=PASS
K19_AXIOM_AUDIT=PASS_NO_SORRYAX_NO_STUB_AXIOMS
FORMAL_GATE=PASS
```

## Endpoint theorem

```lean
theorem CollatzPredecessorK19.predecessor_count_lower_bound_14551_16000
  {target : Nat}
  (htarget : 0 < target)
  (hmod : target % 3 ≠ 0) :
  ∃ constant : Real,
    0 < constant ∧
    ∀ᶠ x in Filter.atTop,
      constant * x ^ ((14551 : Real) / 16000) ≤
        (predecessorCountReal target x : Real)
```

Equivalently, for every fixed positive target not divisible by 3,

\[
P_t(x)\ge c_t x^{14551/16000}
\]

for all sufficiently large `x`, with `c_t>0`.

## Payload authentication

Source certificate payload:

```text
bytes   1,549,681,956
SHA256  82a71c4e1ca22ea94c0d3338fbea93c8d052e659a65a2101a1643bfdda7f8d79
rows    387,420,489
```

Adaptive potential payload:

```text
bytes   387,420,489
SHA256  728ed6fbe2def7f37e41b5568feefe3553a3d7c43553aee6ee5495f7ae241e39
rows    387,420,489
```

Total exact row propositions assembled into the two public `Valid` boundaries:

```text
774,840,978
```

## Exact trust boundary

The final axiom audit for

```text
CollatzPredecessorK19.predecessor_count_lower_bound_14551_16000
```

contains:

- `propext`;
- `Classical.choice`;
- `Quot.sound`;
- one disclosed native-decide axiom for adaptive metadata;
- eight disclosed native-decide axioms for adaptive row intervals;
- one disclosed native-decide axiom for source metadata;
- eight disclosed native-decide axioms for source row intervals.

It contains no `sorryAx` and no ad hoc certificate-stub axiom. Therefore the correct classification is:

> source-pinned, hash-authenticated, native-assisted Lean theorem; not a pure kernel-reduction of all 774,840,978 finite row computations.

## Mathematical consequence and limit

The formally integrated terminal ceiling is

\[
1-\frac{14551}{16000}=\frac{1449}{16000}=0.0905625.
\]

This closes Gate A. It does not itself prove the Collatz conjecture. The remaining active arrow is the cancellation-sensitive, positivity/height/output-load-paid transfer above `1449/16000`.

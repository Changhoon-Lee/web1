# Gate B — single-numerator paid-transfer contract

**Date:** 2026-08-08  
**Status:** active universal arrow after the successful K19 Gate A.  
**Scope:** this contract governs all subsequent Collatz-complete-proof work on this branch.

## 1. Closed upstream inputs

The following are fixed inputs, not new search objectives.

1. The K19 source certificate is an authenticated Lean theorem.
2. The K19 adaptive certificate is an authenticated Lean theorem.
3. The all-target predecessor lower bound at
   \[
   \gamma=\frac{14551}{16000}=0.9094375
   \]
   is compiled and axiom-audited in Lean.
4. For the exact T089 backward recurrence, all intermediate divisibility conditions collapse to one terminal compatibility numerator congruence
   \[
   3^{R_\pi}\mid C_\pi,
   \qquad
   C_\pi=\sum_j A^j a_j3^{R_\pi-R_j},
   \qquad A=2^{14}.
   \]
5. When compatible, the exact integer source discrepancy is
   \[
   Q_\pi=\Delta_0=\frac{C_\pi}{3^{R_\pi}}.
   \]

## 2. LIVE ARROW

\[
\boxed{
\begin{array}{c}
\text{K19 all-target predecessor reservoir at }14551/16000\\
+\;\text{exact T089 compatibility projector}
\end{array}
\Longrightarrow
\text{actual distinct-output paid terminal pressure}
>
\frac{1449}{16000}
}
\]

No other arrow is active until this one is proved or killed.

## 3. Complete lawful state

Every path state used in a PASS or FAIL certificate must contain enough information to recover or certify all of the following.

- the exact K19 fixed-target path/reservoir state;
- the exact T089 block label and local discrepancy `a`;
- the accumulated exponent `R`;
- the compatibility residue `C mod 3^R`;
- the quotient `Q=C/3^R` whenever the residue vanishes;
- source positivity and the common source-height/cutoff charge;
- the exact numerical output, or a collision label with a proved load bound;
- the terminal-capacity charge;
- all normalization factors, including the local `3^{-r}` compatibility weight.

Marker-only, valuation-only, quotient-free, height-free, or output-free states are inadmissible.

## 4. Exact compatibility projector

For
\[
S_\pi=\sum_i r_i
\]
and the exact affine modular path map `Phi_pi` on `Z/3^K Z`, for every `K >= S_pi`,

\[
3^{-S_\pi}\#\Phi_\pi^{-1}(0)
=
\mathbf 1_{\{3^{R_\pi}\mid C_\pi\}}.
\]

Therefore compatibility is to be counted by the terminal coefficient of the locally `3^{-r}`-weighted transfer, not by raw branch count, raw menu size, or an informal terminal-fiber penalty.

## 5. PASS certificate

A PASS must provide a proof, uniform in every fixed target `t > 0` with `3 ∤ t`, of families `F_N(t)` at unbounded depths or scales such that:

1. every member is a lawful path in the K19 all-target reservoir;
2. every counted member satisfies `3^{R_pi} | C_pi`;
3. the corresponding integer source is positive and lies under one common proved cutoff;
4. numerical-output multiplicity is paid by a proved load bound;
5. all terminal and height charges are included;
6. after those payments, the resulting lower exponent/pressure is strictly larger than
   \[
   \theta=\frac{1449}{16000}=0.0905625;
   \]
7. the resulting theorem is sufficient to contradict every hypothetical nonconvergent Collatz component.

The PASS certificate must state the exact inequality with a positive rational margin, not merely a floating-point estimate.

## 6. FAIL certificate

A FAIL must prove an upper bound at or below `1449/16000` on the complete lawful state by one of the following exact forms.

- a finite-state spectral upper bound with rational interval certification;
- a flow/cut certificate;
- a Farkas-dual certificate;
- a conservation or injection theorem;
- another exact theorem that includes compatibility, quotient/height, actuality, output load, and terminal capacity.

A failure of a truncated or incomplete state is not a Gate-B FAIL certificate.

## 7. Resource and stopping rules

Before any computation, the sprint must state:

- the exact theorem being tested;
- the map from its output to the LIVE ARROW;
- the PASS and FAIL certificate formats;
- the state-completeness audit;
- the resource cap;
- the stop condition.

Stop immediately if the computation omits quotient height, positivity, output identity/load, or terminal payment.

## 8. Frozen work

Until Gate B is resolved, do not start:

- K20 or a larger predecessor certificate;
- `B_53` or a larger fixed modulus;
- larger packet alphabets or raw branch censuses;
- marker-only or capped-valuation automata;
- local gadget searches without a proved injection into the K19 reservoir;
- any result whose consumer does not appear explicitly in the PASS inequality.

## 9. Current exact subproblem

The immediate mathematical target is:

> Prove an exponential lower bound for K19-reservoir paths satisfying
> `v3(C_pi) >= R_pi`, jointly with a subexponential or sufficiently small
> exponential bound for `|Q_pi|`, source cutoff, and numerical-output load;
> or produce a complete-state exact no-go.

Equal-valuation cancellation is no longer an informal phenomenon: it is exactly cancellation among the summands
\[
A^j a_j3^{R_\pi-R_j}
\]
inside `C_pi`.

## 10. Claim discipline

Closing Gate A and formalizing the compatibility collapse are substantial positive advances. They do not by themselves prove the Collatz conjecture or establish decisive proximity. That claim becomes justified only after the LIVE ARROW and the final contradiction theorem are both closed.

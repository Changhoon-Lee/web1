# T089 global compatibility collapse and normalized terminal-fiber projector

**Date:** 2026-08-08  
**Status:** exact paper-level theorem; independently exhaustively regression-checked in Python and C++; not yet Lean-formalized; not a proof of the Collatz conjecture.

## 1. Source recurrence

For a sequence of `N` selected T089 blocks, write the exact source-side discrepancy recurrence as

\[
\Delta_i=a_i+A\frac{\Delta_{i+1}}{3^{r_i}},
\qquad 3^{r_i}\mid\Delta_{i+1},
\qquad A=2^{14},
\qquad \Delta_N=0.
\]

Here every `a_i` is the exact local affine discrepancy and every `r_i` is the odd count of the selected alternative. Only `gcd(A,3)=1` is used below.

## 2. Single-numerator theorem

Define prefix denominator exponents

\[
R_0=0,
\qquad
R_j=\sum_{k=0}^{j-1}r_k\quad(1\le j\le N-1),
\qquad
R=R_{N-1}=\sum_{k=0}^{N-2}r_k.
\]

The final block exponent `r_{N-1}` is absent from `R`, because `3^{r_{N-1}} \mid \Delta_N=0` is automatic. Define the terminal compatibility numerator

\[
\boxed{
C_\pi=
\sum_{j=0}^{N-1}
A^j a_j\,3^{R-R_j}.
}
\]

### Theorem 2.1 — all global divisibility conditions collapse to one

The following are equivalent.

1. The backward recurrence produces integers `Delta_{N-1},...,Delta_0`.
2. Every exact intermediate condition `3^{r_i} | Delta_{i+1}` holds.
3. The single terminal congruence
   \[
   \boxed{3^R\mid C_\pi}
   \]
   holds.

When these conditions hold, the source discrepancy is uniquely

\[
\boxed{\Delta_0=C_\pi/3^R.}
\]

More generally, put

\[
C_i=
\sum_{j=i}^{N-1}
A^{j-i}a_j\,3^{R-R_j},
\qquad
D_i=3^{R-R_i}.
\]

Then

\[
\boxed{\Delta_i=C_i/D_i}
\]

for every `0 <= i <= N-1`.

### Proof

The definitions give

\[
C_i=a_iD_i+A C_{i+1},
\qquad
D_i=3^{r_i}D_{i+1}.
\]

If `D_i | C_i`, then `D_i | A C_{i+1}`. Since `gcd(A,D_i)=1`, one has `D_i | C_{i+1}`, hence in particular `D_{i+1}|C_{i+1}`. Starting from `D_0=3^R | C_0=C_pi`, induction proves every `C_i/D_i` integral. The displayed recursion then gives the exact T089 recurrence and its divisibility conditions. Conversely, repeatedly substituting an integral recurrence with `Delta_N=0` gives `Delta_i=C_i/D_i`, hence `3^R|C_pi`. This also proves uniqueness.

## 3. Exact modular terminal-fiber theorem

Let

\[
S=\sum_{i=0}^{N-1}r_i=R+r_{N-1}
\]

and, on `G_K = Z/3^K Z`, define the forward affine map of block `i`

\[
\Phi_i(\delta)=3^{r_i}A^{-1}(\delta-a_i).
\]

Let `Phi_pi = Phi_{N-1} o ... o Phi_0`.

### Theorem 3.1 — terminal fiber is an exact compatibility projector

For every `K >= S`,

\[
\boxed{
\#\Phi_\pi^{-1}(0)=
\begin{cases}
3^S,&3^R\mid C_\pi,\\
0,&3^R\nmid C_\pi.
\end{cases}
}
\]

If the path is compatible, every modular source alias satisfies

\[
\boxed{
\delta\equiv\Delta_0\pmod{3^{K-S}}.
}
\]

Equivalently,

\[
\boxed{
3^{-S}\#\Phi_\pi^{-1}(0)
=
\mathbf 1_{\{3^R\mid C_\pi\}}.
}
\]

### Proof

Direct composition gives

\[
A^N\Phi_\pi(\delta)
\equiv
3^S\delta-3^{r_{N-1}}C_\pi
\pmod{3^K}.
\]

Because `K >= S`, the equation `Phi_pi(delta)=0` is solvable exactly when `3^S` divides `3^{r_{N-1}} C_pi`, i.e. exactly when `3^R | C_pi`. In the compatible case `C_pi=3^R Delta_0`, so the equation is

\[
3^S(\delta-\Delta_0)\equiv0\pmod{3^K},
\]

which has exactly `3^S` solutions and is equivalent to the displayed congruence.

## 4. Exact weighted-operator representation

For a labeled path `pi`, use local weight

\[
w(\pi)=3^{-S}=\prod_i3^{-r_i}.
\]

Theorem 3.1 gives, for every finite family `F` and every `K` at least the largest `S(pi)`,

\[
\boxed{
\#\{\pi\in F:\pi\text{ is globally integral}\}
=
\sum_{\delta\in G_K}
\sum_{\pi\in F}
3^{-S(\pi)}
\mathbf 1_{\{\Phi_\pi(\delta)=0\}}.
}
\]

Thus the previously informal “growing-precision terminal fiber” is not an unspecified limiting penalty. It splits exactly into:

1. **compatibility:** the single valuation event `v3(C_pi) >= R(pi)`, represented by a terminal coefficient of the local `3^{-r}`-weighted transfer;
2. **alias/height resolution:** after compatibility, the extra precision `K-S` only separates the distinguished integer source `Delta_0` from its modular aliases;
3. **actuality and output payment:** positivity, common cutoff and numerical-output load remain separate requirements.

## 5. What this changes in Gate B

The exact live state no longer needs an unstructured history of every intermediate divisibility test. For a complete labeled path it is enough to retain the recursively updated pair

\[
(R,C_\pi\bmod 3^R)
\]

plus the quotient `C_pi/3^R` when the residue vanishes. Equal-valuation cancellation is precisely cancellation among the summands

\[
A^j a_j3^{R-R_j}
\]

inside `C_pi`.

The next quantitative theorem is therefore sharply stated:

> On the exponent-sized K19 fixed-target path reservoir, prove a lower bound for the `3^{-r}`-weighted terminal coefficient at `C_pi=0 mod 3^{R(pi)}`, while simultaneously bounding `|C_pi|/3^{R(pi)}` and numerical-output load strongly enough to exceed `1449/16000` paid pressure; or prove an exact upper-bound/no-go on this complete state.

## 6. Scope boundary

This theorem closes the **representation and compatibility-collapse** sub-arrow. It does not prove that an exponent-sized fixed-target reservoir has enough compatible paths. It does not pay positivity, height, numerical-output collapse or final terminal capacity. Therefore it does not establish decisive proximity to a complete Collatz proof.

## 7. Verification

Two independent finite regressions accompany this note.

- Python: 4,288,305 exhaustive integer-recurrence cases and 21,690 modular-fiber cases.
- C++: an independently structured exhaustive regression over the same theorem, plus deterministic randomized large-integer cases.

Both print `PASS`.

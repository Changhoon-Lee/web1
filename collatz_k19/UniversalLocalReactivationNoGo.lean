import Mathlib

/-!
# Bounded-potential obstruction to universal local reactivation

Any self-reproducing operation that multiplies one nonnegative potential by a
fixed factor on every generation can be iterated.  If a separate capacity or
harmonic theorem gives a uniform upper bound, a finite geometric-overflow
witness yields an immediate contradiction.

This abstract lemma records the exact logical obstruction used to rule out a
badness-blind, universally applicable Collatz fibre theorem.  A viable theorem
must therefore consume some nonlocal hypothesis specific to a hypothetical bad
component, or fail to reproduce its own input class indefinitely.
-/

namespace UniversalLocalReactivationNoGo

/-- Iterating a one-step multiplicative lower bound. -/
theorem iterated_lower_bound
    {kappa : ℝ} (hkappa : 0 ≤ kappa)
    (mass : Nat → ℝ)
    (hgrowth : ∀ generation,
      kappa * mass generation ≤ mass (generation + 1)) :
    ∀ generation,
      kappa ^ generation * mass 0 ≤ mass generation := by
  intro generation
  induction generation with
  | zero => simp
  | succ generation inductionHypothesis =>
      calc
        kappa ^ (generation + 1) * mass 0 =
            kappa * (kappa ^ generation * mass 0) := by ring
        _ ≤ kappa * mass generation :=
          mul_le_mul_of_nonneg_left inductionHypothesis hkappa
        _ ≤ mass (generation + 1) := hgrowth generation

/-- A finite geometric-overflow witness contradicts a uniform capacity bound.
This is the exact finite form needed in a certificate: no asymptotic limit is
hidden inside the theorem. -/
theorem contradiction_of_growth_capacity_and_overflow
    {kappa capacity : ℝ} (hkappa : 0 ≤ kappa)
    (mass : Nat → ℝ)
    (hgrowth : ∀ generation,
      kappa * mass generation ≤ mass (generation + 1))
    (hcapacity : ∀ generation, mass generation ≤ capacity)
    {witnessGeneration : Nat}
    (hoverflow : capacity <
      kappa ^ witnessGeneration * mass 0) : False := by
  have hlower := iterated_lower_bound hkappa mass hgrowth witnessGeneration
  have hupper := hcapacity witnessGeneration
  linarith

#print axioms UniversalLocalReactivationNoGo.iterated_lower_bound
#print axioms UniversalLocalReactivationNoGo.contradiction_of_growth_capacity_and_overflow

end UniversalLocalReactivationNoGo

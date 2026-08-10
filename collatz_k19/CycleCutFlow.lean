import Mathlib

/-!
# Algebraic core of the cycle cut

The Collatz-specific facts (the residue-two return cycle, off-cycle numerical
forest, and first-crossing shell) are separate. This file records the exact
algebra used when local q-weighted inequalities are substituted around a
cycle.
-/

namespace CycleCutFlow

/-- A closed return inequality leaves an off-cycle remainder. -/
theorem return_gap {q A B : ℝ} {cost : ℕ}
    (hreturn : A ≤ q ^ cost * A + B) :
    (1 - q ^ cost) * A ≤ B := by
  nlinarith

/-- Positivity of the cycle-cut coefficient once the return discount is
strictly smaller than one. -/
theorem return_factor_pos {q : ℝ} {cost : ℕ}
    (hpow : q ^ cost < 1) :
    0 < 1 - q ^ cost := by
  exact sub_pos.mpr hpow

/-- Substitution through two successive cycle edges. Repeating this lemma
unrolls an arbitrary finite cycle. -/
theorem two_edge_unroll {A₀ A₁ r₀ r₁ B₀ B₁ : ℝ}
    (hr₀ : 0 ≤ r₀)
    (h₀ : A₀ ≤ r₀ * A₁ + B₀)
    (h₁ : A₁ ≤ r₁ * A₀ + B₁) :
    A₀ ≤ (r₀ * r₁) * A₀ + (B₀ + r₀ * B₁) := by
  calc
    A₀ ≤ r₀ * A₁ + B₀ := h₀
    _ ≤ r₀ * (r₁ * A₀ + B₁) + B₀ := by
      simpa [add_comm] using
        (add_le_add_right (mul_le_mul_of_nonneg_left h₁ hr₀) B₀)
    _ = (r₀ * r₁) * A₀ + (B₀ + r₀ * B₁) := by ring

#print axioms CycleCutFlow.return_gap
#print axioms CycleCutFlow.return_factor_pos
#print axioms CycleCutFlow.two_edge_unroll

end CycleCutFlow

import Mathlib

/-!
# Algebraic core of the valuation-one odd-block side gain

For the shortcut Collatz map, an odd state `x` with `v₂(3x+1)=1` has next odd
state `(3x+1)/2`.  Replacing the continuation term by the side predecessor
`3x+1` loses exactly `1/(x(3x+1))` in reciprocal mass.

At the terminal state of a maximal such run, `v₂(3x+1)≥2`; using only the
coarse next-odd bound `(3x+1)/4` gives a reciprocal surplus
`(2x-1)/(x(3x+1))`, which dominates `1/(2(x+1))` for `x≥1`.

The finite geometric comparison showing that one terminal surplus pays all
preceding deficits is recorded separately by an exact integer certificate.
-/

namespace ValuationOneBlockAlgebra

/-- Exact reciprocal deficit at a valuation-one odd step. -/
theorem valuation_one_deficit_identity
    {x : ℝ} (hx : x ≠ 0) (hthree : 3 * x + 1 ≠ 0) :
    1 / x - (1 / (3 * x + 1) + 1 / ((3 * x + 1) / 2)) =
      1 / (x * (3 * x + 1)) := by
  have hshortcut :
      1 / ((3 * x + 1) / 2) = 2 / (3 * x + 1) := by
    field_simp [hthree]
  rw [hshortcut]
  field_simp [hx, hthree]
  ring

/-- Exact lower surplus obtained when the terminal odd continuation is at most
`(3x+1)/4`. -/
theorem terminal_four_surplus_identity
    {x : ℝ} (hx : x ≠ 0) (hthree : 3 * x + 1 ≠ 0) :
    1 / (3 * x + 1) + 1 / ((3 * x + 1) / 4) - 1 / x =
      (2 * x - 1) / (x * (3 * x + 1)) := by
  have hshortcut :
      1 / ((3 * x + 1) / 4) = 4 / (3 * x + 1) := by
    field_simp [hthree]
  rw [hshortcut]
  field_simp [hx, hthree]
  ring

/-- The terminal lower surplus dominates the simple scale bound used in the
geometric deficit estimate. -/
theorem terminal_surplus_ge_scale
    {x : ℝ} (hx : 1 ≤ x) :
    1 / (2 * (x + 1)) ≤ (2 * x - 1) / (x * (3 * x + 1)) := by
  have hx0 : 0 < x := lt_of_lt_of_le zero_lt_one hx
  have hxp1 : 0 < x + 1 := by linarith
  have hthree : 0 < 3 * x + 1 := by linarith
  apply (div_le_div_iff₀ (mul_pos (by positivity) hxp1)
    (mul_pos hx0 hthree)).2
  nlinarith [sq_nonneg (x - 1)]

/-- Elementary denominator bounds behind each preterminal deficit. -/
theorem deficit_denominator_ge_square
    {A : ℝ} (hA : 2 ≤ A) :
    A ^ 2 ≤ (A - 1) * (3 * A - 2) := by
  nlinarith [sq_nonneg (A - 2)]

#print axioms ValuationOneBlockAlgebra.valuation_one_deficit_identity
#print axioms ValuationOneBlockAlgebra.terminal_four_surplus_identity
#print axioms ValuationOneBlockAlgebra.terminal_surplus_ge_scale
#print axioms ValuationOneBlockAlgebra.deficit_denominator_ge_square

end ValuationOneBlockAlgebra

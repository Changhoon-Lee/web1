import Mathlib

/-!
# From bounded first-hit depth to discounted frontier mass

This conversion is deliberately external to the adaptive K19 minimizer.  Once
a numerical predecessor family is known to have first-hit depth at most `B`,
a geometric rank `q^depth` loses at most the single factor `q^B`.  No claim is
made that the old unweighted adaptive critical tree remains critical after a
`q` decoration.
-/

namespace DepthBoundedToDiscountedFrontier

open scoped BigOperators

/-- Powers of a number in `[0,1]` decrease with the natural exponent. -/
theorem pow_le_pow_of_le_exponent
    {q : ℝ} (hq0 : 0 ≤ q) (hq1 : q ≤ 1)
    {depth bound : ℕ} (hdepth : depth ≤ bound) :
    q ^ bound ≤ q ^ depth := by
  obtain ⟨extra, rfl⟩ := Nat.exists_eq_add_of_le hdepth
  rw [pow_add]
  have hqextra : q ^ extra ≤ 1 := by
    exact pow_le_one₀ hq0 hq1
  have hqdepth : 0 ≤ q ^ depth := pow_nonneg hq0 _
  nlinarith

/-- A finite nonnegative family supported at depths at most `bound` retains at
least `q^bound` of its unweighted mass after geometric depth discounting. -/
theorem discounted_sum_ge_uniform_floor
    {α : Type*} [DecidableEq α]
    (family : Finset α) (depth : α → ℕ) (weight : α → ℝ)
    {q : ℝ} (hq0 : 0 ≤ q) (hq1 : q ≤ 1) {bound : ℕ}
    (hdepth : ∀ x ∈ family, depth x ≤ bound)
    (hweight : ∀ x ∈ family, 0 ≤ weight x) :
    q ^ bound * ∑ x ∈ family, weight x ≤
      ∑ x ∈ family, q ^ depth x * weight x := by
  rw [Finset.mul_sum]
  apply Finset.sum_le_sum
  intro x hx
  exact mul_le_mul_of_nonneg_right
    (pow_le_pow_of_le_exponent hq0 hq1 (hdepth x hx))
    (hweight x hx)

/-- Consumer form: an unweighted lower bound at bounded depth immediately gives
a discounted lower bound with the single explicit factor `q^bound`. -/
theorem discounted_lower_bound_of_bounded_depth
    {α : Type*} [DecidableEq α]
    (family : Finset α) (depth : α → ℕ) (weight : α → ℝ)
    {q lower : ℝ} (hq0 : 0 ≤ q) (hq1 : q ≤ 1) {bound : ℕ}
    (hdepth : ∀ x ∈ family, depth x ≤ bound)
    (hweight : ∀ x ∈ family, 0 ≤ weight x)
    (hlower : lower ≤ ∑ x ∈ family, weight x) :
    q ^ bound * lower ≤
      ∑ x ∈ family, q ^ depth x * weight x := by
  have hqpow : 0 ≤ q ^ bound := pow_nonneg hq0 _
  exact (mul_le_mul_of_nonneg_left hlower hqpow).trans
    (discounted_sum_ge_uniform_floor family depth weight hq0 hq1
      hdepth hweight)

#print axioms DepthBoundedToDiscountedFrontier.pow_le_pow_of_le_exponent
#print axioms DepthBoundedToDiscountedFrontier.discounted_lower_bound_of_bounded_depth

end DepthBoundedToDiscountedFrontier

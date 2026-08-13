import Mathlib

/-!
# Monotone weakening of a tempered coefficient lower bound

For any base `w ≥ 1`, decreasing the temper exponent decreases `w^tau`.
Consequently a lower bound already proved with `w^(1/16)` immediately implies
the same lower bound with `w^(1/256)`, without changing any spatial exponent,
uniform constant, target, source, or cutoff.
-/

namespace UltraTemperingMonotonicity

/-- Pointwise coefficient monotonicity from sixteenth-root to 256th-root. -/
theorem rpow_one_over_256_le_one_over_16
    {weight : ℝ} (hweight : 1 ≤ weight) :
    weight ^ ((1 : ℝ) / 256) ≤ weight ^ ((1 : ℝ) / 16) := by
  exact Real.rpow_le_rpow_of_exponent_le hweight (by norm_num)

/-- Generic lower-bound transfer: all non-coefficient factors are untouched. -/
theorem lower_bound_transfer
    {constant weight scale count : ℝ}
    (hconstant : 0 ≤ constant) (hscale : 0 ≤ scale)
    (hweight : 1 ≤ weight)
    (hlower :
      constant * (weight ^ ((1 : ℝ) / 16)) * scale ≤ count) :
    constant * (weight ^ ((1 : ℝ) / 256)) * scale ≤ count := by
  have hcoefficient :
      constant * (weight ^ ((1 : ℝ) / 256)) ≤
        constant * (weight ^ ((1 : ℝ) / 16)) :=
    mul_le_mul_of_nonneg_left
      (rpow_one_over_256_le_one_over_16 hweight) hconstant
  exact (mul_le_mul_of_nonneg_right hcoefficient hscale).trans hlower

/-- Exact exponent ordering used by the bridge. -/
theorem exponent_order :
    (1 : ℝ) / 256 ≤ (1 : ℝ) / 16 := by
  norm_num

#print axioms UltraTemperingMonotonicity.rpow_one_over_256_le_one_over_16
#print axioms UltraTemperingMonotonicity.lower_bound_transfer

end UltraTemperingMonotonicity

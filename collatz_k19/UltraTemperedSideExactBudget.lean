import Mathlib

/-!
# Exact 1/256-tempered sixteen-side budget

Authenticated K19 extrema:

* minimum weight `1497192`,
* maximum weight `4166117961`.

The exact integer inequality

`1497192 * 32^256 > 4166117961 * 31^256`

implies a global 256th-root coefficient ratio greater than `31/32`.
Combining this with the same sixteen bad-spine size ratios gives the exact
conservative side factor

`30645584905 / 16529940864 > 9/5`.
-/

namespace UltraTemperedSideExactBudget

noncomputable def weightMinimum : ℝ := 1497192
noncomputable def weightMaximum : ℝ := 4166117961
noncomputable def ultraTemperExponent : ℝ := (1 : ℝ) / 256

/-- Exact integer certificate behind the `31/32` 256th-root ratio. -/
theorem exact_weight_power_certificate :
    (4166117961 : ℕ) * 31 ^ (256 : ℕ) <
      (1497192 : ℕ) * 32 ^ (256 : ℕ) := by
  norm_num

/-- Global K19 256th-root range ratio exceeds `31/32`. -/
theorem ultra_tempered_weight_ratio_gt_thirtyOne_over_thirtyTwo :
    (31 : ℝ) / 32 <
      (weightMinimum / weightMaximum) ^ ultraTemperExponent := by
  have hminPositive : 0 < weightMinimum := by norm_num [weightMinimum]
  have hmaxPositive : 0 < weightMaximum := by norm_num [weightMaximum]
  have hratioNonnegative : 0 ≤ weightMinimum / weightMaximum :=
    div_nonneg hminPositive.le hmaxPositive.le
  have hbase :
      ((31 : ℝ) / 32) ^ (256 : ℝ) <
        weightMinimum / weightMaximum := by
    norm_num [weightMinimum, weightMaximum]
  have hroot :=
    (Real.lt_rpow_inv_iff_of_pos
      (by norm_num : 0 ≤ (31 : ℝ) / 32)
      hratioNonnegative
      (by norm_num : 0 < (256 : ℝ))).2 hbase
  simpa [ultraTemperExponent, div_eq_mul_inv] using hroot

/-- Exact geometric sum used by the sixteen-side certificate. -/
theorem sixteen_geometric_sum_identity :
    ∑ j ∈ Finset.range 16, ((2 : ℝ) / 3) ^ (j + 1) =
      (85962370 : ℝ) / 43046721 := by
  norm_num [Finset.sum_range_succ]

/-- Exact conservative 1/256-tempered factor for the first sixteen side targets. -/
noncomputable def ultraTemperedSixteenSideFactor : ℝ :=
  (30645584905 : ℝ) / 16529940864

/-- Exact rational reconstruction of the conservative side factor. -/
theorem ultra_tempered_side_factor_identity :
    (31 : ℝ) / 32 * ((23 : ℝ) / 24) *
        (∑ j ∈ Finset.range 16, ((2 : ℝ) / 3) ^ (j + 1)) =
      ultraTemperedSixteenSideFactor := by
  rw [sixteen_geometric_sum_identity]
  norm_num [ultraTemperedSixteenSideFactor]

/-- The new same-potential side factor clears `9/5`. -/
theorem ultraTemperedSixteenSideFactor_gt_nine_fifths :
    (9 : ℝ) / 5 < ultraTemperedSixteenSideFactor := by
  norm_num [ultraTemperedSixteenSideFactor]

/-- Hence its exact reciprocal threshold lies below `5/9`. -/
theorem ultraTemperedFrontierThreshold_lt_five_ninths :
    (16529940864 : ℝ) / 30645584905 < (5 : ℝ) / 9 := by
  norm_num

/-- Exact positive margin over `9/5`. -/
theorem ultraTemperedSixteenSideFactor_margin :
    ultraTemperedSixteenSideFactor - (9 : ℝ) / 5 =
      (4458456749 : ℝ) / 82649704320 := by
  norm_num [ultraTemperedSixteenSideFactor]

#print axioms UltraTemperedSideExactBudget.exact_weight_power_certificate
#print axioms UltraTemperedSideExactBudget.ultra_tempered_weight_ratio_gt_thirtyOne_over_thirtyTwo
#print axioms UltraTemperedSideExactBudget.sixteen_geometric_sum_identity
#print axioms UltraTemperedSideExactBudget.ultraTemperedSixteenSideFactor_gt_nine_fifths
#print axioms UltraTemperedSideExactBudget.ultraTemperedFrontierThreshold_lt_five_ninths

end UltraTemperedSideExactBudget

import Mathlib

/-!
# Exact sixteenth-root side normalization budget

This file isolates the finite arithmetic behind the same-exponent tempered K19
bridge.  It does not depend on the large K19 generated certificate.

The authenticated coefficient range is

* `w_min = 1497192`,
* `w_max = 4166117961`.

The integer inequality

`w_min * 5^16 > w_max * 3^16`

implies that every output/input sixteenth-root weight ratio is larger than
`3/5`.  Combining this with the conservative sixteen-side spatial ratios gives

`(3/5) * (23/24) * Σ_{j=1}^{16} (2/3)^j
 = 197713451 / 172186884 > 8/7`.
-/

namespace TemperedSideExactBudget

noncomputable def temperExponent : ℝ := (1 : ℝ) / 16
noncomputable def weightMinimum : ℝ := 1497192
noncomputable def weightMaximum : ℝ := 4166117961

/-- Exact integer certificate behind the global sixteenth-root ratio. -/
theorem weight_range_power_certificate :
    (4166117961 : ℕ) * 3 ^ 16 < 1497192 * 5 ^ 16 := by
  norm_num

/-- Every pair of weights in the authenticated range has sixteenth-root ratio
strictly larger than `3/5`. -/
theorem tempered_weight_ratio_gt_three_fifths
    {outputWeight inputWeight : ℝ}
    (houtput : weightMinimum ≤ outputWeight)
    (hinput : inputWeight ≤ weightMaximum)
    (hinputPositive : 0 < inputWeight) :
    (3 : ℝ) / 5 < (outputWeight / inputWeight) ^ temperExponent := by
  have hminPositive : 0 < weightMinimum := by norm_num [weightMinimum]
  have hmaxPositive : 0 < weightMaximum := by norm_num [weightMaximum]
  have houtputPositive : 0 < outputWeight := hminPositive.trans_le houtput
  have hratioNonnegative : 0 ≤ outputWeight / inputWeight :=
    div_nonneg houtputPositive.le hinputPositive.le
  have hratioLower :
      weightMinimum / weightMaximum ≤ outputWeight / inputWeight := by
    apply (div_le_div_iff₀ hmaxPositive hinputPositive).2
    calc
      weightMinimum * inputWeight ≤ weightMinimum * weightMaximum :=
        mul_le_mul_of_nonneg_left hinput hminPositive.le
      _ ≤ outputWeight * weightMaximum :=
        mul_le_mul_of_nonneg_right houtput hmaxPositive.le
  have hbase :
      ((3 : ℝ) / 5) ^ (16 : ℝ) < weightMinimum / weightMaximum := by
    norm_num [weightMinimum, weightMaximum]
  have hpow :
      ((3 : ℝ) / 5) ^ (16 : ℝ) < outputWeight / inputWeight :=
    hbase.trans_le hratioLower
  have hroot :=
    (Real.lt_rpow_inv_iff_of_pos
      (by norm_num : 0 ≤ (3 : ℝ) / 5)
      hratioNonnegative
      (by norm_num : 0 < (16 : ℝ))).2 hpow
  simpa [temperExponent, div_eq_mul_inv] using hroot

/-- Exact geometric sum used by the sixteen-side certificate. -/
theorem sixteen_geometric_sum_identity :
    ∑ j ∈ Finset.range 16, ((2 : ℝ) / 3) ^ (j + 1) =
      (85962370 : ℝ) / 43046721 := by
  norm_num [Finset.sum_range_succ]

noncomputable def temperedSixteenSideFactor : ℝ :=
  (197713451 : ℝ) / 172186884

/-- Exact rational reconstruction of the conservative side factor. -/
theorem tempered_side_factor_identity :
    (3 : ℝ) / 5 * ((23 : ℝ) / 24) *
        (∑ j ∈ Finset.range 16, ((2 : ℝ) / 3) ^ (j + 1)) =
      temperedSixteenSideFactor := by
  rw [sixteen_geometric_sum_identity]
  norm_num [temperedSixteenSideFactor]

/-- The same-potential conservative factor clears `8/7`. -/
theorem tempered_side_factor_gt_eight_sevenths :
    (8 : ℝ) / 7 < temperedSixteenSideFactor := by
  norm_num [temperedSixteenSideFactor]

/-- Exact positive margin. -/
theorem tempered_side_factor_margin :
    temperedSixteenSideFactor - (8 : ℝ) / 7 =
      (6499085 : ℝ) / 1205308188 := by
  norm_num [temperedSixteenSideFactor]

#print axioms TemperedSideExactBudget.tempered_weight_ratio_gt_three_fifths
#print axioms TemperedSideExactBudget.sixteen_geometric_sum_identity
#print axioms TemperedSideExactBudget.tempered_side_factor_gt_eight_sevenths

end TemperedSideExactBudget

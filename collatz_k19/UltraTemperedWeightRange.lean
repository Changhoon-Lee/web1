import Mathlib

/-!
# Valid 1/256-tempered K19 coefficient-range theorem

Authenticated K19 extrema:

* minimum coefficient `1497192`,
* maximum coefficient `4166117961`.

The exact integer inequality

`4166117961 * 31^256 < 1497192 * 32^256`

implies that the global output/input ratio of 256th-root coefficients is
strictly larger than `31/32`.

This module contains no side-size calculation; it is unaffected by the
separate retraction of the invalid `9/5` side interpretation.
-/

namespace UltraTemperedWeightRange

noncomputable def weightMinimum : ℝ := 1497192
noncomputable def weightMaximum : ℝ := 4166117961
noncomputable def ultraTemperExponent : ℝ := (1 : ℝ) / 256

/-- Exact natural-number certificate. -/
theorem exact_power_certificate :
    (4166117961 : ℕ) * 31 ^ (256 : ℕ) <
      (1497192 : ℕ) * 32 ^ (256 : ℕ) := by
  norm_num

/-- Global 256th-root coefficient range ratio. -/
theorem tempered_weight_ratio_gt_thirtyOne_over_thirtyTwo :
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

#print axioms UltraTemperedWeightRange.exact_power_certificate
#print axioms UltraTemperedWeightRange.tempered_weight_ratio_gt_thirtyOne_over_thirtyTwo

end UltraTemperedWeightRange

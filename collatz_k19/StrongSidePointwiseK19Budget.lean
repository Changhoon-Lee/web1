import Mathlib

/-!
# Strong side-factor / pointwise K19 critical budget

The exact all-row critical-one scan of the authenticated K19 coefficient vector
has global minimum

`8747235 / 9917332`.

A separate bad-spine calculation gives a finite sixteen-side critical factor
strictly larger than `8/7`.  This file records the exact scalar closure:

* every scanned K19 row clears `7/8`, and
* `(8/7) * (8747235/9917332) > 1`.

This is deliberately only a scalar interface.  It does not identify the
unweighted side mass with the coefficient-weighted K19 state mass; that
numerical normalization/composition theorem remains a separate obligation.
-/

namespace StrongSidePointwiseK19Budget

noncomputable def k19CriticalOneMinimum : ℝ :=
  (8747235 : ℝ) / 9917332

/-- Exact pointwise floor obtained by the full `3^18` K19 row scan. -/
theorem k19CriticalOneMinimum_gt_seven_eighths :
    (7 : ℝ) / 8 < k19CriticalOneMinimum := by
  norm_num [k19CriticalOneMinimum]

/-- Exact scalar product after the strengthened sixteen-side factor. -/
theorem eight_sevenths_times_k19Minimum_gt_one :
    (1 : ℝ) < (8 : ℝ) / 7 * k19CriticalOneMinimum := by
  norm_num [k19CriticalOneMinimum]

/-- Reduced exact form of the product and its positive margin. -/
theorem exact_product_identity :
    (8 : ℝ) / 7 * k19CriticalOneMinimum =
      (2499210 : ℝ) / 2479333 := by
  norm_num [k19CriticalOneMinimum]

/-- Generic composition surface, conditional on a lawful normalization map
between the side potential and the K19 coefficient potential. -/
theorem composition_of_strong_side_and_pointwise_retention
    {side retention : ℝ}
    (hside : (8 : ℝ) / 7 < side)
    (hretention : (7 : ℝ) / 8 ≤ retention) :
    1 < side * retention := by
  have hpositive : (0 : ℝ) < (7 : ℝ) / 8 := by norm_num
  have hscaled := mul_lt_mul_of_pos_right hside hpositive
  have hsidePositive : 0 < side := by nlinarith
  have hlower : side * ((7 : ℝ) / 8) ≤ side * retention :=
    mul_le_mul_of_nonneg_left hretention hsidePositive.le
  norm_num at hscaled
  exact hscaled.trans_le hlower

#print axioms StrongSidePointwiseK19Budget.k19CriticalOneMinimum_gt_seven_eighths
#print axioms StrongSidePointwiseK19Budget.eight_sevenths_times_k19Minimum_gt_one
#print axioms StrongSidePointwiseK19Budget.composition_of_strong_side_and_pointwise_retention

end StrongSidePointwiseK19Budget

import Mathlib

/-!
# Exact scalar budget closure for the bad-spine route

The authenticated all-`3^18` K19 critical-one census has total retention

`7092010965587945 / 7254173737686134`.

The valuation-one bad-spine argument supplies a separate critical side-mass
factor strictly larger than `31/30`. This file records the exact rational fact
that the K19 aggregate retention is larger than `30/31`, so the two certified
scalar budgets compose to a factor strictly larger than one.

This is not an occupation theorem: a later argument must still show that the
actual hypothetical bad component realizes retention at least `30/31`.
-/

namespace BadSpineCriticalBudget

noncomputable def k19AggregateRetention : ℝ :=
  (7092010965587945 : ℝ) / 7254173737686134

/-- The exact all-row K19 aggregate retention clears the strengthened
reciprocal side budget. -/
theorem k19AggregateRetention_gt_thirty_over_thirtyOne :
    (30 : ℝ) / 31 < k19AggregateRetention := by
  norm_num [k19AggregateRetention]

/-- Exact scalar closure: the certified `31/30` side factor pays the complete
all-row K19 aggregate deficit with strict margin. -/
theorem side_factor_times_k19AggregateRetention_gt_one :
    (1 : ℝ) < (31 : ℝ) / 30 * k19AggregateRetention := by
  norm_num [k19AggregateRetention]

/-- Generic composition surface for a future bad-component occupation theorem. -/
theorem composition_of_side_and_occupation
    {side retention : ℝ}
    (hside : (31 : ℝ) / 30 < side)
    (hretention : (30 : ℝ) / 31 ≤ retention) :
    1 < side * retention := by
  have hpositive : (0 : ℝ) < (30 : ℝ) / 31 := by norm_num
  have hscaled := mul_lt_mul_of_pos_right hside hpositive
  have hlower : side * ((30 : ℝ) / 31) ≤ side * retention := by
    have hsidePositive : 0 < side := by
      nlinarith
    exact mul_le_mul_of_nonneg_left hretention hsidePositive.le
  norm_num at hscaled
  exact hscaled.trans_le hlower

#print axioms BadSpineCriticalBudget.k19AggregateRetention_gt_thirty_over_thirtyOne
#print axioms BadSpineCriticalBudget.side_factor_times_k19AggregateRetention_gt_one
#print axioms BadSpineCriticalBudget.composition_of_side_and_occupation

end BadSpineCriticalBudget

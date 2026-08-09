import DepthBudgetRetarded

/-!
# Choice-valued depth-budgeted retarded propagation

At each current state and time, the system may choose a different retarded
expression.  Every chosen leaf carries a natural depth cost bounded by one
common `maxCost`.  The same exponential lower bound then propagates while the
available orbit-depth budget grows only linearly with the number of retarded
intervals.
-/

namespace DepthBudgetRetarded
namespace Expr

/-- Choice-valued interval induction with a linear depth budget. -/
theorem choice_exponential_lower_bound_on_intervals {index : Type*}
    (values : index → ℝ → ℕ → ℝ)
    (coefficients : index → ℝ)
    {delta lambda mu nu : ℝ} {maxCost : ℕ}
    (hdelta : 0 ≤ delta) (hlambda : 1 < lambda)
    (hmu : 0 < mu)
    (hbudgetMono : ∀ i y, Monotone (values i y))
    (hchoice : ∀ i y budget, nu ≤ y → maxCost ≤ budget →
      ∃ expr : Expr index,
        expr.Bounds mu nu maxCost ∧
          coefficients i ≤ expr.coefficientValue coefficients lambda ∧
          expr.eval values y budget ≤ values i y budget)
    (hinitial : ∀ i y budget, 0 ≤ y → y ≤ nu → maxCost ≤ budget →
      delta * coefficients i * lambda ^ y ≤ values i y budget) :
    ∀ steps : ℕ, ∀ i y, 0 ≤ y →
      y ≤ nu + (steps : ℝ) * mu →
      delta * coefficients i * lambda ^ y ≤
        values i y (maxCost * (steps + 1)) := by
  intro steps
  induction steps with
  | zero =>
      intro i y hy hyUpper
      simpa using hinitial i y maxCost hy (by simpa using hyUpper) le_rfl
  | succ steps ih =>
      intro i y hy hyUpper
      by_cases hprevious : y ≤ nu + (steps : ℝ) * mu
      · have hprev := ih i y hy hprevious
        have hbudget :
            maxCost * (steps + 1) ≤ maxCost * (Nat.succ steps + 1) := by
          exact Nat.mul_le_mul_left maxCost (by omega)
        exact hprev.trans (hbudgetMono i y hbudget)
      have htime : nu ≤ y := by
        have hnonneg : 0 ≤ (steps : ℝ) * mu :=
          mul_nonneg (Nat.cast_nonneg steps) hmu.le
        linarith
      have hcurrentBudget : maxCost ≤ maxCost * (Nat.succ steps + 1) := by
        rw [show Nat.succ steps + 1 = (steps + 1) + 1 by omega,
          Nat.mul_add, Nat.mul_one]
        omega
      obtain ⟨expr, hbounds, hcoefficients, hsystem⟩ :=
        hchoice i y (maxCost * (Nat.succ steps + 1)) htime hcurrentBudget
      have hscale : 0 ≤ delta * lambda ^ y :=
        mul_nonneg hdelta
          (Real.rpow_nonneg (zero_le_one.trans hlambda.le) y)
      calc
        delta * coefficients i * lambda ^ y =
            (delta * lambda ^ y) * coefficients i := by ring
        _ ≤ (delta * lambda ^ y) *
            expr.coefficientValue coefficients lambda :=
          mul_le_mul_of_nonneg_left hcoefficients hscale
        _ = expr.eval
            (fun j t _ => delta * coefficients j * lambda ^ t) y
              (maxCost * (Nat.succ steps + 1)) :=
          (expr.eval_exponential coefficients hdelta
            (zero_lt_one.trans hlambda)).symm
        _ ≤ expr.eval values y (maxCost * (Nat.succ steps + 1)) := by
          apply expr.eval_mono_of_bounds hbounds
          intro j shift cost hshiftLower hshiftUpper hcost
          have hyLower : 0 ≤ y + shift := by linarith
          have hyUpperLeaf :
              y + shift ≤ nu + (steps : ℝ) * mu := by
            norm_num only [Nat.cast_succ] at hyUpper
            linarith
          have hprev := ih j (y + shift) hyLower hyUpperLeaf
          have hbudget :
              maxCost * (steps + 1) ≤
                maxCost * (Nat.succ steps + 1) - cost := by
            apply Nat.le_sub_of_add_le
            rw [show Nat.succ steps + 1 = (steps + 1) + 1 by omega,
              Nat.mul_add, Nat.mul_one]
            exact Nat.add_le_add_left hcost _
          exact hprev.trans (hbudgetMono j (y + shift) hbudget)
        _ ≤ values i y (maxCost * (Nat.succ steps + 1)) := hsystem

/-- Every nonnegative time admits the same exponential lower bound with a
natural depth budget linear in its retarded interval index. -/
theorem choice_exists_linear_budget_exponential_lower_bound
    {index : Type*}
    (values : index → ℝ → ℕ → ℝ)
    (coefficients : index → ℝ)
    {delta lambda mu nu : ℝ} {maxCost : ℕ}
    (hdelta : 0 ≤ delta) (hlambda : 1 < lambda)
    (hmu : 0 < mu)
    (hbudgetMono : ∀ i y, Monotone (values i y))
    (hchoice : ∀ i y budget, nu ≤ y → maxCost ≤ budget →
      ∃ expr : Expr index,
        expr.Bounds mu nu maxCost ∧
          coefficients i ≤ expr.coefficientValue coefficients lambda ∧
          expr.eval values y budget ≤ values i y budget)
    (hinitial : ∀ i y budget, 0 ≤ y → y ≤ nu → maxCost ≤ budget →
      delta * coefficients i * lambda ^ y ≤ values i y budget) :
    ∀ i y, 0 ≤ y →
      ∃ steps : ℕ,
        y ≤ nu + (steps : ℝ) * mu ∧
        delta * coefficients i * lambda ^ y ≤
          values i y (maxCost * (steps + 1)) := by
  intro i y hy
  obtain ⟨steps : ℕ, hsteps⟩ := exists_nat_gt ((y - nu) / mu)
  have hupper : y ≤ nu + (steps : ℝ) * mu := by
    have hmul : y - nu < (steps : ℝ) * mu := by
      apply (div_lt_iff₀ hmu).mp
      exact hsteps
    linarith
  exact ⟨steps, hupper,
    choice_exponential_lower_bound_on_intervals values coefficients
      hdelta hlambda hmu hbudgetMono hchoice hinitial
      steps i y hy hupper⟩

#print axioms DepthBudgetRetarded.Expr.choice_exponential_lower_bound_on_intervals
#print axioms DepthBudgetRetarded.Expr.choice_exists_linear_budget_exponential_lower_bound

end Expr
end DepthBudgetRetarded

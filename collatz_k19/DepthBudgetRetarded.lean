import Mathlib

/-!
# Depth-budgeted retarded propagation

This module is the abstract engine needed to retain a linear orbit-depth
budget while propagating a Krasikov--Lagarias exponential lower bound.
Each retarded leaf carries both a real shift and a natural depth cost.
-/

namespace DepthBudgetRetarded

inductive Expr (index : Type*) where
  | leaf (i : index) (shift : ℝ) (cost : ℕ)
  | add (left right : Expr index)
  | min (left right : Expr index)

namespace Expr

def eval {index : Type*} (expr : Expr index)
    (values : index → ℝ → ℕ → ℝ) (y : ℝ) (budget : ℕ) : ℝ :=
  match expr with
  | .leaf i shift cost => values i (y + shift) (budget - cost)
  | .add left right => left.eval values y budget + right.eval values y budget
  | .min left right =>
      Min.min (left.eval values y budget) (right.eval values y budget)

noncomputable def coefficientValue {index : Type*} (expr : Expr index)
    (coefficients : index → ℝ) (lambda : ℝ) : ℝ :=
  match expr with
  | .leaf i shift _ => coefficients i * lambda ^ shift
  | .add left right =>
      left.coefficientValue coefficients lambda +
        right.coefficientValue coefficients lambda
  | .min left right =>
      Min.min (left.coefficientValue coefficients lambda)
        (right.coefficientValue coefficients lambda)

/-- Every leaf shift lies in `[-nu,-mu]` and every leaf depth cost is at most
`maxCost`. -/
def Bounds {index : Type*} (expr : Expr index)
    (mu nu : ℝ) (maxCost : ℕ) : Prop :=
  match expr with
  | .leaf _ shift cost => -nu ≤ shift ∧ shift ≤ -mu ∧ cost ≤ maxCost
  | .add left right => left.Bounds mu nu maxCost ∧ right.Bounds mu nu maxCost
  | .min left right => left.Bounds mu nu maxCost ∧ right.Bounds mu nu maxCost

/-- Monotonicity of expression evaluation from leafwise inequalities. -/
theorem eval_mono_of_bounds {index : Type*} (expr : Expr index)
    {mu nu y : ℝ} {maxCost budget : ℕ}
    {lower upper : index → ℝ → ℕ → ℝ}
    (hbounds : expr.Bounds mu nu maxCost)
    (hleaf : ∀ i shift cost,
      -nu ≤ shift → shift ≤ -mu → cost ≤ maxCost →
      lower i (y + shift) (budget - cost) ≤
        upper i (y + shift) (budget - cost)) :
    expr.eval lower y budget ≤ expr.eval upper y budget := by
  induction expr with
  | leaf i shift cost =>
      simpa [eval] using
        hleaf i shift cost hbounds.1 hbounds.2.1 hbounds.2.2
  | add left right ihLeft ihRight =>
      simpa [eval] using add_le_add (ihLeft hbounds.1) (ihRight hbounds.2)
  | min left right ihLeft ihRight =>
      simpa [eval] using min_le_min (ihLeft hbounds.1) (ihRight hbounds.2)

/-- Depth costs do not alter the exponential coefficient identity. -/
theorem eval_exponential {index : Type*} (expr : Expr index)
    (coefficients : index → ℝ) {delta lambda y : ℝ} {budget : ℕ}
    (hdelta : 0 ≤ delta) (hlambda : 0 < lambda) :
    expr.eval (fun i t _ => delta * coefficients i * lambda ^ t) y budget =
      (delta * lambda ^ y) * expr.coefficientValue coefficients lambda := by
  induction expr with
  | leaf i shift cost =>
      simp only [eval, coefficientValue, Real.rpow_add hlambda]
      ring
  | add left right ihLeft ihRight =>
      simp only [eval, coefficientValue, ihLeft, ihRight]
      ring
  | min left right ihLeft ihRight =>
      simp only [eval, coefficientValue, ihLeft, ihRight]
      exact (mul_min_of_nonneg _ _
        (mul_nonneg hdelta (Real.rpow_nonneg hlambda.le y))).symm

private theorem budget_mono (maxCost steps : ℕ) :
    maxCost * (steps + 1) ≤ maxCost * (Nat.succ steps + 1) := by
  exact Nat.mul_le_mul_left maxCost (by omega)

private theorem previous_budget_le_sub
    {maxCost steps cost : ℕ} (hcost : cost ≤ maxCost) :
    maxCost * (steps + 1) ≤ maxCost * (Nat.succ steps + 1) - cost := by
  apply Nat.le_sub_of_add_le
  rw [show Nat.succ steps + 1 = (steps + 1) + 1 by omega,
    Nat.mul_add, Nat.mul_one]
  exact Nat.add_le_add_left hcost _

private theorem maxCost_le_current_budget (maxCost steps : ℕ) :
    maxCost ≤ maxCost * (Nat.succ steps + 1) := by
  rw [show Nat.succ steps + 1 = (steps + 1) + 1 by omega,
    Nat.mul_add, Nat.mul_one]
  omega

/--
Retarded interval induction with a linear natural depth budget.

At interval number `steps`, the available budget is
`maxCost * (steps + 1)`. One retarded macro-step consumes at most `maxCost`,
so every leaf can invoke the previous interval with its remaining budget.
-/
theorem exponential_lower_bound_on_intervals {index : Type*}
    (rhs : index → Expr index) (values : index → ℝ → ℕ → ℝ)
    (coefficients : index → ℝ)
    {delta lambda mu nu : ℝ} {maxCost : ℕ}
    (hdelta : 0 ≤ delta) (hlambda : 1 < lambda)
    (hmu : 0 < mu)
    (hbudgetMono : ∀ i y, Monotone (values i y))
    (hbounds : ∀ i, (rhs i).Bounds mu nu maxCost)
    (hcoefficients : ∀ i,
      coefficients i ≤ (rhs i).coefficientValue coefficients lambda)
    (hsystem : ∀ i y budget, nu ≤ y → maxCost ≤ budget →
      (rhs i).eval values y budget ≤ values i y budget)
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
        exact hprev.trans (hbudgetMono i y (budget_mono maxCost steps))
      have htime : nu ≤ y := by
        have hnonneg : 0 ≤ (steps : ℝ) * mu :=
          mul_nonneg (Nat.cast_nonneg steps) hmu.le
        linarith
      have hscale : 0 ≤ delta * lambda ^ y :=
        mul_nonneg hdelta
          (Real.rpow_nonneg (zero_le_one.trans hlambda.le) y)
      calc
        delta * coefficients i * lambda ^ y =
            (delta * lambda ^ y) * coefficients i := by ring
        _ ≤ (delta * lambda ^ y) *
            (rhs i).coefficientValue coefficients lambda :=
          mul_le_mul_of_nonneg_left (hcoefficients i) hscale
        _ = (rhs i).eval
            (fun j t _ => delta * coefficients j * lambda ^ t) y
              (maxCost * (Nat.succ steps + 1)) :=
          ((rhs i).eval_exponential coefficients hdelta
            (zero_lt_one.trans hlambda)).symm
        _ ≤ (rhs i).eval values y
              (maxCost * (Nat.succ steps + 1)) := by
          apply (rhs i).eval_mono_of_bounds (hbounds i)
          intro j shift cost hshiftLower hshiftUpper hcost
          have hyLower : 0 ≤ y + shift := by linarith
          have hyUpperLeaf :
              y + shift ≤ nu + (steps : ℝ) * mu := by
            norm_num only [Nat.cast_succ] at hyUpper
            linarith
          have hprev := ih j (y + shift) hyLower hyUpperLeaf
          exact hprev.trans
            (hbudgetMono j (y + shift) (previous_budget_le_sub hcost))
        _ ≤ values i y (maxCost * (Nat.succ steps + 1)) :=
          hsystem i y _ htime (maxCost_le_current_budget maxCost steps)

/-- Every nonnegative time has an exponential lower bound with some depth
budget linear in the number of retarded intervals. -/
theorem exists_linear_budget_exponential_lower_bound {index : Type*}
    (rhs : index → Expr index) (values : index → ℝ → ℕ → ℝ)
    (coefficients : index → ℝ)
    {delta lambda mu nu : ℝ} {maxCost : ℕ}
    (hdelta : 0 ≤ delta) (hlambda : 1 < lambda)
    (hmu : 0 < mu)
    (hbudgetMono : ∀ i y, Monotone (values i y))
    (hbounds : ∀ i, (rhs i).Bounds mu nu maxCost)
    (hcoefficients : ∀ i,
      coefficients i ≤ (rhs i).coefficientValue coefficients lambda)
    (hsystem : ∀ i y budget, nu ≤ y → maxCost ≤ budget →
      (rhs i).eval values y budget ≤ values i y budget)
    (hinitial : ∀ i y budget, 0 ≤ y → y ≤ nu → maxCost ≤ budget →
      delta * coefficients i * lambda ^ y ≤ values i y budget) :
    ∀ i y, 0 ≤ y →
      ∃ steps : ℕ,
        y ≤ nu + (steps : ℝ) * mu ∧
        delta * coefficients i * lambda ^ y ≤
          values i y (maxCost * (steps + 1)) := by
  intro i y hy
  obtain ⟨steps : ℕ, hsteps⟩ := exists_nat_gt ((y - nu) / mu)
  refine ⟨steps, ?_, ?_⟩
  · have hmul : y - nu < (steps : ℝ) * mu := by
      apply (div_lt_iff₀ hmu).mp
      exact hsteps
    linarith
  · exact exponential_lower_bound_on_intervals rhs values coefficients
      hdelta hlambda hmu hbudgetMono hbounds hcoefficients hsystem hinitial
      steps i y hy (by
        have hmul : y - nu < (steps : ℝ) * mu := by
          apply (div_lt_iff₀ hmu).mp
          exact hsteps
        linarith)

#print axioms DepthBudgetRetarded.Expr.exponential_lower_bound_on_intervals
#print axioms DepthBudgetRetarded.Expr.exists_linear_budget_exponential_lower_bound

end Expr
end DepthBudgetRetarded

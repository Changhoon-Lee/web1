import DepthBudgetRetarded
import Mathlib.Analysis.MeanInequalitiesPow

/-!
# Fractional-power transport with an unchanged natural depth budget

The depth-budgeted retarded expression has the same addition/minimum
coefficient algebra as the ordinary retarded expression; each leaf merely
carries an extra natural cost.  Consequently concave fractional-power transport
preserves every coefficient inequality while leaving all leaf costs and Bounds
certificates unchanged.

This is the abstract depth half needed by the fractional K19 first-hit fibre
program: the exponent and coefficient dynamic range may be changed without
paying any additional accelerated-step budget.
-/

namespace DepthBudgetFractionalPower

open DepthBudgetRetarded

noncomputable def poweredCoefficients {index : Type*}
    (coefficients : index → ℝ) (p : ℝ) : index → ℝ :=
  fun index => coefficients index ^ p

private theorem coefficientValue_nonneg {index : Type*}
    (expr : Expr index) (coefficients : index → ℝ)
    {lambda : ℝ} (hcoefficients : ∀ index, 0 ≤ coefficients index)
    (hlambda : 0 < lambda) :
    0 ≤ expr.coefficientValue coefficients lambda := by
  induction expr with
  | leaf index shift cost =>
      simp only [Expr.coefficientValue]
      exact mul_nonneg (hcoefficients index)
        (Real.rpow_nonneg hlambda.le shift)
  | add left right ihLeft ihRight =>
      simp only [Expr.coefficientValue]
      exact add_nonneg ihLeft ihRight
  | min left right ihLeft ihRight =>
      simp only [Expr.coefficientValue]
      exact le_min ihLeft ihRight

/-- Fractional powers preserve the coefficient inequality of a depth-budgeted
expression and do not alter its natural leaf costs. -/
theorem coefficientValue_rpow_le {index : Type*}
    (expr : Expr index) (coefficients : index → ℝ)
    {lambda p : ℝ}
    (hcoefficients : ∀ index, 0 ≤ coefficients index)
    (hlambda : 0 < lambda) (hp : 0 ≤ p) (hpOne : p ≤ 1) :
    (expr.coefficientValue coefficients lambda) ^ p ≤
      expr.coefficientValue (poweredCoefficients coefficients p)
        (lambda ^ p) := by
  induction expr with
  | leaf index shift cost =>
      simp only [Expr.coefficientValue, poweredCoefficients]
      have hmul :
          (coefficients index * lambda ^ shift) ^ p =
            coefficients index ^ p * (lambda ^ shift) ^ p :=
        Real.mul_rpow (hcoefficients index)
          (Real.rpow_nonneg hlambda.le shift)
      have hshift :
          (lambda ^ shift) ^ p = lambda ^ (shift * p) :=
        (Real.rpow_mul hlambda.le shift p).symm
      have hpShift :
          (lambda ^ p) ^ shift = lambda ^ (p * shift) :=
        (Real.rpow_mul hlambda.le p shift).symm
      have hleafEq :
          (coefficients index * lambda ^ shift) ^ p =
            coefficients index ^ p * (lambda ^ p) ^ shift := by
        calc
          (coefficients index * lambda ^ shift) ^ p =
              coefficients index ^ p * (lambda ^ shift) ^ p := hmul
          _ = coefficients index ^ p * lambda ^ (shift * p) := by rw [hshift]
          _ = coefficients index ^ p * lambda ^ (p * shift) := by
            congr 1
            ring
          _ = coefficients index ^ p * (lambda ^ p) ^ shift := by
            rw [hpShift]
      exact hleafEq.le
  | add left right ihLeft ihRight =>
      simp only [Expr.coefficientValue]
      have hleft := coefficientValue_nonneg left coefficients
        hcoefficients hlambda
      have hright := coefficientValue_nonneg right coefficients
        hcoefficients hlambda
      calc
        (left.coefficientValue coefficients lambda +
            right.coefficientValue coefficients lambda) ^ p ≤
          (left.coefficientValue coefficients lambda) ^ p +
            (right.coefficientValue coefficients lambda) ^ p :=
          Real.rpow_add_le_add_rpow hleft hright hp hpOne
        _ ≤ left.coefficientValue (poweredCoefficients coefficients p)
              (lambda ^ p) +
            right.coefficientValue (poweredCoefficients coefficients p)
              (lambda ^ p) := add_le_add ihLeft ihRight
  | min left right ihLeft ihRight =>
      simp only [Expr.coefficientValue]
      have hleft := coefficientValue_nonneg left coefficients
        hcoefficients hlambda
      have hright := coefficientValue_nonneg right coefficients
        hcoefficients hlambda
      rcases le_total
          (left.coefficientValue coefficients lambda)
          (right.coefficientValue coefficients lambda) with hle | hle
      · rw [min_eq_left hle]
        apply le_min ihLeft
        exact (Real.rpow_le_rpow hleft hle hp).trans ihRight
      · rw [min_eq_right hle]
        apply le_min
        · exact (Real.rpow_le_rpow hright hle hp).trans ihLeft
        · exact ihRight

/-- A choice-valued depth system keeps exactly the same expression and Bounds
certificate after fractional-power transport. -/
theorem choice_poweredCoefficients {index : Type*}
    (coefficients : index → ℝ) {lambda p mu nu : ℝ} {maxCost : ℕ}
    (hcoefficients : ∀ index, 0 ≤ coefficients index)
    (hlambda : 0 < lambda) (hp : 0 ≤ p) (hpOne : p ≤ 1)
    (choice : ∀ i y budget, nu ≤ y → maxCost ≤ budget →
      ∃ expr : Expr index,
        expr.Bounds mu nu maxCost ∧
          coefficients i ≤ expr.coefficientValue coefficients lambda ∧
          True) :
    ∀ i y budget, nu ≤ y → maxCost ≤ budget →
      ∃ expr : Expr index,
        expr.Bounds mu nu maxCost ∧
          poweredCoefficients coefficients p i ≤
            expr.coefficientValue (poweredCoefficients coefficients p)
              (lambda ^ p) ∧
          True := by
  intro i y budget hy hbudget
  obtain ⟨expr, hbounds, hcoefficient, htail⟩ :=
    choice i y budget hy hbudget
  refine ⟨expr, hbounds, ?_, htail⟩
  calc
    poweredCoefficients coefficients p i = coefficients i ^ p := rfl
    _ ≤ (expr.coefficientValue coefficients lambda) ^ p :=
      Real.rpow_le_rpow (hcoefficients i) hcoefficient hp
    _ ≤ expr.coefficientValue (poweredCoefficients coefficients p)
          (lambda ^ p) :=
      coefficientValue_rpow_le expr coefficients
        hcoefficients hlambda hp hpOne

#print axioms DepthBudgetFractionalPower.coefficientValue_rpow_le
#print axioms DepthBudgetFractionalPower.choice_poweredCoefficients

end DepthBudgetFractionalPower

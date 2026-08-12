import Erdos1135.KrasikovLagarias.EliminationTrace
import Mathlib.Analysis.MeanInequalitiesPow

/-!
# Concave fractional-power transport of retarded LP feasibility

If a nonnegative coefficient vector is feasible for a retarded addition/minimum
system at base `lambda`, then its pointwise `p`-th real power is feasible at
base `lambda^p` for every `0 ≤ p ≤ 1`.

The proof is structural:

* leaves use multiplicativity of real powers;
* additions use concavity `(a+b)^p ≤ a^p+b^p`;
* minima use monotonicity of `x ↦ x^p`.

Applied to the authenticated K19 vector with `p=1/5`, this produces a new K19
certificate at exponent `14551/80000` whose coefficient dynamic range is only
the fifth root of the original range.
-/

namespace Erdos1135
namespace KrasikovLagarias
namespace FractionalPowerFeasibility

open Retarded

noncomputable def poweredCoefficients {index : Type*}
    (coefficients : index → Real) (p : Real) : index → Real :=
  fun index => coefficients index ^ p

private theorem coefficientValue_nonneg {index : Type*}
    (expr : Expr index) (coefficients : index → Real)
    {lambda : Real} (hcoefficients : ∀ index, 0 ≤ coefficients index)
    (hlambda : 0 < lambda) :
    0 ≤ expr.coefficientValue coefficients lambda := by
  induction expr with
  | leaf index shift =>
      simp only [Expr.coefficientValue]
      exact mul_nonneg (hcoefficients index)
        (Real.rpow_nonneg hlambda.le shift)
  | add left right ihLeft ihRight =>
      simp only [Expr.coefficientValue]
      exact add_nonneg ihLeft ihRight
  | min left right ihLeft ihRight =>
      simp only [Expr.coefficientValue]
      exact le_min ihLeft ihRight

/-- Concavity transports the coefficient value of every retarded expression. -/
theorem coefficientValue_rpow_le {index : Type*}
    (expr : Expr index) (coefficients : index → Real)
    {lambda p : Real}
    (hcoefficients : ∀ index, 0 ≤ coefficients index)
    (hlambda : 0 < lambda) (hp : 0 ≤ p) (hpOne : p ≤ 1) :
    (expr.coefficientValue coefficients lambda) ^ p ≤
      expr.coefficientValue (poweredCoefficients coefficients p)
        (lambda ^ p) := by
  induction expr with
  | leaf index shift =>
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

/-- Any feasible nonnegative coefficient vector remains feasible after a
concave fractional-power transform. -/
theorem feasible_poweredCoefficients {index : Type*}
    (system : DifferenceSystem index) (coefficients : index → Real)
    {lambda p : Real}
    (hfeasible : system.IsFeasible coefficients lambda)
    (hcoefficients : ∀ index, 0 ≤ coefficients index)
    (hlambda : 0 < lambda) (hp : 0 ≤ p) (hpOne : p ≤ 1) :
    system.IsFeasible (poweredCoefficients coefficients p) (lambda ^ p) := by
  intro index
  calc
    poweredCoefficients coefficients p index = coefficients index ^ p := rfl
    _ ≤ ((system index).coefficientValue coefficients lambda) ^ p :=
      Real.rpow_le_rpow (hcoefficients index) (hfeasible index) hp
    _ ≤ (system index).coefficientValue
          (poweredCoefficients coefficients p) (lambda ^ p) :=
      coefficientValue_rpow_le (system index) coefficients
        hcoefficients hlambda hp hpOne

#print axioms Erdos1135.KrasikovLagarias.FractionalPowerFeasibility.coefficientValue_rpow_le
#print axioms Erdos1135.KrasikovLagarias.FractionalPowerFeasibility.feasible_poweredCoefficients

end FractionalPowerFeasibility
end KrasikovLagarias
end Erdos1135

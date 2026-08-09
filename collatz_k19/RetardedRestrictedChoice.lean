import Erdos1135.KrasikovLagarias.RetardedChoice

/-!
# Choice-valued retarded induction on a closed index subset

The standard retarded theorem propagates all indices simultaneously and hence
uses a global coefficient upper bound.  For a predicate `P` closed under every
chosen expression, the same interval induction propagates only indices in `P`.
Its initial interval therefore needs a coefficient upper bound only on `P`.
This is the formal interface required for root-local K19 coefficient
normalization.
-/

namespace Erdos1135
namespace KrasikovLagarias
namespace Retarded
namespace Expr

/-- Every leaf index of an expression satisfies `P`. -/
def UsesOnly {index : Type*} (P : index → Prop) : Expr index → Prop
  | .leaf i _ => P i
  | .add left right => left.UsesOnly P ∧ right.UsesOnly P
  | .min left right => left.UsesOnly P ∧ right.UsesOnly P

/-- Monotonicity restricted to the leaf indices actually used by an
expression. -/
theorem eval_mono_of_shiftBounds_of_usesOnly {index : Type*}
    (expr : Expr index) (P : index → Prop)
    {mu nu y : Real} {lower upper : index → Real → Real}
    (hbounds : expr.ShiftBounds mu nu)
    (huses : expr.UsesOnly P)
    (hleaf : ∀ i shift, P i → -nu ≤ shift → shift ≤ -mu →
      lower i (y + shift) ≤ upper i (y + shift)) :
    expr.eval lower y ≤ expr.eval upper y := by
  induction expr with
  | leaf i shift =>
      exact hleaf i shift huses hbounds.1 hbounds.2
  | add left right ihLeft ihRight =>
      exact add_le_add
        (ihLeft hbounds.1 huses.1)
        (ihRight hbounds.2 huses.2)
  | min left right ihLeft ihRight =>
      exact min_le_min
        (ihLeft hbounds.1 huses.1)
        (ihRight hbounds.2 huses.2)

/-- Restricted interval induction on a predicate closed under the chosen
retarded expressions. -/
theorem choice_exponential_lower_bound_on_intervals_restricted
    {index : Type*} (P : index → Prop)
    (values : index → Real → Real)
    (coefficients : index → Real) {delta lambda mu nu : Real}
    (hdelta : 0 ≤ delta) (hlambda : 1 < lambda)
    (hmu : 0 < mu)
    (hchoice : ∀ i, P i → ∀ y, nu ≤ y →
      ∃ expr : Expr index,
        expr.UsesOnly P ∧
        expr.ShiftBounds mu nu ∧
        coefficients i ≤ expr.coefficientValue coefficients lambda ∧
        expr.eval values y ≤ values i y)
    (hinitial : ∀ i, P i → ∀ y, 0 ≤ y → y ≤ nu →
      delta * coefficients i * lambda ^ y ≤ values i y) :
    ∀ steps : Nat, ∀ i, P i → ∀ y, 0 ≤ y →
      y ≤ nu + steps * mu →
      delta * coefficients i * lambda ^ y ≤ values i y := by
  intro steps
  induction steps with
  | zero =>
      intro i hi y hy hyUpper
      apply hinitial i hi y hy
      simpa using hyUpper
  | succ steps ih =>
      intro i hi y hy hyUpper
      by_cases hprevious : y ≤ nu + steps * mu
      · exact ih i hi y hy hprevious
      have htime : nu ≤ y := by
        have hnonneg : 0 ≤ (steps : Real) * mu :=
          mul_nonneg (Nat.cast_nonneg steps) hmu.le
        linarith
      obtain ⟨expr, huses, hshifts, hcoefficients, hsystem⟩ :=
        hchoice i hi y htime
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
            (fun j t => delta * coefficients j * lambda ^ t) y :=
          (expr.eval_exponential coefficients hdelta
            (zero_lt_one.trans hlambda)).symm
        _ ≤ expr.eval values y := by
          apply expr.eval_mono_of_shiftBounds_of_usesOnly P hshifts huses
          intro j shift hj hshiftLower hshiftUpper
          apply ih j hj (y + shift)
          · have hstepsNonneg : 0 ≤ (steps : Real) * mu :=
              mul_nonneg (Nat.cast_nonneg steps) hmu.le
            linarith
          · push_cast at hyUpper ⊢
            linarith
        _ ≤ values i y := hsystem

/-- Restricted choice-valued retarded lower bound for all nonnegative times. -/
theorem choice_exponential_lower_bound_restricted
    {index : Type*} (P : index → Prop)
    (values : index → Real → Real)
    (coefficients : index → Real) {delta lambda mu nu : Real}
    (hdelta : 0 ≤ delta) (hlambda : 1 < lambda)
    (hmu : 0 < mu)
    (hchoice : ∀ i, P i → ∀ y, nu ≤ y →
      ∃ expr : Expr index,
        expr.UsesOnly P ∧
        expr.ShiftBounds mu nu ∧
        coefficients i ≤ expr.coefficientValue coefficients lambda ∧
        expr.eval values y ≤ values i y)
    (hinitial : ∀ i, P i → ∀ y, 0 ≤ y → y ≤ nu →
      delta * coefficients i * lambda ^ y ≤ values i y) :
    ∀ i, P i → ∀ y, 0 ≤ y →
      delta * coefficients i * lambda ^ y ≤ values i y := by
  intro i hi y hy
  obtain ⟨steps : Nat, hsteps⟩ := exists_nat_gt ((y - nu) / mu)
  apply choice_exponential_lower_bound_on_intervals_restricted P
    values coefficients hdelta hlambda hmu hchoice hinitial
    steps i hi y hy
  have hmul : y - nu < (steps : Real) * mu := by
    apply (div_lt_iff₀ hmu).mp
    exact hsteps
  linarith

/-- Uniform-bound form whose coefficient upper bound is required only on the
closed predicate `P`. -/
theorem choice_exponential_lower_bound_of_restricted_bounds
    {index : Type*} (P : index → Prop)
    (values : index → Real → Real)
    (coefficients : index → Real)
    {base coefficientMax lambda mu nu : Real}
    (hbase : 0 ≤ base) (hcoefficientMax : 0 < coefficientMax)
    (hlambda : 1 < lambda) (hmu : 0 < mu)
    (hmono : ∀ i, P i → Monotone (values i))
    (hvalueZero : ∀ i, P i → base ≤ values i 0)
    (hcoefficientUpper : ∀ i, P i → coefficients i ≤ coefficientMax)
    (hchoice : ∀ i, P i → ∀ y, nu ≤ y →
      ∃ expr : Expr index,
        expr.UsesOnly P ∧
        expr.ShiftBounds mu nu ∧
        coefficients i ≤ expr.coefficientValue coefficients lambda ∧
        expr.eval values y ≤ values i y) :
    ∀ i, P i → ∀ y, 0 ≤ y →
      (lambda ^ (-nu) * base / coefficientMax) *
          coefficients i * lambda ^ y ≤ values i y := by
  apply choice_exponential_lower_bound_restricted P values coefficients
    (delta := lambda ^ (-nu) * base / coefficientMax)
    (by positivity) hlambda hmu hchoice
  intro i hi y hy hyUpper
  have hlambdaPos : 0 < lambda := zero_lt_one.trans hlambda
  have hdelta : 0 ≤ lambda ^ (-nu) * base / coefficientMax := by positivity
  calc
    (lambda ^ (-nu) * base / coefficientMax) * coefficients i * lambda ^ y
        = ((lambda ^ (-nu) * base / coefficientMax) * lambda ^ y) *
            coefficients i := by ring
    _ ≤ ((lambda ^ (-nu) * base / coefficientMax) * lambda ^ y) *
            coefficientMax := by
      apply mul_le_mul_of_nonneg_left (hcoefficientUpper i hi)
      exact mul_nonneg hdelta (Real.rpow_nonneg hlambdaPos.le y)
    _ = lambda ^ (-nu) * base * lambda ^ y := by
      field_simp [hcoefficientMax.ne']
    _ = base * lambda ^ (y - nu) := by
      rw [show y - nu = -nu + y by ring, Real.rpow_add hlambdaPos]
      ring
    _ ≤ base := by
      calc
        base * lambda ^ (y - nu) ≤ base * 1 := by
          gcongr
          exact Real.rpow_le_one_of_one_le_of_nonpos hlambda.le
            (sub_nonpos.mpr hyUpper)
        _ = base := by ring
    _ ≤ values i 0 := hvalueZero i hi
    _ ≤ values i y := hmono i hi hy

#print axioms Erdos1135.KrasikovLagarias.Retarded.Expr.choice_exponential_lower_bound_of_restricted_bounds

end Expr
end Retarded
end KrasikovLagarias
end Erdos1135

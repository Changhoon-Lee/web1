import Erdos1135.KrasikovLagarias.AdaptiveCriticalChoice

/-!
# Maximum-normalized adaptive critical envelope

The original generic wrapper uses the sum of all positive certificate
coefficients as a convenient common upper bound.  The interval induction only
requires a common upper bound for each individual coefficient, so the exact
finite maximum is sufficient and is never larger than the sum.

This removes the artificial cardinality-scale loss from the coefficient-level
envelope while preserving the exact same adaptive full trees, feasible source
vector, and choice-valued retarded induction.
-/

namespace Erdos1135
namespace KrasikovLagarias
namespace AdaptiveCriticalChoiceMax

open AdaptiveEliminationPolicy
open AdaptiveEliminationTree
open EliminationCriticalTree
open EliminationPolicy
open EliminationResidue
open EliminationSourceSystem
open Retarded

/-- Exact maximum of a coefficient vector on a finite nonempty principal index
set. -/
noncomputable def coefficientMax {k : Nat} [Nonempty (PrincipalIndex k)]
    (coefficients : PrincipalIndex k → Real) : Real :=
  (Finset.univ : Finset (PrincipalIndex k)).sup'
    Finset.univ_nonempty coefficients

/-- Every coefficient is bounded by the exact finite maximum. -/
theorem coefficient_le_max {k : Nat} [Nonempty (PrincipalIndex k)]
    (coefficients : PrincipalIndex k → Real)
    (index : PrincipalIndex k) :
    coefficients index ≤ coefficientMax coefficients := by
  exact Finset.le_sup' (s := (Finset.univ : Finset (PrincipalIndex k)))
    (f := coefficients) (Finset.mem_univ index)

/-- A positive coefficient vector has a positive exact maximum. -/
theorem coefficientMax_pos {k : Nat} [Nonempty (PrincipalIndex k)]
    (coefficients : PrincipalIndex k → Real)
    (hpositive : ∀ index, 0 < coefficients index) :
    0 < coefficientMax coefficients := by
  let index : PrincipalIndex k := Classical.choice inferInstance
  exact (hpositive index).trans_le (coefficient_le_max coefficients index)

/-- Stronger generic exponential consequence using the exact maximum rather
than the sum of all certificate coefficients. -/
theorem exponential_lower_bound_max {k : Nat} {hk : 2 ≤ k}
    [Nonempty (PrincipalIndex k)]
    (potential : AdaptiveEliminationPolicy.ForcedPotential k hk)
    (values : PrincipalIndex k → Real → Real)
    (coefficients : PrincipalIndex k → Real) {lambda : Real}
    (hone : 1 < lambda)
    (hsourceSolution : DifferenceSystem.IsSolution
      (sourceSystem hk) 2 values)
    (hvaluesPositive : ∀ index time, 0 ≤ time → 0 < values index time)
    (hmono : ∀ index, Monotone (values index))
    (hsourceFeasible : DifferenceSystem.IsFeasible
      (sourceSystem hk) coefficients lambda)
    (hcoefficientsPositive : ∀ index, 0 < coefficients index)
    (hvalueZero : ∀ index, (1 : Real) ≤ values index 0) :
    ∃ constant : Real, 0 < constant ∧
      ∀ index y, 0 ≤ y →
        constant * coefficients index * lambda ^ y ≤ values index y := by
  obtain ⟨mu, nu, hmu, hnu, hbounds⟩ :=
    AdaptiveCriticalChoice.exists_uniform_shiftBounds potential
  let maximum : Real := coefficientMax coefficients
  let constant : Real := lambda ^ (-nu) / maximum
  have hmaximum : 0 < maximum := by
    exact coefficientMax_pos coefficients hcoefficientsPositive
  have hconstant : 0 < constant := by
    dsimp [constant]
    exact div_pos (Real.rpow_pos_of_pos (zero_lt_one.trans hone) _) hmaximum
  refine ⟨constant, hconstant, ?_⟩
  have hgrowth := Expr.choice_exponential_lower_bound_of_uniform_bounds
    values coefficients
    (base := (1 : Real)) (coefficientMax := maximum)
    (lambda := lambda) (mu := mu) (nu := nu)
    (by norm_num) hmaximum hone hmu hmono hvalueZero
    (fun index => coefficient_le_max coefficients index)
    (AdaptiveCriticalChoice.choice_witness potential values coefficients
      (zero_lt_one.trans hone) hsourceSolution hvaluesPositive hmono
      hsourceFeasible hmu hnu hbounds)
  intro index y hy
  simpa [constant, maximum] using hgrowth index y hy

#print axioms Erdos1135.KrasikovLagarias.AdaptiveCriticalChoiceMax.exponential_lower_bound_max

end AdaptiveCriticalChoiceMax
end KrasikovLagarias
end Erdos1135

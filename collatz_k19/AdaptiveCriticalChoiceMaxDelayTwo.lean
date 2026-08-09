import AdaptiveCriticalChoiceMax
import AdaptiveSharpDelayTwo

/-!
# Maximum-normalized adaptive envelope with exact delay two

Combining the exact finite coefficient maximum with the sharp adaptive delay
`nu = 2` gives the generic envelope constant

`lambda ^ (-2) / max_i coefficient i`.

No sum over the principal index set and no unspecified compactness delay remain
in this generic theorem.
-/

namespace Erdos1135
namespace KrasikovLagarias
namespace AdaptiveCriticalChoiceMaxDelayTwo

open AdaptiveEliminationPolicy
open AdaptiveEliminationTree
open AdaptiveCriticalChoiceMax
open AdaptiveSharpDelayTwo
open EliminationCriticalTree
open EliminationPolicy
open EliminationResidue
open EliminationSourceSystem
open Retarded

/-- Sharp generic adaptive envelope: maximum normalization and exact delay two. -/
theorem exponential_lower_bound_max_delay_two
    {k : Nat} {hk : 2 ≤ k} [Nonempty (PrincipalIndex k)]
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
    ∃ constant : Real,
      constant = lambda ^ (-2 : Real) / coefficientMax coefficients ∧
      0 < constant ∧
      ∀ index y, 0 ≤ y →
        constant * coefficients index * lambda ^ y ≤ values index y := by
  obtain ⟨mu, hmu, hbounds⟩ :=
    fullTree_uniform_shiftBounds_two potential
  let maximum : Real := coefficientMax coefficients
  let constant : Real := lambda ^ (-2 : Real) / maximum
  have hmaximum : 0 < maximum := by
    exact coefficientMax_pos coefficients hcoefficientsPositive
  have hconstant : 0 < constant := by
    dsimp [constant]
    exact div_pos (Real.rpow_pos_of_pos (zero_lt_one.trans hone) _) hmaximum
  refine ⟨constant, rfl, hconstant, ?_⟩
  have hgrowth := Expr.choice_exponential_lower_bound_of_uniform_bounds
    values coefficients
    (base := (1 : Real)) (coefficientMax := maximum)
    (lambda := lambda) (mu := mu) (nu := (2 : Real))
    (by norm_num) hmaximum hone hmu hmono hvalueZero
    (fun index => coefficient_le_max coefficients index)
    (AdaptiveCriticalChoice.choice_witness potential values coefficients
      (zero_lt_one.trans hone) hsourceSolution hvaluesPositive hmono
      hsourceFeasible hmu (by norm_num) hbounds)
  intro index y hy
  simpa [constant, maximum] using hgrowth index y hy

#print axioms Erdos1135.KrasikovLagarias.AdaptiveCriticalChoiceMaxDelayTwo.exponential_lower_bound_max_delay_two

end AdaptiveCriticalChoiceMaxDelayTwo
end KrasikovLagarias
end Erdos1135

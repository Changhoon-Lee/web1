import FractionalPowerFeasibility
import Erdos1135.KrasikovLagarias.K19CriticalChoice

/-!
# Fractional-power family of K19 adaptive envelopes

The authenticated K19 coefficient vector is feasible at
`lambda14551 = 2^(14551/16000)`. Concave fractional-power transport produces,
for every `0 < p ≤ 1`, a new feasible vector

`index ↦ k19PrincipalWeights index ^ p`

at base `lambda14551 ^ p`. Feeding that vector back into the same adaptive
critical-tree theorem gives a continuum of K19 predecessor envelopes at
exponent `p * 14551/16000`.

The concrete fourth-root member has exponent `14551/64000` and is the strongest
simple fractional member for which the global coefficient-range bound still
leaves a strictly positive sixteen-side same-potential factor.
-/

namespace Erdos1135
namespace KrasikovLagarias
namespace K19FractionalCriticalChoice

open EliminationResidue
open EliminationSourceSystem
open FractionalPowerFeasibility
open K19CriticalChoice
open K19SourceBridge
open Retarded

local instance principalIndexNonempty : Nonempty (PrincipalIndex 19) :=
  ⟨⟨0, by norm_num [principalCount]⟩⟩

noncomputable def fractionalWeights (p : Real) : PrincipalIndex 19 → Real :=
  poweredCoefficients k19PrincipalWeights p

noncomputable def fractionalLambda (p : Real) : Real :=
  lambda14551 ^ p

noncomputable def fractionalGamma (p : Real) : Real :=
  gamma14551 * p

@[simp]
theorem fractionalLambda_eq_two_rpow (p : Real) :
    fractionalLambda p = (2 : Real) ^ fractionalGamma p := by
  rw [fractionalLambda, lambda14551, fractionalGamma,
    ← Real.rpow_mul (by norm_num)]

/-- Fractional K19 weights remain strictly positive. -/
theorem fractionalWeights_pos (p : Real) (index : PrincipalIndex 19) :
    0 < fractionalWeights p index := by
  exact Real.rpow_pos_of_pos (k19PrincipalWeights_pos index) p

/-- Concavity transports the authenticated K19 source-system certificate. -/
theorem fractionalSourceSystem_isFeasible
    {p : Real} (hp : 0 ≤ p) (hpOne : p ≤ 1) :
    DifferenceSystem.IsFeasible
      (sourceSystem (by norm_num : 2 ≤ 19))
      (fractionalWeights p) (fractionalLambda p) := by
  exact feasible_poweredCoefficients
    (sourceSystem (by norm_num : 2 ≤ 19)) k19PrincipalWeights
    k19SourceSystem_isFeasible
    (fun index => (k19PrincipalWeights_pos index).le)
    lambda14551_pos hp hpOne

/-- Every positive fractional exponent retains an expanding LP base. -/
theorem one_lt_fractionalLambda {p : Real} (hp : 0 < p) :
    1 < fractionalLambda p := by
  exact Real.one_lt_rpow one_lt_lambda14551 hp

/-- Continuum of adaptive K19 envelopes obtained from the same authenticated
finite certificate. -/
theorem phiValues19_fractional_exponential_lower_bound
    {p : Real} (hp : 0 < p) (hpOne : p ≤ 1) :
    ∃ constant : Real, 0 < constant ∧
      ∀ index y, 0 ≤ y →
        constant * fractionalWeights p index *
            fractionalLambda p ^ y ≤ phiValues19 index y := by
  exact AdaptiveCriticalChoice.exponential_lower_bound
    k19AdaptiveForcedPotential phiValues19 (fractionalWeights p)
    (one_lt_fractionalLambda hp) phiValues19_isSourceSolution
    (fun index time htime => phiValues19_pos index htime)
    phiValues19_mono
    (fractionalSourceSystem_isFeasible hp.le hpOne)
    (fractionalWeights_pos p) one_le_phiValues19_zero

noncomputable def fourthWeights : PrincipalIndex 19 → Real :=
  fractionalWeights ((1 : Real) / 4)

noncomputable def fourthLambda : Real :=
  fractionalLambda ((1 : Real) / 4)

noncomputable def fourthGamma : Real :=
  fractionalGamma ((1 : Real) / 4)

@[simp]
theorem fourthGamma_eq :
    fourthGamma = (14551 : Real) / 64000 := by
  norm_num [fourthGamma, fractionalGamma, gamma14551]

@[simp]
theorem fourthLambda_eq_two_rpow :
    fourthLambda = (2 : Real) ^ ((14551 : Real) / 64000) := by
  change fractionalLambda ((1 : Real) / 4) =
    (2 : Real) ^ ((14551 : Real) / 64000)
  rw [fractionalLambda_eq_two_rpow]
  rw [show fractionalGamma ((1 : Real) / 4) =
      (14551 : Real) / 64000 by
    norm_num [fractionalGamma, gamma14551]]

/-- Concrete fourth-root K19 envelope used by the normalization breakthrough. -/
theorem phiValues19_fourth_exponential_lower_bound :
    ∃ constant : Real, 0 < constant ∧
      ∀ index y, 0 ≤ y →
        constant * fourthWeights index * fourthLambda ^ y ≤
          phiValues19 index y := by
  simpa [fourthWeights, fourthLambda] using
    phiValues19_fractional_exponential_lower_bound
      (p := (1 : Real) / 4) (by norm_num) (by norm_num)

#print axioms Erdos1135.KrasikovLagarias.K19FractionalCriticalChoice.fractionalSourceSystem_isFeasible
#print axioms Erdos1135.KrasikovLagarias.K19FractionalCriticalChoice.phiValues19_fractional_exponential_lower_bound
#print axioms Erdos1135.KrasikovLagarias.K19FractionalCriticalChoice.phiValues19_fourth_exponential_lower_bound

end K19FractionalCriticalChoice
end KrasikovLagarias
end Erdos1135

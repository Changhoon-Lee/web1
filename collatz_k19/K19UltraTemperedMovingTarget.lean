import K19UniformMovingTarget

/-!
# Ultra-tempered same-exponent K19 bridge

The K19 predecessor theorem may be weakened from the authenticated natural
coefficient `w` to `w^(1/256)` without changing the exponent
`14551/16000` or the uniform envelope constant.  The smaller temper exponent
substantially compresses the global coefficient range and strengthens the
bad-spine side factor.
-/

namespace Erdos1135
namespace KrasikovLagarias
namespace K19UltraTemperedMovingTarget

open EliminationResidue
open K19CriticalChoice
open K19UniformMovingTarget
open Terras

noncomputable def ultraTemperExponent : Real := (1 : Real) / 256

/-- Every positive K19 coefficient dominates its 256th-root tempering. -/
theorem ultraTemperedWeight_le_weight (index : PrincipalIndex 19) :
    k19PrincipalWeights index ^ ultraTemperExponent ≤
      k19PrincipalWeights index := by
  have h := Real.rpow_le_rpow_of_exponent_le
    (one_le_k19PrincipalWeights index)
    (show ultraTemperExponent ≤ (1 : Real) by
      norm_num [ultraTemperExponent])
  simpa using h

/-- Same K19 exponent and same uniform constant with the 256th-root coefficient. -/
theorem exists_uniform_ultra_tempered_principal_ratio_bound :
    ∃ envelopeConstant : Real, 0 < envelopeConstant ∧
      ∀ (index : PrincipalIndex 19) {sourceTarget target : Nat},
        AdmissibleTarget 19 (residue index) sourceTarget →
        Reaches sourceTarget target →
        ∀ x : Real, (sourceTarget : Real) ≤ x →
          envelopeConstant *
              (k19PrincipalWeights index ^ ultraTemperExponent) *
              (x / (sourceTarget : Real)) ^ gamma14551 ≤
            (predecessorCountReal target x : Real) := by
  obtain ⟨envelopeConstant, henvelopeConstant, huniform⟩ :=
    exists_uniform_principal_ratio_bound
  refine ⟨envelopeConstant, henvelopeConstant, ?_⟩
  intro index sourceTarget target hadmissible hreach x hx
  have hsourcePositive : 0 < (sourceTarget : Real) := by
    exact_mod_cast hadmissible.1
  have hxNonnegative : 0 ≤ x := hsourcePositive.le.trans hx
  have hratioNonnegative : 0 ≤ x / (sourceTarget : Real) :=
    div_nonneg hxNonnegative hsourcePositive.le
  have hpowerNonnegative :
      0 ≤ (x / (sourceTarget : Real)) ^ gamma14551 :=
    Real.rpow_nonneg hratioNonnegative _
  have hcoefficient :
      envelopeConstant *
          (k19PrincipalWeights index ^ ultraTemperExponent) ≤
        envelopeConstant * k19PrincipalWeights index :=
    mul_le_mul_of_nonneg_left (ultraTemperedWeight_le_weight index)
      henvelopeConstant.le
  calc
    envelopeConstant *
          (k19PrincipalWeights index ^ ultraTemperExponent) *
          (x / (sourceTarget : Real)) ^ gamma14551 ≤
        envelopeConstant * k19PrincipalWeights index *
          (x / (sourceTarget : Real)) ^ gamma14551 :=
      mul_le_mul_of_nonneg_right hcoefficient hpowerNonnegative
    _ ≤ (predecessorCountReal target x : Real) :=
      huniform index hadmissible hreach x hx

#print axioms Erdos1135.KrasikovLagarias.K19UltraTemperedMovingTarget.ultraTemperedWeight_le_weight
#print axioms Erdos1135.KrasikovLagarias.K19UltraTemperedMovingTarget.exists_uniform_ultra_tempered_principal_ratio_bound

end K19UltraTemperedMovingTarget
end KrasikovLagarias
end Erdos1135

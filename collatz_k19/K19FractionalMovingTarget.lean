import K19FractionalCriticalChoice
import Erdos1135.KrasikovLagarias.K19PredecessorBridge

/-!
# Uniform moving-target bounds for the fractional K19 family

Every fractional K19 envelope from `K19FractionalCriticalChoice` has one
constant uniform in the principal residue.  The ordinary source/target bridge
therefore gives a source-normalized predecessor bound carrying the fractional
certificate weight itself.

The concrete fourth-root member has

* coefficient `k19PrincipalWeights index ^ (1/4)`, and
* exponent `14551/64000`.

This is the exact same-potential K19 interface needed by the bad-spine
sixteen-side theorem; no `w_min / w_max` normalization is performed inside the
K19 lower bound.
-/

namespace Erdos1135
namespace KrasikovLagarias
namespace K19FractionalMovingTarget

open EliminationResidue
open Filter
open FractionalPowerFeasibility
open K19CriticalChoice
open K19FractionalCriticalChoice
open K19SourceBridge
open Terras

/-- Uniform source-normalized moving-target theorem for every member of the
fractional K19 family. -/
theorem exists_uniform_fractional_principal_ratio_bound
    {p : Real} (hp : 0 < p) (hpOne : p ≤ 1) :
    ∃ envelopeConstant : Real, 0 < envelopeConstant ∧
      ∀ (index : PrincipalIndex 19) {sourceTarget target : Nat},
        AdmissibleTarget 19 (residue index) sourceTarget →
        Reaches sourceTarget target →
        ∀ x : Real, (sourceTarget : Real) ≤ x →
          envelopeConstant * fractionalWeights p index *
              (x / (sourceTarget : Real)) ^ fractionalGamma p ≤
            (predecessorCountReal target x : Real) := by
  obtain ⟨envelopeConstant, henvelopeConstant, henvelope⟩ :=
    phiValues19_fractional_exponential_lower_bound hp hpOne
  refine ⟨envelopeConstant, henvelopeConstant, ?_⟩
  intro index sourceTarget target hadmissible hreach x hx
  have hsourcePositive : 0 < (sourceTarget : Real) := by
    exact_mod_cast hadmissible.1
  have hxPositive : 0 < x := hsourcePositive.trans_le hx
  have hratioPositive : 0 < x / (sourceTarget : Real) :=
    div_pos hxPositive hsourcePositive
  have hratioOne : (1 : Real) ≤ x / (sourceTarget : Real) := by
    exact (le_div_iff₀ hsourcePositive).2 (by simpa using hx)
  let y : Real := Real.logb 2 (x / (sourceTarget : Real))
  have hy : 0 ≤ y := by
    exact Real.logb_nonneg (by norm_num) hratioOne
  have hpow : (2 : Real) ^ y = x / (sourceTarget : Real) := by
    exact Real.rpow_logb (by norm_num) (by norm_num) hratioPositive
  have hcutoff : (2 : Real) ^ y * (sourceTarget : Real) = x := by
    rw [hpow]
    exact div_mul_cancel₀ x hsourcePositive.ne'
  have henvelopeAt := henvelope index y hy
  have hphiTargetNat := phi_le_predecessorCountReal (k := 19)
    (residue := residue index) (target := sourceTarget) y hadmissible
  have hphiTarget : phiValues19 index y ≤
      (predecessorCountReal sourceTarget x : Real) := by
    change (phi 19 (residue index) y : Real) ≤ _
    rw [← hcutoff]
    exact_mod_cast hphiTargetNat
  have htargetTransfer :
      (predecessorCountReal sourceTarget x : Real) ≤
        (predecessorCountReal target x : Real) := by
    exact_mod_cast
      K19PredecessorBridge.predecessorCountReal_le_of_reaches hreach x
  have hlambda : fractionalLambda p ^ y =
      (x / (sourceTarget : Real)) ^ fractionalGamma p := by
    rw [fractionalLambda_eq_two_rpow,
      ← Real.rpow_mul (by norm_num)]
    rw [show fractionalGamma p * y = y * fractionalGamma p by ring,
      Real.rpow_mul (by norm_num), hpow]
  calc
    envelopeConstant * fractionalWeights p index *
          (x / (sourceTarget : Real)) ^ fractionalGamma p =
        envelopeConstant * fractionalWeights p index *
          fractionalLambda p ^ y := by rw [hlambda]
    _ ≤ phiValues19 index y := henvelopeAt
    _ ≤ (predecessorCountReal sourceTarget x : Real) := hphiTarget
    _ ≤ (predecessorCountReal target x : Real) := htargetTransfer

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

/-- Concrete fourth-root moving-target theorem. -/
theorem exists_uniform_fourth_principal_ratio_bound :
    ∃ envelopeConstant : Real, 0 < envelopeConstant ∧
      ∀ (index : PrincipalIndex 19) {sourceTarget target : Nat},
        AdmissibleTarget 19 (residue index) sourceTarget →
        Reaches sourceTarget target →
        ∀ x : Real, (sourceTarget : Real) ≤ x →
          envelopeConstant * fourthWeights index *
              (x / (sourceTarget : Real)) ^
                ((14551 : Real) / 64000) ≤
            (predecessorCountReal target x : Real) := by
  simpa [fourthWeights, fourthGamma_eq] using
    exists_uniform_fractional_principal_ratio_bound
      (p := (1 : Real) / 4) (by norm_num) (by norm_num)

#print axioms Erdos1135.KrasikovLagarias.K19FractionalMovingTarget.exists_uniform_fractional_principal_ratio_bound
#print axioms Erdos1135.KrasikovLagarias.K19FractionalMovingTarget.exists_uniform_fourth_principal_ratio_bound

end K19FractionalMovingTarget
end KrasikovLagarias
end Erdos1135

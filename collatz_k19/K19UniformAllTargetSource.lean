import K19UniformMovingTarget
import Erdos1135.KrasikovLagarias.PeriodicTargetReduction

/-!
# Uniform source-normalized K19 theorem for every eligible target

The target-normalized theorem with threshold `2 * target` is strongest for
nonperiodic targets.  A periodic target may require a larger power-of-two
source, whose size depends on its period.  Nevertheless, the K19 envelope
constant is still uniform: every positive target not divisible by three has a
nonperiodic principal source reaching it, and the same constant applies after
normalization by that source.

This module also records the counterexample transfer needed in a global
Collatz argument: if the downstream target does not reach one, neither can any
source that reaches it.  Consequently every eligible counterexample can be
rooted at a nonperiodic principal source without losing badness.
-/

namespace Erdos1135
namespace KrasikovLagarias
namespace K19UniformAllTargetSource

open EliminationResidue
open K19CriticalChoice
open K19UniformMovingTarget
open Terras

/-- Failure to reach one propagates backwards along reachability. -/
def AvoidsOne (target : Nat) : Prop := ¬ Reaches target 1

theorem avoidsOne_of_reaches
    {source target : Nat} (hreach : Reaches source target)
    (htarget : AvoidsOne target) : AvoidsOne source := by
  intro hsourceOne
  exact htarget (hreach.trans hsourceOne)

/-- One uniform K19 constant works for every eligible target after normalizing
by a nonperiodic principal source reaching that target.  Unlike the stronger
`2 * target` theorem, this statement also covers periodic targets. -/
theorem uniform_all_eligible_target_source_ratio_bound :
    ∃ constant : Real, 0 < constant ∧
      ∀ {target : Nat}, 0 < target → target % 3 ≠ 0 →
        ∃ (index : PrincipalIndex 19) (source : Nat),
          AdmissibleTarget 19 (residue index) source ∧
          Reaches source target ∧
          ∀ x : Real, (source : Real) ≤ x →
            constant * (x / (source : Real)) ^
                ((14551 : Real) / 16000) ≤
              (predecessorCountReal target x : Real) := by
  obtain ⟨constant, hconstant, huniform⟩ :=
    exists_uniform_principal_ratio_bound
  refine ⟨constant, hconstant, ?_⟩
  intro target htarget hmod
  obtain ⟨source, hsourcePos, hsourceMod, hsourceNonperiodic, hreach⟩ :=
    exists_nonperiodic_mod_two_reaches_of_pos_mod_three_ne_zero htarget hmod
  obtain ⟨index, hsourceResidue⟩ :=
    K19PrincipalIndex.exists_modEq_residue source hsourceMod
  have hadmissible : AdmissibleTarget 19 (residue index) source :=
    ⟨hsourcePos, hsourceResidue, hsourceNonperiodic⟩
  refine ⟨index, source, hadmissible, hreach, ?_⟩
  intro x hx
  have hraw := huniform index hadmissible hreach x hx
  have hsourceRealPos : 0 < (source : Real) := by
    exact_mod_cast hsourcePos
  have hxNonnegative : 0 ≤ x := hsourceRealPos.le.trans hx
  have hratioNonnegative : 0 ≤ x / (source : Real) :=
    div_nonneg hxNonnegative hsourceRealPos.le
  have hpowerNonnegative :
      0 ≤ (x / (source : Real)) ^ gamma14551 :=
    Real.rpow_nonneg hratioNonnegative _
  have hdrop :
      constant * (x / (source : Real)) ^ gamma14551 ≤
        constant * k19PrincipalWeights index *
          (x / (source : Real)) ^ gamma14551 := by
    calc
      constant * (x / (source : Real)) ^ gamma14551 =
          (constant * (x / (source : Real)) ^ gamma14551) * 1 := by ring
      _ ≤ (constant * (x / (source : Real)) ^ gamma14551) *
            k19PrincipalWeights index :=
        mul_le_mul_of_nonneg_left
          (one_le_k19PrincipalWeights index)
          (mul_nonneg hconstant.le hpowerNonnegative)
      _ = constant * k19PrincipalWeights index *
            (x / (source : Real)) ^ gamma14551 := by ring
  rw [gamma14551] at hdrop hraw
  exact hdrop.trans hraw

/-- Every eligible counterexample has a nonperiodic principal counterexample
source reaching it.  This removes a separate periodic-component branch from
the later mass argument; the source size is intentionally retained as part of
the state. -/
theorem exists_nonperiodic_principal_counterexample_source
    {target : Nat} (htarget : 0 < target) (hmod : target % 3 ≠ 0)
    (hbad : AvoidsOne target) :
    ∃ (index : PrincipalIndex 19) (source : Nat),
      AdmissibleTarget 19 (residue index) source ∧
      Reaches source target ∧ AvoidsOne source := by
  obtain ⟨source, hsourcePos, hsourceMod, hsourceNonperiodic, hreach⟩ :=
    exists_nonperiodic_mod_two_reaches_of_pos_mod_three_ne_zero htarget hmod
  obtain ⟨index, hsourceResidue⟩ :=
    K19PrincipalIndex.exists_modEq_residue source hsourceMod
  refine ⟨index, source,
    ⟨hsourcePos, hsourceResidue, hsourceNonperiodic⟩,
    hreach, ?_⟩
  exact avoidsOne_of_reaches hreach hbad

#print axioms Erdos1135.KrasikovLagarias.K19UniformAllTargetSource.uniform_all_eligible_target_source_ratio_bound
#print axioms Erdos1135.KrasikovLagarias.K19UniformAllTargetSource.exists_nonperiodic_principal_counterexample_source

end K19UniformAllTargetSource
end KrasikovLagarias
end Erdos1135

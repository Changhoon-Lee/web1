import Erdos1135.KrasikovLagarias.K19PredecessorBridge
import Erdos1135.KrasikovLagarias.K19PrincipalIndex
import Erdos1135.KrasikovLagarias.PeriodicTargetReduction

/-!
# A uniform moving-target consequence of the K19 predecessor certificate

The published K19 endpoint theorem is stated with a target-dependent eventual
constant.  The proof underneath it is stronger: the adaptive envelope supplies
one constant uniform in every principal residue, and the only target scale is
the admissible source itself.  For a nonperiodic eligible target, that source
can be chosen to be either `target` or `2 * target`.
-/

namespace Erdos1135
namespace KrasikovLagarias
namespace K19UniformMovingTarget

open EliminationResidue
open K19CriticalChoice
open K19SourceBridge
open Filter
open Terras

/-- The K19 principal weights are positive natural numbers, hence at least one
when interpreted over the reals. -/
theorem one_le_k19PrincipalWeights (index : PrincipalIndex 19) :
    (1 : Real) ≤ k19PrincipalWeights index := by
  have hreal := k19PrincipalWeights_pos index
  change (0 : Real) <
    (k19Gamma14551EncodedCertificate.weight index.val : Real) at hreal
  have hnat : 0 < k19Gamma14551EncodedCertificate.weight index.val := by
    exact_mod_cast hreal
  have hone : 1 ≤ k19Gamma14551EncodedCertificate.weight index.val := by
    omega
  change (1 : Real) ≤
    (k19Gamma14551EncodedCertificate.weight index.val : Real)
  exact_mod_cast hone

/-- The uniform envelope constant gives a pointwise, source-normalized K19
predecessor bound.  Unlike the publication wrapper, this holds for every
`x ≥ sourceTarget`, not merely eventually, and its leading constant is uniform
in the principal index and both targets. -/
theorem exists_uniform_principal_ratio_bound :
    ∃ envelopeConstant : Real, 0 < envelopeConstant ∧
      ∀ (index : PrincipalIndex 19) {sourceTarget target : Nat},
        AdmissibleTarget 19 (residue index) sourceTarget →
        Reaches sourceTarget target →
        ∀ x : Real, (sourceTarget : Real) ≤ x →
          envelopeConstant * k19PrincipalWeights index *
              (x / (sourceTarget : Real)) ^ gamma14551 ≤
            (predecessorCountReal target x : Real) := by
  obtain ⟨envelopeConstant, henvelopeConstant, henvelope⟩ :=
    phiValues19_exponential_lower_bound
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
  have hlambda : lambda14551 ^ y =
      (x / (sourceTarget : Real)) ^ gamma14551 := by
    rw [lambda14551, ← Real.rpow_mul (by norm_num)]
    rw [show gamma14551 * y = y * gamma14551 by ring,
      Real.rpow_mul (by norm_num), hpow]
  calc
    envelopeConstant * k19PrincipalWeights index *
          (x / (sourceTarget : Real)) ^ gamma14551 =
        envelopeConstant * k19PrincipalWeights index * lambda14551 ^ y := by
          rw [hlambda]
    _ ≤ phiValues19 index y := henvelopeAt
    _ ≤ (predecessorCountReal sourceTarget x : Real) := hphiTarget
    _ ≤ (predecessorCountReal target x : Real) := htargetTransfer

/-- If doubling a target were accelerated-periodic, then applying one
accelerated step would make the original target accelerated-periodic. -/
theorem two_mul_not_inAcceleratedCycle_of_not
    {target : Nat} (hnot : ¬ InAcceleratedCycle target) :
    ¬ InAcceleratedCycle (2 * target) := by
  intro htwo
  apply hnot
  have hstep : accelerated (2 * target) = target := by
    rw [accelerated_eq_div_two_of_even (even_two_mul target)]
    omega
  simpa [Function.iterate_one, hstep] using htwo.iterate 1

/-- Uniform moving-target theorem for every positive nonperiodic eligible
accelerated-Collatz target.  The same positive constant works for every target,
and the natural threshold is only `2 * target`.

This is strictly stronger than a family of unrelated eventual constants:
`target` may now move with the cutoff while the leading constant stays fixed. -/
theorem uniform_nonperiodic_target_ratio_bound :
    ∃ constant : Real, 0 < constant ∧
      ∀ {target : Nat}, 0 < target → target % 3 ≠ 0 →
        ¬ InAcceleratedCycle target →
        ∀ x : Real, 2 * (target : Real) ≤ x →
          constant * (x / (2 * (target : Real))) ^
              ((14551 : Real) / 16000) ≤
            (predecessorCountReal target x : Real) := by
  obtain ⟨constant, hconstant, huniform⟩ :=
    exists_uniform_principal_ratio_bound
  refine ⟨constant, hconstant, ?_⟩
  intro target htarget hmod hnonperiodic x hx
  have hcases : target % 3 = 1 ∨ target % 3 = 2 := by
    have hlt : target % 3 < 3 := Nat.mod_lt target (by norm_num : 0 < 3)
    omega
  rcases hcases with hmodOne | hmodTwo
  · let source : Nat := 2 * target
    have hsourcePositive : 0 < source := by
      dsimp [source]
      exact Nat.mul_pos (by norm_num) htarget
    have hsourceMod : source % 3 = 2 := by
      dsimp [source]
      calc
        (2 * target) % 3 = ((2 % 3) * (target % 3)) % 3 := by
          rw [Nat.mul_mod]
        _ = 2 := by norm_num [hmodOne]
    have hsourceNonperiodic : ¬ InAcceleratedCycle source := by
      dsimp [source]
      exact two_mul_not_inAcceleratedCycle_of_not hnonperiodic
    obtain ⟨index, hsourceResidue⟩ :=
      K19PrincipalIndex.exists_modEq_residue source hsourceMod
    have hadmissible : AdmissibleTarget 19 (residue index) source :=
      ⟨hsourcePositive, hsourceResidue, hsourceNonperiodic⟩
    have hreach : Reaches source target := by
      dsimp [source]
      simpa using pow_two_mul_reaches 1 target
    have hxSource : (source : Real) ≤ x := by
      dsimp [source]
      norm_num only [Nat.cast_mul, Nat.cast_ofNat]
      exact hx
    have hraw := huniform index hadmissible hreach x hxSource
    have hsourceRealPositive : 0 < (source : Real) := by
      exact_mod_cast hsourcePositive
    have hxNonnegative : 0 ≤ x :=
      hsourceRealPositive.le.trans hxSource
    have hratioNonnegative : 0 ≤ x / (source : Real) :=
      div_nonneg hxNonnegative hsourceRealPositive.le
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
          mul_le_mul_of_nonneg_left (one_le_k19PrincipalWeights index)
            (mul_nonneg hconstant.le hpowerNonnegative)
        _ = constant * k19PrincipalWeights index *
              (x / (source : Real)) ^ gamma14551 := by ring
    rw [gamma14551] at hdrop hraw
    simpa [source, Nat.cast_mul, Nat.cast_ofNat] using hdrop.trans hraw
  · obtain ⟨index, hsourceResidue⟩ :=
      K19PrincipalIndex.exists_modEq_residue target hmodTwo
    have hadmissible : AdmissibleTarget 19 (residue index) target :=
      ⟨htarget, hsourceResidue, hnonperiodic⟩
    have htargetRealPositive : 0 < (target : Real) := by
      exact_mod_cast htarget
    have hxTarget : (target : Real) ≤ x := by
      have htwoTargetPositive : 0 < (2 : Real) * (target : Real) := by positivity
      nlinarith
    have hraw := huniform index hadmissible (reaches_refl target) x hxTarget
    have hxNonnegative : 0 ≤ x := by
      have htwoTargetPositive : 0 < (2 : Real) * (target : Real) := by positivity
      nlinarith
    have hhalfNonnegative :
        0 ≤ x / (2 * (target : Real)) := by positivity
    have hratioLe :
        x / (2 * (target : Real)) ≤ x / (target : Real) := by
      have htwoTargetPositive : 0 < (2 : Real) * (target : Real) := by positivity
      apply (div_le_div_iff₀ htwoTargetPositive htargetRealPositive).2
      nlinarith
    have hpowerLe :
        (x / (2 * (target : Real))) ^ gamma14551 ≤
          (x / (target : Real)) ^ gamma14551 :=
      Real.rpow_le_rpow hhalfNonnegative hratioLe gamma14551_pos.le
    have hscaled :
        constant * k19PrincipalWeights index *
            (x / (2 * (target : Real))) ^ gamma14551 ≤
          constant * k19PrincipalWeights index *
            (x / (target : Real)) ^ gamma14551 :=
      mul_le_mul_of_nonneg_left hpowerLe
        (mul_nonneg hconstant.le (k19PrincipalWeights_pos index).le)
    have hpowerNonnegative :
        0 ≤ (x / (2 * (target : Real))) ^ gamma14551 :=
      Real.rpow_nonneg hhalfNonnegative _
    have hdrop :
        constant * (x / (2 * (target : Real))) ^ gamma14551 ≤
          constant * k19PrincipalWeights index *
            (x / (2 * (target : Real))) ^ gamma14551 := by
      calc
        constant * (x / (2 * (target : Real))) ^ gamma14551 =
            (constant * (x / (2 * (target : Real))) ^ gamma14551) * 1 := by ring
        _ ≤ (constant * (x / (2 * (target : Real))) ^ gamma14551) *
              k19PrincipalWeights index :=
          mul_le_mul_of_nonneg_left (one_le_k19PrincipalWeights index)
            (mul_nonneg hconstant.le hpowerNonnegative)
        _ = constant * k19PrincipalWeights index *
              (x / (2 * (target : Real))) ^ gamma14551 := by ring
    rw [gamma14551] at hdrop hscaled hraw
    exact hdrop.trans (hscaled.trans hraw)

#print axioms Erdos1135.KrasikovLagarias.K19UniformMovingTarget.uniform_nonperiodic_target_ratio_bound

end K19UniformMovingTarget
end KrasikovLagarias
end Erdos1135

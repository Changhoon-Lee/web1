import K19UniformMovingTarget

/-!
# Same-exponent tempered K19 moving-target bridge

The direct weighted sixteen-side comparison fails for the original K19
coefficient vector because its dynamic range is too large.  Lowering the K19
exponent by a fractional-power feasibility transform would introduce a severe
terminal-capacity tax.

A different operation preserves the original K19 exponent: keep the proven
coefficient-level lower bound and only replace each positive natural
coefficient `w` by the smaller tempered weight `w^(1/16)`.  Since `w ≥ 1`, this
new coefficient is bounded above by `w`; hence the original predecessor lower
bound immediately implies the tempered one with the same exponent
`14551/16000` and the same uniform envelope constant.

The exact finite side calculation uses the authenticated global K19 bounds

* `w_min = 1497192`,
* `w_max = 4166117961`,

and the integer inequality

`w_min * 5^16 > w_max * 3^16`

to obtain a universal weight-ratio floor `(w_min/w_max)^(1/16) > 3/5`.
Together with the next sixteen bad-spine side targets this gives the exact
rational lower factor

`197713451 / 172186884 > 8/7`.

This file formalizes the K19 theorem-level tempering and the exact scalar
consumer.  The dynamical side-target inequality is kept as a separately audited
finite/paper certificate.
-/

namespace Erdos1135
namespace KrasikovLagarias
namespace K19TemperedMovingTarget

open EliminationResidue
open K19CriticalChoice
open K19UniformMovingTarget
open Terras

noncomputable def temperExponent : Real := (1 : Real) / 16

/-- Every positive K19 natural coefficient dominates its sixteenth-root
Tempering. -/
theorem temperedWeight_le_weight (index : PrincipalIndex 19) :
    k19PrincipalWeights index ^ temperExponent ≤
      k19PrincipalWeights index := by
  have h := Real.rpow_le_rpow_of_exponent_le
    (one_le_k19PrincipalWeights index)
    (show temperExponent ≤ (1 : Real) by norm_num [temperExponent])
  simpa using h

/-- The original uniform principal K19 theorem immediately yields a
sixteenth-root-weighted theorem at the unchanged exponent `14551/16000`. -/
theorem exists_uniform_tempered_principal_ratio_bound :
    ∃ envelopeConstant : Real, 0 < envelopeConstant ∧
      ∀ (index : PrincipalIndex 19) {sourceTarget target : Nat},
        AdmissibleTarget 19 (residue index) sourceTarget →
        Reaches sourceTarget target →
        ∀ x : Real, (sourceTarget : Real) ≤ x →
          envelopeConstant *
              (k19PrincipalWeights index ^ temperExponent) *
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
          (k19PrincipalWeights index ^ temperExponent) ≤
        envelopeConstant * k19PrincipalWeights index :=
    mul_le_mul_of_nonneg_left (temperedWeight_le_weight index)
      henvelopeConstant.le
  calc
    envelopeConstant *
          (k19PrincipalWeights index ^ temperExponent) *
          (x / (sourceTarget : Real)) ^ gamma14551 ≤
        envelopeConstant * k19PrincipalWeights index *
          (x / (sourceTarget : Real)) ^ gamma14551 :=
      mul_le_mul_of_nonneg_right hcoefficient hpowerNonnegative
    _ ≤ (predecessorCountReal target x : Real) :=
      huniform index hadmissible hreach x hx

/-- Exact rational lower factor obtained from the conservative global K19
weight ratio and the sixteen bad-spine spatial ratios. -/
noncomputable def temperedSixteenSideFactor : Real :=
  (197713451 : Real) / 172186884

/-- The same-potential sixteen-side factor strictly clears `8/7`. -/
theorem temperedSixteenSideFactor_gt_eight_sevenths :
    (8 : Real) / 7 < temperedSixteenSideFactor := by
  norm_num [temperedSixteenSideFactor]

/-- Exact positive margin above `8/7`. -/
theorem temperedSixteenSideFactor_margin :
    temperedSixteenSideFactor - (8 : Real) / 7 =
      (6499085 : Real) / 1205308188 := by
  norm_num [temperedSixteenSideFactor]

/-- Consumer surface for a dynamical side-target certificate expressed in the
same tempered K19 potential. -/
theorem side_mass_gt_eight_sevenths_of_tempered_factor
    {parentMass sideMass : Real} (hparent : 0 < parentMass)
    (hside : temperedSixteenSideFactor * parentMass < sideMass) :
    (8 : Real) / 7 * parentMass < sideMass := by
  have hfactor := temperedSixteenSideFactor_gt_eight_sevenths
  have hscaled := mul_lt_mul_of_pos_right hfactor hparent
  exact hscaled.trans hside

#print axioms Erdos1135.KrasikovLagarias.K19TemperedMovingTarget.temperedWeight_le_weight
#print axioms Erdos1135.KrasikovLagarias.K19TemperedMovingTarget.exists_uniform_tempered_principal_ratio_bound
#print axioms Erdos1135.KrasikovLagarias.K19TemperedMovingTarget.temperedSixteenSideFactor_gt_eight_sevenths
#print axioms Erdos1135.KrasikovLagarias.K19TemperedMovingTarget.side_mass_gt_eight_sevenths_of_tempered_factor

end K19TemperedMovingTarget
end KrasikovLagarias
end Erdos1135

import Mathlib
import UltraTemperedSideExactBudget

/-!
# Same-potential deep-frontier contract at 1/256 tempering

The exact side factor is

`30645584905 / 16529940864 > 9/5`.

Its reciprocal is below `5/9`.  Therefore any lawful deep frontier retaining
`5/9` of the *same* 1/256-tempered numerical potential yields strict growth.
-/

namespace UltraTemperedDeepFrontierContract

open UltraTemperedSideExactBudget

noncomputable def frontierThreshold : ℝ :=
  (16529940864 : ℝ) / 30645584905

@[simp] theorem factor_mul_threshold :
    ultraTemperedSixteenSideFactor * frontierThreshold = 1 := by
  norm_num [ultraTemperedSixteenSideFactor, frontierThreshold]

@[simp] theorem threshold_mul_factor :
    frontierThreshold * ultraTemperedSixteenSideFactor = 1 := by
  norm_num [ultraTemperedSixteenSideFactor, frontierThreshold]

/-- Same-potential scalar composition. -/
theorem composition_of_same_ultra_tempered_potential
    {parentMass sideMass frontierMass retention : ℝ}
    (hparent : 0 < parentMass)
    (hside : ultraTemperedSixteenSideFactor * parentMass < sideMass)
    (hretention : frontierThreshold < retention)
    (hfrontier : retention * sideMass ≤ frontierMass) :
    parentMass < frontierMass := by
  have hsidePositive : 0 < sideMass :=
    (mul_pos (by norm_num [ultraTemperedSixteenSideFactor]) hparent).trans hside
  have hthresholdPositive : 0 < frontierThreshold := by
    norm_num [frontierThreshold]
  have hscaledSide :
      frontierThreshold *
          (ultraTemperedSixteenSideFactor * parentMass) <
        frontierThreshold * sideMass :=
    mul_lt_mul_of_pos_left hside hthresholdPositive
  have hparentBelow : parentMass < frontierThreshold * sideMass := by
    calc
      parentMass = frontierThreshold *
          (ultraTemperedSixteenSideFactor * parentMass) := by
        rw [← mul_assoc, threshold_mul_factor, one_mul]
      _ < frontierThreshold * sideMass := hscaledSide
  have hscaledRetention :
      frontierThreshold * sideMass < retention * sideMass :=
    mul_lt_mul_of_pos_right hretention hsidePositive
  exact hparentBelow.trans (hscaledRetention.trans_le hfrontier)

/-- A same-potential `5/9` deep-frontier retention is sufficient. -/
theorem composition_of_five_ninths_retention
    {parentMass sideMass frontierMass : ℝ}
    (hparent : 0 < parentMass)
    (hside : ultraTemperedSixteenSideFactor * parentMass < sideMass)
    (hfrontier : ((5 : ℝ) / 9) * sideMass ≤ frontierMass) :
    parentMass < frontierMass := by
  exact composition_of_same_ultra_tempered_potential hparent hside
    ultraTemperedFrontierThreshold_lt_five_ninths hfrontier

#print axioms UltraTemperedDeepFrontierContract.composition_of_same_ultra_tempered_potential
#print axioms UltraTemperedDeepFrontierContract.composition_of_five_ninths_retention

end UltraTemperedDeepFrontierContract

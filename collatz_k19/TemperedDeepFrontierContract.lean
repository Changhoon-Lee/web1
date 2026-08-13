import Mathlib

/-!
# Same-potential contract for the tempered bad-spine / K19 frontier bridge

The certified sixteen-side scalar factor is

`197713451 / 172186884 > 8/7`.

Its exact reciprocal is the retention threshold that a subsequent K19 deep
frontier must beat.  The two inequalities compose only when they refer to the
same numerical potential.  This file deliberately makes that requirement an
explicit common variable rather than silently multiplying bounds obtained for
different weights or different normalizations.
-/

namespace TemperedDeepFrontierContract

noncomputable def sideFactor : ℝ :=
  (197713451 : ℝ) / 172186884

noncomputable def frontierThreshold : ℝ :=
  (172186884 : ℝ) / 197713451

@[simp] theorem sideFactor_mul_frontierThreshold :
    sideFactor * frontierThreshold = 1 := by
  norm_num [sideFactor, frontierThreshold]

@[simp] theorem frontierThreshold_mul_sideFactor :
    frontierThreshold * sideFactor = 1 := by
  norm_num [sideFactor, frontierThreshold]

/-- The exact side factor strictly clears `8/7`. -/
theorem sideFactor_gt_eight_sevenths :
    (8 : ℝ) / 7 < sideFactor := by
  norm_num [sideFactor]

/-- Consequently the exact required frontier retention lies strictly below
`7/8`; this records the remaining numerical room without identifying the
frontier theorem itself. -/
theorem frontierThreshold_lt_seven_eighths :
    frontierThreshold < (7 : ℝ) / 8 := by
  norm_num [frontierThreshold]

/-- Same-potential composition.  `parentMass`, `sideMass`, and `frontierMass`
must be evaluations of one and the same potential on successive lawful
numerical antichains. -/
theorem composition_of_same_potential
    {parentMass sideMass frontierMass retention : ℝ}
    (hparent : 0 < parentMass)
    (hside : sideFactor * parentMass < sideMass)
    (hretention : frontierThreshold < retention)
    (hfrontier : retention * sideMass ≤ frontierMass) :
    parentMass < frontierMass := by
  have hsidePositive : 0 < sideMass :=
    (mul_pos (by norm_num [sideFactor]) hparent).trans hside
  have hthresholdPositive : 0 < frontierThreshold := by
    norm_num [frontierThreshold]
  have hscaledSide :
      frontierThreshold * (sideFactor * parentMass) <
        frontierThreshold * sideMass :=
    mul_lt_mul_of_pos_left hside hthresholdPositive
  have hparentBelowThresholdSide :
      parentMass < frontierThreshold * sideMass := by
    calc
      parentMass = frontierThreshold * (sideFactor * parentMass) := by
        rw [← mul_assoc, frontierThreshold_mul_sideFactor, one_mul]
      _ < frontierThreshold * sideMass := hscaledSide
  have hthresholdScaled :
      frontierThreshold * sideMass < retention * sideMass :=
    mul_lt_mul_of_pos_right hretention hsidePositive
  exact hparentBelowThresholdSide.trans
    (hthresholdScaled.trans_le hfrontier)

/-- Convenient sufficient specialization: a same-potential `7/8` frontier
retention is already more than enough. -/
theorem composition_of_seven_eighths_retention
    {parentMass sideMass frontierMass : ℝ}
    (hparent : 0 < parentMass)
    (hside : sideFactor * parentMass < sideMass)
    (hfrontier : ((7 : ℝ) / 8) * sideMass ≤ frontierMass) :
    parentMass < frontierMass := by
  exact composition_of_same_potential hparent hside
    frontierThreshold_lt_seven_eighths hfrontier

#print axioms TemperedDeepFrontierContract.composition_of_same_potential
#print axioms TemperedDeepFrontierContract.composition_of_seven_eighths_retention

end TemperedDeepFrontierContract

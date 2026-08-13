import Mathlib

/-!
# Unweighted same-potential side / frontier contract

The finite sixteen-side theorem is naturally expressed in the coefficient-one
K19 critical potential.  Its strict side factor is `8/7`; therefore a fresh
numerical frontier retaining at least `7/8` of that same potential gives strict
growth.

This contract avoids every coefficient-normalization comparison.  It is only a
consumer surface: the actual bounded-depth numerical frontier theorem remains a
separate obligation.
-/

namespace UnweightedSideFrontierContract

noncomputable def sideFactor : ℝ := (8 : ℝ) / 7
noncomputable def frontierThreshold : ℝ := (7 : ℝ) / 8

@[simp] theorem factor_times_threshold :
    sideFactor * frontierThreshold = 1 := by
  norm_num [sideFactor, frontierThreshold]

@[simp] theorem threshold_times_factor :
    frontierThreshold * sideFactor = 1 := by
  norm_num [sideFactor, frontierThreshold]

/-- Same-potential composition at the exact reciprocal threshold. -/
theorem composition_of_same_unweighted_potential
    {parentMass sideMass frontierMass retention : ℝ}
    (hparent : 0 < parentMass)
    (hside : sideFactor * parentMass < sideMass)
    (hretention : frontierThreshold < retention)
    (hfrontier : retention * sideMass ≤ frontierMass) :
    parentMass < frontierMass := by
  have hfactorPositive : 0 < sideFactor := by norm_num [sideFactor]
  have hsidePositive : 0 < sideMass :=
    (mul_pos hfactorPositive hparent).trans hside
  have hthresholdPositive : 0 < frontierThreshold := by
    norm_num [frontierThreshold]
  have hscaledSide :
      frontierThreshold * (sideFactor * parentMass) <
        frontierThreshold * sideMass :=
    mul_lt_mul_of_pos_left hside hthresholdPositive
  have hparentBelow : parentMass < frontierThreshold * sideMass := by
    calc
      parentMass = frontierThreshold * (sideFactor * parentMass) := by
        rw [← mul_assoc, threshold_times_factor, one_mul]
      _ < frontierThreshold * sideMass := hscaledSide
  have hscaledRetention :
      frontierThreshold * sideMass < retention * sideMass :=
    mul_lt_mul_of_pos_right hretention hsidePositive
  exact hparentBelow.trans (hscaledRetention.trans_le hfrontier)

/-- Any explicit retention strictly above `7/8`, for example `29/32`, suffices. -/
theorem composition_of_twentyNine_over_thirtyTwo_retention
    {parentMass sideMass frontierMass : ℝ}
    (hparent : 0 < parentMass)
    (hside : sideFactor * parentMass < sideMass)
    (hfrontier : ((29 : ℝ) / 32) * sideMass ≤ frontierMass) :
    parentMass < frontierMass := by
  have hretention : frontierThreshold < (29 : ℝ) / 32 := by
    norm_num [frontierThreshold]
  exact composition_of_same_unweighted_potential hparent hside
    hretention hfrontier

#print axioms UnweightedSideFrontierContract.composition_of_same_unweighted_potential
#print axioms UnweightedSideFrontierContract.composition_of_twentyNine_over_thirtyTwo_retention

end UnweightedSideFrontierContract

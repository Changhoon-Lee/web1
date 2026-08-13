import Mathlib

/-!
# Corrected ultra-tempered side / frontier contract

The unweighted finite sixteen-side theorem gives a strict factor `8/7`.
For the authenticated K19 coefficient range, 256th-root tempering gives a
uniform output/input coefficient ratio strictly larger than `31/32`.
Therefore the valid same-potential side factor is strictly larger than

`(31/32) * (8/7) = 31/28`.

The corresponding deep-frontier retention threshold is `28/31`.

This file replaces the invalid `9/5` interpretation, which had omitted the
factor `1/2` in the numerical side-size ratio
`2^j / 3^(j+1) = (1/2) * (2/3)^(j+1)`.
-/

namespace CorrectedUltraTemperedSideContract

noncomputable def correctedSideFactor : ℝ := (31 : ℝ) / 28
noncomputable def correctedFrontierThreshold : ℝ := (28 : ℝ) / 31

@[simp] theorem corrected_factor_times_threshold :
    correctedSideFactor * correctedFrontierThreshold = 1 := by
  norm_num [correctedSideFactor, correctedFrontierThreshold]

@[simp] theorem corrected_threshold_times_factor :
    correctedFrontierThreshold * correctedSideFactor = 1 := by
  norm_num [correctedSideFactor, correctedFrontierThreshold]

/-- The corrected same-potential factor is strictly larger than one. -/
theorem correctedSideFactor_gt_one :
    (1 : ℝ) < correctedSideFactor := by
  norm_num [correctedSideFactor]

/-- The exact required same-potential frontier retention. -/
theorem correctedFrontierThreshold_lt_one :
    correctedFrontierThreshold < (1 : ℝ) := by
  norm_num [correctedFrontierThreshold]

/-- Exact arithmetic assembling the two independently valid lower factors. -/
theorem corrected_factor_identity :
    (31 : ℝ) / 32 * ((8 : ℝ) / 7) = correctedSideFactor := by
  norm_num [correctedSideFactor]

/-- Same-potential composition at the corrected threshold. -/
theorem composition_of_corrected_same_potential
    {parentMass sideMass frontierMass retention : ℝ}
    (hparent : 0 < parentMass)
    (hside : correctedSideFactor * parentMass < sideMass)
    (hretention : correctedFrontierThreshold < retention)
    (hfrontier : retention * sideMass ≤ frontierMass) :
    parentMass < frontierMass := by
  have hfactorPositive : 0 < correctedSideFactor := by
    norm_num [correctedSideFactor]
  have hsidePositive : 0 < sideMass :=
    (mul_pos hfactorPositive hparent).trans hside
  have hthresholdPositive : 0 < correctedFrontierThreshold := by
    norm_num [correctedFrontierThreshold]
  have hscaledSide :
      correctedFrontierThreshold *
          (correctedSideFactor * parentMass) <
        correctedFrontierThreshold * sideMass :=
    mul_lt_mul_of_pos_left hside hthresholdPositive
  have hparentBelow :
      parentMass < correctedFrontierThreshold * sideMass := by
    calc
      parentMass = correctedFrontierThreshold *
          (correctedSideFactor * parentMass) := by
        rw [← mul_assoc, corrected_threshold_times_factor, one_mul]
      _ < correctedFrontierThreshold * sideMass := hscaledSide
  have hscaledRetention :
      correctedFrontierThreshold * sideMass < retention * sideMass :=
    mul_lt_mul_of_pos_right hretention hsidePositive
  exact hparentBelow.trans (hscaledRetention.trans_le hfrontier)

/-- A lawful same-potential `29/32` frontier would already be sufficient. -/
theorem composition_of_twentyNine_over_thirtyTwo_retention
    {parentMass sideMass frontierMass : ℝ}
    (hparent : 0 < parentMass)
    (hside : correctedSideFactor * parentMass < sideMass)
    (hfrontier : ((29 : ℝ) / 32) * sideMass ≤ frontierMass) :
    parentMass < frontierMass := by
  have hthreshold : correctedFrontierThreshold < (29 : ℝ) / 32 := by
    norm_num [correctedFrontierThreshold]
  exact composition_of_corrected_same_potential hparent hside
    hthreshold hfrontier

#print axioms CorrectedUltraTemperedSideContract.corrected_factor_identity
#print axioms CorrectedUltraTemperedSideContract.composition_of_corrected_same_potential
#print axioms CorrectedUltraTemperedSideContract.composition_of_twentyNine_over_thirtyTwo_retention

end CorrectedUltraTemperedSideContract

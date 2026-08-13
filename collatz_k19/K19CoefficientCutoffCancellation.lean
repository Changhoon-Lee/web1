import Mathlib

/-!
# Exact K19 coefficient cancellation by target-specific cutoffs

Let

* `gamma = 14551/16000`,
* `theta = 1449/16000 = 1 - gamma`,
* `weight = scaleWeight^theta`, and
* `H = L * source * scaleWeight`.

Then the coefficient-weighted K19 density

`weight * (H/source)^gamma / H`

is exactly

`L^(-theta) / source`.

Thus target-specific cutoffs scaled by the `theta`-root of the K19 coefficient
convert the coefficient-weighted K19 lower bound into one common unweighted
source-reciprocal potential.  This is an algebraic normalization theorem; the
variable-cutoff harmonic capacity and numerical frontier construction are
separate theorem surfaces.
-/

namespace K19CoefficientCutoffCancellation

noncomputable def gamma : ℝ := (14551 : ℝ) / 16000
noncomputable def theta : ℝ := (1449 : ℝ) / 16000

@[simp] theorem gamma_add_theta : gamma + theta = 1 := by
  norm_num [gamma, theta]

@[simp] theorem gamma_sub_one : gamma - 1 = -theta := by
  norm_num [gamma, theta]

/-- Exact cancellation written in terms of the positive coefficient scale
`scaleWeight`, whose `theta` power is the original K19 coefficient. -/
theorem exact_cutoff_cancellation
    {L source scaleWeight : ℝ}
    (hL : 0 < L) (hsource : 0 < source)
    (hscaleWeight : 0 < scaleWeight) :
    scaleWeight ^ theta *
        ((L * source * scaleWeight) / source) ^ gamma /
        (L * source * scaleWeight) =
      L ^ (-theta) / source := by
  have hratio :
      (L * source * scaleWeight) / source = L * scaleWeight := by
    field_simp [hsource.ne']
  rw [hratio, Real.mul_rpow hL.le hscaleWeight.le]
  have hweight :
      scaleWeight ^ theta * scaleWeight ^ gamma = scaleWeight := by
    rw [← Real.rpow_add hscaleWeight, theta, gamma]
    norm_num
  have hLratio : L ^ gamma / L = L ^ (-theta) := by
    rw [show L = L ^ (1 : ℝ) by simp]
    rw [← Real.rpow_sub hL]
    rw [gamma_sub_one]
  field_simp [hsource.ne', hscaleWeight.ne']
  calc
    scaleWeight ^ theta * (L ^ gamma * scaleWeight ^ gamma) =
        L ^ gamma *
          (scaleWeight ^ theta * scaleWeight ^ gamma) := by ring
    _ = L ^ gamma * scaleWeight := by rw [hweight]
    _ = (L ^ (-theta) * L) * scaleWeight := by
      rw [← hLratio]
    _ = L ^ (-theta) * (L * scaleWeight) := by ring

/-- Consumer form for a K19 lower bound. -/
theorem reciprocal_lower_bound_of_coefficient_lower_bound
    {constant L source scaleWeight count : ℝ}
    (hconstant : 0 ≤ constant)
    (hL : 0 < L) (hsource : 0 < source)
    (hscaleWeight : 0 < scaleWeight)
    (hlower :
      constant * scaleWeight ^ theta *
          (((L * source * scaleWeight) / source) ^ gamma) ≤ count) :
    constant * L ^ (-theta) / source ≤
      count / (L * source * scaleWeight) := by
  have hcutoff : 0 < L * source * scaleWeight := by positivity
  apply (le_div_iff₀ hcutoff).2
  calc
    constant * L ^ (-theta) / source *
        (L * source * scaleWeight) =
      constant *
        (scaleWeight ^ theta *
          (((L * source * scaleWeight) / source) ^ gamma)) := by
        rw [exact_cutoff_cancellation hL hsource hscaleWeight]
        field_simp [hsource.ne']
        ring
    _ ≤ count := hlower

#print axioms K19CoefficientCutoffCancellation.exact_cutoff_cancellation
#print axioms K19CoefficientCutoffCancellation.reciprocal_lower_bound_of_coefficient_lower_bound

end K19CoefficientCutoffCancellation

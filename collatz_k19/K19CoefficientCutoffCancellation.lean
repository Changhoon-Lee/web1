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
source-reciprocal potential. This is an algebraic normalization theorem; the
variable-cutoff harmonic capacity and numerical frontier construction are
separate theorem surfaces.
-/

namespace K19CoefficientCutoffCancellation

noncomputable def gamma : ℝ := (14551 : ℝ) / 16000
noncomputable def theta : ℝ := (1449 : ℝ) / 16000

@[simp] theorem gamma_add_theta : gamma + theta = 1 := by
  norm_num [gamma, theta]

@[simp] theorem theta_add_gamma : theta + gamma = 1 := by
  norm_num [gamma, theta]

@[simp] theorem gamma_eq_neg_theta_add_one :
    gamma = -theta + 1 := by
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
  have hLpower : L ^ gamma = L ^ (-theta) * L := by
    calc
      L ^ gamma = L ^ ((-theta) + 1) := by
        rw [gamma_eq_neg_theta_add_one]
      _ = L ^ (-theta) * L ^ (1 : ℝ) := by
        rw [Real.rpow_add hL]
      _ = L ^ (-theta) * L := by simp
  have hWpower :
      scaleWeight ^ theta * scaleWeight ^ gamma = scaleWeight := by
    calc
      scaleWeight ^ theta * scaleWeight ^ gamma =
          scaleWeight ^ (theta + gamma) := by
            rw [Real.rpow_add hscaleWeight]
      _ = scaleWeight := by rw [theta_add_gamma]; simp
  rw [hratio, Real.mul_rpow hL.le hscaleWeight.le, hLpower]
  calc
    scaleWeight ^ theta *
          ((L ^ (-theta) * L) * scaleWeight ^ gamma) /
          (L * source * scaleWeight) =
        ((L ^ (-theta) * L) *
          (scaleWeight ^ theta * scaleWeight ^ gamma)) /
          (L * source * scaleWeight) := by ring
    _ = ((L ^ (-theta) * L) * scaleWeight) /
          (L * source * scaleWeight) := by rw [hWpower]
    _ = L ^ (-theta) / source := by
      field_simp [hL.ne', hsource.ne', hscaleWeight.ne']

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
  have hcancel := exact_cutoff_cancellation hL hsource hscaleWeight
  calc
    constant * L ^ (-theta) / source =
        constant *
          (scaleWeight ^ theta *
            (((L * source * scaleWeight) / source) ^ gamma) /
            (L * source * scaleWeight)) := by
      rw [hcancel]
    _ =
        (constant * scaleWeight ^ theta *
          (((L * source * scaleWeight) / source) ^ gamma)) /
          (L * source * scaleWeight) := by ring
    _ ≤ count / (L * source * scaleWeight) :=
      div_le_div_of_nonneg_right hlower hcutoff.le

#print axioms K19CoefficientCutoffCancellation.exact_cutoff_cancellation
#print axioms K19CoefficientCutoffCancellation.reciprocal_lower_bound_of_coefficient_lower_bound

end K19CoefficientCutoffCancellation

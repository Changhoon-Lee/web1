import Mathlib

/-!
# Weighted critical transfer at the K19 exponent

The strict-exponent Gate B is impossible after distinct numerical-output
collapse, but the coefficient-level K19 envelope contains a sharper critical
route.  Before uniformization, the lower bound carries the exact positive
certificate weight of the principal residue.

Let

* `gamma = 14551/16000`,
* `theta = 1449/16000 = 1 - gamma`,
* `delta` be the retarded-envelope delay factor,
* `W` be the total certificate weight,
* `M` be the weighted harmonic mass of a finite antichain of targets, and
* `D` be its normalized weighted critical density, so that
  `D * W * H^theta ≤ M`.

If the coefficient-level predecessor lower bounds sum to

`(delta / W) * H^gamma * M`

and the disjoint predecessor capacity is at most `2H`, then necessarily

`delta * D ≤ 2`.

Consequently, constructing a lawful target antichain with `delta * D > 2`
would give an immediate contradiction at the exact critical exponent.  This
is the corrected positive live arrow after the harmonic-ceiling no-go.
-/

namespace K19WeightedCriticalTransfer

noncomputable def gamma : ℝ := (14551 : ℝ) / 16000
noncomputable def theta : ℝ := (1449 : ℝ) / 16000

@[simp] theorem gamma_add_theta : gamma + theta = 1 := by
  norm_num [gamma, theta]

/-- Exact algebraic cancellation of the K19 normalization and complementary
powers. -/
theorem normalization_power_cancellation
    {delta W H D : ℝ} (hW : 0 < W) (hH : 0 < H) :
    (delta / W) * H ^ gamma * (D * W * H ^ theta) =
      delta * D * H := by
  have hpow : H ^ gamma * H ^ theta = H := by
    rw [← Real.rpow_add hH, gamma_add_theta]
    simp
  calc
    (delta / W) * H ^ gamma * (D * W * H ^ theta) =
        delta * D * (H ^ gamma * H ^ theta) := by
      field_simp [hW.ne']
      ring
    _ = delta * D * H := by rw [hpow]

/-- Capacity forces the exact weighted critical product to be at most two. -/
theorem weighted_critical_product_le_two
    {delta W H D M total : ℝ}
    (hdelta : 0 ≤ delta) (hW : 0 < W) (hH : 0 < H) (hD : 0 ≤ D)
    (hoccupancy : D * W * H ^ theta ≤ M)
    (hlower : (delta / W) * H ^ gamma * M ≤ total)
    (hcapacity : total ≤ 2 * H) :
    delta * D ≤ 2 := by
  have hscale : 0 ≤ (delta / W) * H ^ gamma := by
    exact mul_nonneg (div_nonneg hdelta hW.le)
      (Real.rpow_nonneg hH.le _)
  have hscaled := mul_le_mul_of_nonneg_left hoccupancy hscale
  have hchain :
      (delta / W) * H ^ gamma * (D * W * H ^ theta) ≤ 2 * H :=
    hscaled.trans (hlower.trans hcapacity)
  rw [normalization_power_cancellation hW hH] at hchain
  nlinarith

/-- Corrected positive Gate B: a lawful weighted antichain whose normalized
critical density satisfies `delta * D > 2` contradicts the single-cutoff
capacity bound. -/
theorem contradiction_of_weighted_critical_overflow
    {delta W H D M total : ℝ}
    (hdelta : 0 ≤ delta) (hW : 0 < W) (hH : 0 < H) (hD : 0 ≤ D)
    (hoccupancy : D * W * H ^ theta ≤ M)
    (hlower : (delta / W) * H ^ gamma * M ≤ total)
    (hcapacity : total ≤ 2 * H)
    (hoverflow : 2 < delta * D) : False := by
  have hceiling := weighted_critical_product_le_two hdelta hW hH hD
    hoccupancy hlower hcapacity
  linarith

/-- The exact K19 exponents used by the weighted critical gate. -/
theorem exponent_identity :
    (14551 : ℝ) / 16000 + (1449 : ℝ) / 16000 = 1 := by
  norm_num

#print axioms K19WeightedCriticalTransfer.contradiction_of_weighted_critical_overflow

end K19WeightedCriticalTransfer

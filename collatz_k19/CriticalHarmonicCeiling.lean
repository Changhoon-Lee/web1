import Mathlib

/-!
# Critical harmonic ceiling for distinct positive integer outputs

For `0 < theta ≤ 1`, Bernoulli's inequality gives the discrete derivative
estimate

`theta * n^(theta - 1) ≤ n^theta - (n-1)^theta`.

Summing yields the exact terminal ceiling

`theta * ∑_{1 ≤ n ≤ H} n^(theta - 1) ≤ H^theta`.

At the K19 exponent `gamma = 14551/16000`, the complementary exponent is
`theta = 1449/16000`; therefore every finite family of distinct positive
integer outputs below height `H` has total `gamma`-harmonic mass at most a
constant times `H^theta`.  No distinct-output, single-height argument can
produce a strict exponent larger than `theta` after numerical output collapse.
-/

namespace CriticalHarmonicCeiling

open scoped BigOperators

/-- Discrete concavity estimate for real powers in the interval `(0,1]`. -/
theorem rpow_complement_step
    {theta : ℝ} (htheta0 : 0 < theta) (htheta1 : theta ≤ 1)
    (n : ℕ) (hn : 1 ≤ n) :
    theta * (n : ℝ) ^ (theta - 1) ≤
      (n : ℝ) ^ theta - ((n - 1 : ℕ) : ℝ) ^ theta := by
  have hnpos : 0 < (n : ℝ) := by exact_mod_cast (lt_of_lt_of_le Nat.zero_lt_one hn)
  have hnnonneg : 0 ≤ (n : ℝ) := hnpos.le
  let s : ℝ := -(1 / (n : ℝ))
  have hfrac : 1 / (n : ℝ) ≤ 1 := by
    exact (div_le_one hnpos).2 (by exact_mod_cast hn)
  have hs : -1 ≤ s := by
    dsimp [s]
    linarith
  have hones : 0 ≤ 1 + s := by linarith
  have hbern :=
    Real.rpow_one_add_le_one_add_mul_self hs htheta0.le htheta1
  have hscaled :=
    mul_le_mul_of_nonneg_left hbern (Real.rpow_nonneg hnnonneg theta)
  have hcast : ((n - 1 : ℕ) : ℝ) = (n : ℝ) - 1 := by
    rw [Nat.cast_sub hn]
    norm_num
  have hbase : (n : ℝ) * (1 + s) = ((n - 1 : ℕ) : ℝ) := by
    rw [hcast]
    dsimp [s]
    field_simp [hnpos.ne']
    ring
  have hleft :
      (n : ℝ) ^ theta * (1 + s) ^ theta =
        ((n - 1 : ℕ) : ℝ) ^ theta := by
    rw [← Real.mul_rpow hnnonneg hones, hbase]
  have hrpowSub :
      (n : ℝ) ^ (theta - 1) = (n : ℝ) ^ theta / (n : ℝ) := by
    simpa using Real.rpow_sub_one hnpos.ne' theta
  have hright :
      (n : ℝ) ^ theta * (1 + theta * s) =
        (n : ℝ) ^ theta - theta * (n : ℝ) ^ (theta - 1) := by
    rw [hrpowSub]
    dsimp [s]
    field_simp [hnpos.ne']
    ring
  rw [hleft, hright] at hscaled
  linarith

/-- Exact finite harmonic ceiling, before division by `theta`. -/
theorem theta_mul_sum_Icc_rpow_sub_one_le
    {theta : ℝ} (htheta0 : 0 < theta) (htheta1 : theta ≤ 1) :
    ∀ H : ℕ,
      theta * (∑ n ∈ Finset.Icc 1 H, (n : ℝ) ^ (theta - 1)) ≤
        (H : ℝ) ^ theta := by
  intro H
  induction H with
  | zero =>
      simp [htheta0.ne']
  | succ H ih =>
      have hnotmem : H + 1 ∉ Finset.Icc 1 H := by
        simp
      have hstep := rpow_complement_step htheta0 htheta1 (H + 1) (by omega)
      rw [show Finset.Icc 1 (H + 1) = insert (H + 1) (Finset.Icc 1 H) by
        ext n
        simp
        omega]
      rw [Finset.sum_insert hnotmem]
      have hcast : (((H + 1 : ℕ) - 1 : ℕ) : ℝ) = (H : ℝ) := by
        norm_num
      rw [hcast] at hstep
      calc
        theta * ((H + 1 : ℝ) ^ (theta - 1) +
            ∑ n ∈ Finset.Icc 1 H, (n : ℝ) ^ (theta - 1)) =
            theta * (∑ n ∈ Finset.Icc 1 H, (n : ℝ) ^ (theta - 1)) +
              theta * (H + 1 : ℝ) ^ (theta - 1) := by ring
        _ ≤ (H : ℝ) ^ theta +
              ((H + 1 : ℝ) ^ theta - (H : ℝ) ^ theta) :=
          add_le_add ih hstep
        _ = (H + 1 : ℝ) ^ theta := by ring

/-- Divided form of the exact harmonic ceiling. -/
theorem sum_Icc_rpow_sub_one_le
    {theta : ℝ} (htheta0 : 0 < theta) (htheta1 : theta ≤ 1)
    (H : ℕ) :
    (∑ n ∈ Finset.Icc 1 H, (n : ℝ) ^ (theta - 1)) ≤
      (H : ℝ) ^ theta / theta := by
  apply (le_div_iff₀ htheta0).2
  simpa [mul_comm] using theta_mul_sum_Icc_rpow_sub_one_le htheta0 htheta1 H

/-- Any finite family of distinct positive integers below `H` inherits the
same ceiling by inclusion in the full interval. -/
theorem sum_subset_Icc_rpow_sub_one_le
    {theta : ℝ} (htheta0 : 0 < theta) (htheta1 : theta ≤ 1)
    {outputs : Finset ℕ} {H : ℕ}
    (houtputs : outputs ⊆ Finset.Icc 1 H) :
    (∑ n ∈ outputs, (n : ℝ) ^ (theta - 1)) ≤
      (H : ℝ) ^ theta / theta := by
  calc
    (∑ n ∈ outputs, (n : ℝ) ^ (theta - 1)) ≤
        ∑ n ∈ Finset.Icc 1 H, (n : ℝ) ^ (theta - 1) := by
      exact Finset.sum_le_sum_of_subset_of_nonneg houtputs
        (fun _ _ _ => Real.rpow_nonneg (by positivity) _)
    _ ≤ (H : ℝ) ^ theta / theta :=
      sum_Icc_rpow_sub_one_le htheta0 htheta1 H

/-- The exact complementary K19 exponent. -/
theorem k19_theta_identity :
    (1 : ℝ) - (14551 : ℝ) / 16000 = (1449 : ℝ) / 16000 := by
  norm_num

/-- K19-specialized harmonic terminal ceiling. -/
theorem k19_distinct_output_harmonic_ceiling
    {outputs : Finset ℕ} {H : ℕ}
    (houtputs : outputs ⊆ Finset.Icc 1 H) :
    (∑ n ∈ outputs, (n : ℝ) ^ (-(14551 : ℝ) / 16000)) ≤
      (H : ℝ) ^ ((1449 : ℝ) / 16000) / ((1449 : ℝ) / 16000) := by
  have htheta0 : (0 : ℝ) < (1449 : ℝ) / 16000 := by norm_num
  have htheta1 : (1449 : ℝ) / 16000 ≤ 1 := by norm_num
  have h := sum_subset_Icc_rpow_sub_one_le htheta0 htheta1 houtputs
  convert h using 1 <;> norm_num

#print axioms CriticalHarmonicCeiling.k19_distinct_output_harmonic_ceiling

end CriticalHarmonicCeiling

import Mathlib

/-!
# Strict subeigenvector amplification

A positive, monotone, positively homogeneous operator with a strict positive
subeigenvector eventually overcomes every fixed scalar loss at the abstract
coefficient level.  This is the correct interpretation of the authenticated
strict K19 row slack.

The theorem below is deliberately operator-generic.  It does not assert that an
abstract coefficient iterate has already been decoded into a collision-free
numerical Collatz first-hit frontier; that is a separate theorem surface.
-/

namespace StrictSubeigenvectorAmplification

/-- Pointwise order for real-valued vectors. -/
def PointwiseLE {ι : Type*} (u v : ι → ℝ) : Prop :=
  ∀ i, u i ≤ v i

/-- Iterated lower bound from a strict subeigenvector.  The initial vector only
needs to dominate a positive scalar multiple of the subeigenvector. -/
theorem iterate_lower_bound
    {ι : Type*} (T : (ι → ℝ) → (ι → ℝ))
    (w initial : ι → ℝ) {delta scale : ℝ}
    (hdelta : 0 ≤ delta) (hscale : 0 ≤ scale)
    (hmono : ∀ {u v : ι → ℝ}, PointwiseLE u v →
      PointwiseLE (T u) (T v))
    (hhomogeneous : ∀ (c : ℝ), 0 ≤ c → ∀ v : ι → ℝ,
      T (fun i => c * v i) = fun i => c * T v i)
    (hsubeigen : ∀ i, (1 + delta) * w i ≤ T w i)
    (hinitial : ∀ i, scale * w i ≤ initial i) :
    ∀ n i,
      scale * (1 + delta) ^ n * w i ≤
        (T^[n]) initial i := by
  intro n
  induction n with
  | zero =>
      intro i
      simpa using hinitial i
  | succ n ih =>
      intro i
      have hnonnegative : 0 ≤ scale * (1 + delta) ^ n := by
        exact mul_nonneg hscale (pow_nonneg (by linarith) _)
      have hpointwise : PointwiseLE
          (fun j => scale * (1 + delta) ^ n * w j)
          ((T^[n]) initial) := ih
      have hmonotone := hmono hpointwise i
      have hscaledSubeigen :=
        mul_le_mul_of_nonneg_left (hsubeigen i) hnonnegative
      have hhom := hhomogeneous
        (scale * (1 + delta) ^ n) hnonnegative w
      rw [Function.iterate_succ_apply]
      calc
        scale * (1 + delta) ^ (n + 1) * w i =
            (scale * (1 + delta) ^ n) * ((1 + delta) * w i) := by
          ring
        _ ≤ (scale * (1 + delta) ^ n) * T w i :=
          hscaledSubeigen
        _ = T (fun j => scale * (1 + delta) ^ n * w j) i := by
          rw [hhom]
        _ ≤ T ((T^[n]) initial) i := hmonotone

/-- Consumer form: any explicit finite power witness gives a uniform threshold
for all coordinates whose subeigenvector entries have a common positive floor. -/
theorem finite_threshold_of_power_witness
    {ι : Type*} (T : (ι → ℝ) → (ι → ℝ))
    (w initial : ι → ℝ) {delta scale floor threshold : ℝ}
    (hdelta : 0 ≤ delta) (hscale : 0 ≤ scale)
    (hmono : ∀ {u v : ι → ℝ}, PointwiseLE u v →
      PointwiseLE (T u) (T v))
    (hhomogeneous : ∀ (c : ℝ), 0 ≤ c → ∀ v : ι → ℝ,
      T (fun i => c * v i) = fun i => c * T v i)
    (hsubeigen : ∀ i, (1 + delta) * w i ≤ T w i)
    (hinitial : ∀ i, scale * w i ≤ initial i)
    (hfloor : ∀ i, floor ≤ w i)
    {n : ℕ}
    (hpower : threshold < scale * (1 + delta) ^ n * floor) :
    ∀ i, threshold < (T^[n]) initial i := by
  intro i
  have hlower := iterate_lower_bound T w initial hdelta hscale
    hmono hhomogeneous hsubeigen hinitial n i
  have hcoefficient : 0 ≤ scale * (1 + delta) ^ n := by
    exact mul_nonneg hscale (pow_nonneg (by linarith) _)
  have hfloorScaled :
      scale * (1 + delta) ^ n * floor ≤
        scale * (1 + delta) ^ n * w i :=
    mul_le_mul_of_nonneg_left (hfloor i) hcoefficient
  exact hpower.trans_le (hfloorScaled.trans hlower)

#print axioms StrictSubeigenvectorAmplification.iterate_lower_bound
#print axioms StrictSubeigenvectorAmplification.finite_threshold_of_power_witness

end StrictSubeigenvectorAmplification

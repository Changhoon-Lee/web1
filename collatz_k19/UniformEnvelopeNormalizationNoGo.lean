import Mathlib

/-!
# Uniform-envelope normalization no-go at level 19

The adaptive envelope theorem constructs a coefficient-level constant of the
form

`lambda ^ (-nu) / ∑ i, weight i`

with `1 ≤ lambda`, `0 ≤ nu`, and positive integer certificate weights.  If a
uniform target theorem drops every individual weight using only `1 ≤ weight i`,
then its exposed constant is at most the reciprocal of the number of principal
indices.

At level 19 there are `3^18 = 387420489` principal indices.  This reciprocal is
strictly below the critical constant `2 * (1449/16000)` forced by the K19
terminal-capacity calculation.  Thus the current all-principal uniform-envelope
normalization cannot close a critical-constant contradiction.
-/

namespace UniformEnvelopeNormalizationNoGo

open scoped BigOperators

/-- If every coefficient is at least one, their sum is at least the cardinality
of the finite index set. -/
theorem card_le_coefficient_sum
    {N : ℕ} (weights : Fin N → ℝ)
    (hweights : ∀ i, 1 ≤ weights i) :
    (N : ℝ) ≤ ∑ i, weights i := by
  calc
    (N : ℝ) = ∑ _ : Fin N, (1 : ℝ) := by simp
    _ ≤ ∑ i, weights i := by
      exact Finset.sum_le_sum fun i _ => hweights i

/-- The exposed coefficient-level envelope constant is bounded by the inverse
cardinality whenever the base is at least one and the shift exponent is
nonnegative. -/
theorem envelope_constant_le_card_inverse
    {N : ℕ} (hN : 0 < N)
    (weights : Fin N → ℝ) (hweights : ∀ i, 1 ≤ weights i)
    {lambda nu : ℝ} (hlambda : 1 ≤ lambda) (hnu : 0 ≤ nu) :
    lambda ^ (-nu) / (∑ i, weights i) ≤ 1 / (N : ℝ) := by
  have hNpos : (0 : ℝ) < N := by exact_mod_cast hN
  have hsum : (N : ℝ) ≤ ∑ i, weights i :=
    card_le_coefficient_sum weights hweights
  have hsumpos : 0 < ∑ i, weights i := hNpos.trans_le hsum
  have hrpow : lambda ^ (-nu) ≤ 1 :=
    Real.rpow_le_one_of_one_le_of_nonpos hlambda (neg_nonpos.mpr hnu)
  calc
    lambda ^ (-nu) / (∑ i, weights i) ≤
        1 / (∑ i, weights i) := by
      exact (div_le_div_iff_of_pos_right hsumpos).2 hrpow
    _ ≤ 1 / (N : ℝ) := by
      exact one_div_le_one_div_of_le hNpos hsum

/-- Exact level-19 principal cardinality. -/
theorem level19_principal_count : 3 ^ 18 = 387420489 := by
  norm_num

/-- The reciprocal-cardinality ceiling is far below the critical K19 constant
threshold. -/
theorem level19_card_inverse_lt_critical_constant :
    (1 : ℝ) / (3 ^ 18 : ℕ) < 2 * ((1449 : ℝ) / 16000) := by
  norm_num

/-- Standalone level-19 normalization no-go.  This theorem directly applies to
the constant formula exposed by the current adaptive envelope proof after the
certificate weights are dropped uniformly via `1 ≤ weight`. -/
theorem level19_uniform_envelope_constant_lt_critical
    (weights : Fin (3 ^ 18) → ℝ)
    (hweights : ∀ i, 1 ≤ weights i)
    {lambda nu : ℝ} (hlambda : 1 ≤ lambda) (hnu : 0 ≤ nu) :
    lambda ^ (-nu) / (∑ i, weights i) <
      2 * ((1449 : ℝ) / 16000) := by
  exact lt_of_le_of_lt
    (envelope_constant_le_card_inverse (by norm_num) weights hweights
      hlambda hnu)
    level19_card_inverse_lt_critical_constant

#print axioms UniformEnvelopeNormalizationNoGo.level19_uniform_envelope_constant_lt_critical

end UniformEnvelopeNormalizationNoGo

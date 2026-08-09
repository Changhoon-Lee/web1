import Mathlib

/-!
# Strict finite-certificate slack implies a genuine depth discount

Let an unweighted finite row satisfy `L + s ≤ R`, uniformly with `R ≤ Rmax`.
For a rational discount `q = a / b < 1`, the scalar condition

`(b^2 - a^2) * Rmax ≤ b^2 * s`

implies `b^2 * L ≤ a^2 * R`.  The mixed-cost D3 row is even stronger:
`a^2 * A + a*b*B ≥ a^2*(A+B)` when `0 ≤ a ≤ b` and `B ≥ 0`.
Thus one positive uniform row slack yields a nontrivial depth generating
function without changing the exponent.
-/

namespace DepthDiscountSlackTransfer

/-- Uniform quadratic discount transfer. -/
theorem qSquared_row
    {L R s Rmax a b : ℤ}
    (hL : 0 ≤ L) (hR : 0 ≤ R)
    (ha : 0 ≤ a) (hab : a ≤ b)
    (hslack : L + s ≤ R)
    (hRmax : R ≤ Rmax)
    (hscalar : (b^2 - a^2) * Rmax ≤ b^2 * s) :
    b^2 * L ≤ a^2 * R := by
  have hb : 0 ≤ b := ha.trans hab
  have hdiff : 0 ≤ b^2 - a^2 := by nlinarith
  have hloss : (b^2 - a^2) * R ≤ b^2 * s := by
    exact (mul_le_mul_of_nonneg_left hRmax hdiff).trans hscalar
  nlinarith

/-- D3 mixed-cost row: the auxiliary branch loses only one power of `q`, so
it dominates the uniform `q^2` discount. -/
theorem qMixed_row
    {L A B s Rmax a b : ℤ}
    (hL : 0 ≤ L) (hA : 0 ≤ A) (hB : 0 ≤ B)
    (ha : 0 ≤ a) (hab : a ≤ b)
    (hslack : L + s ≤ A + B)
    (hRmax : A + B ≤ Rmax)
    (hscalar : (b^2 - a^2) * Rmax ≤ b^2 * s) :
    b^2 * L ≤ a^2 * A + a * b * B := by
  have hbase : b^2 * L ≤ a^2 * (A + B) := by
    exact qSquared_row hL (add_nonneg hA hB) ha hab hslack hRmax hscalar
  have hba : 0 ≤ b - a := sub_nonneg.mpr hab
  have hprod : 0 ≤ a * (b - a) * B :=
    mul_nonneg (mul_nonneg ha hba) hB
  have haux : a^2 * B ≤ a * b * B := by
    nlinarith
  nlinarith

/-- The concrete scalar data used by the K19 depth-discount certificate. -/
theorem k19_q_scalar :
    let b : ℤ := 100000000000000000000
    let a : ℤ := b - 1
    let s : ℤ := 1488314
    let Rmax : ℤ :=
      (79781805157054 + 406990044804623) * 4166117961
    (b^2 - a^2) * Rmax ≤ b^2 * s := by
  norm_num

/-- The chosen depth discount is genuinely smaller than one. -/
theorem k19_q_strict :
    (100000000000000000000 - 1 : ℚ) /
      100000000000000000000 < 1 := by
  norm_num

#print axioms DepthDiscountSlackTransfer.qSquared_row
#print axioms DepthDiscountSlackTransfer.qMixed_row
#print axioms DepthDiscountSlackTransfer.k19_q_scalar
#print axioms DepthDiscountSlackTransfer.k19_q_strict

end DepthDiscountSlackTransfer

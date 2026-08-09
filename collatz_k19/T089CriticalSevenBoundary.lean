import Mathlib

/-!
# The exact 14-bit K19 critical boundary

This file formalizes the finite arithmetic layer.  The separate T089
enumeration theorem that every nonneutral image has at most six odd bits is an
upstream input and is not re-asserted here.
-/

namespace K19T089CriticalSevenBoundary

open scoped BigOperators

def cap6 : Nat := ∑ k ∈ Finset.range 7, Nat.choose 14 k
def exact7 : Nat := Nat.choose 14 7
def cap7 : Nat := ∑ k ∈ Finset.range 8, Nat.choose 14 k

theorem cap6_value : cap6 = 6476 := by native_decide
theorem exact7_value : exact7 = 3432 := by native_decide
theorem cap7_value : cap7 = 9908 := by native_decide

theorem cap6_sub_k19 :
    6476 ^ 16000 < 2 ^ 203714 := by native_decide

theorem cap7_super_k19 :
    2 ^ 203714 < 9908 ^ 16000 := by native_decide

/-- Exact integer form of the `z=1/64` tilted `1/110`-density bound. -/
theorem tilted_one_over_110_sub_k19 :
    417896 ^ 176000 < 2 ^ 3287254 := by native_decide

/-- Abstract closure statement used with the separately certified T089
nonneutral-image cap. -/
theorem capSeven_preserved
    {Word : Type*} (oddCount : Word → Nat)
    (neutral : Word → Word)
    (alternatives : Word → Set Word)
    (hneut : ∀ w, oddCount (neutral w) = oddCount w)
    (halt : ∀ w v, v ∈ alternatives w → oddCount v ≤ 6)
    {w v : Word} (hw : oddCount w ≤ 7)
    (hv : v = neutral w ∨ v ∈ alternatives w) :
    oddCount v ≤ 7 := by
  rcases hv with rfl | hv
  · simpa [hneut w] using hw
  · exact (halt w v hv).trans (by omega)

#print axioms K19T089CriticalSevenBoundary.cap6_sub_k19
#print axioms K19T089CriticalSevenBoundary.cap7_super_k19
#print axioms K19T089CriticalSevenBoundary.tilted_one_over_110_sub_k19

end K19T089CriticalSevenBoundary

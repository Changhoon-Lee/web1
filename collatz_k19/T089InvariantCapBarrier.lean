import Mathlib

/-!
# T089 invariant-cap barrier

Every nonneutral local T089 alternative used in the certified 14-bit menu has
at most six odd steps.  Hence, once the identity/neutral edge is included, the
language of blocks having at most seven odd steps is invariant under the local
relation.

The accompanying exact finite certificate verifies

* `|{u : {0,...,2^14-1} : oddCount u ≤ 6}| = 6476`,
* `|{u : {0,...,2^14-1} : oddCount u ≤ 7}| = 9908`, and
* `6476^16000 < 2^(14*14551) < 9908^16000`.

Thus a cardinality lower bound at exponent `14551/16000`, by itself, cannot
force escape from the invariant cap-seven language.  A successful Gate-B
argument must use construction-level distribution/occupation information, not
only the final K19 predecessor count.
-/

namespace T089InvariantCapBarrier

universe u
variable {α : Type u}

/-- Relational image of a set. -/
def relImage (R : α → α → Prop) (S : Set α) : Set α :=
  {v | ∃ u, u ∈ S ∧ R u v}

/-- A generic odd-count cap. -/
def cap (oddCount : α → Nat) (k : Nat) : Set α :=
  {u | oddCount u ≤ k}

/-- If every local edge is either neutral or lands at odd-count at most six,
then the cap-seven language is exactly invariant. -/
theorem capSeven_image_eq
    (R : α → α → Prop) (oddCount : α → Nat)
    (hneutral : ∀ u, R u u)
    (houtput : ∀ {u v}, R u v → u = v ∨ oddCount v ≤ 6) :
    relImage R (cap oddCount 7) = cap oddCount 7 := by
  ext v
  constructor
  · rintro ⟨u, hu, huv⟩
    rcases houtput huv with rfl | hv
    · exact hu
    · exact hv.trans (by norm_num)
  · intro hv
    exact ⟨v, hv, hneutral v⟩

/-- Exact scalar location of the K19 exponent between the two consecutive
odd-count caps.  The large powers are evaluated by the native kernel-backed
decision procedure. -/
theorem k19_rate_between_capSix_and_capSeven :
    (6476 : Nat) ^ 16000 < 2 ^ (14 * 14551) ∧
      2 ^ (14 * 14551) < (9908 : Nat) ^ 16000 := by
  native_decide

/-- Consequently the cap-seven block language has strictly larger exponential
rate than `14551/16000`, whereas cap six has strictly smaller rate. -/
theorem exact_cap_threshold_data :
    (6476 : Nat) ^ 16000 < 2 ^ 203714 ∧
      2 ^ 203714 < (9908 : Nat) ^ 16000 := by
  native_decide

#print axioms T089InvariantCapBarrier.capSeven_image_eq
#print axioms T089InvariantCapBarrier.k19_rate_between_capSix_and_capSeven

end T089InvariantCapBarrier

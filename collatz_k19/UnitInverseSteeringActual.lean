import UnitInverseSteering

namespace UnitInverseSteering

/-- An actual positive-unit inverse odd step. The equation means that one odd
shortcut step from `z`, followed by `e` even shortcut steps, reaches `y`. -/
structure ActualStep (y z e : Nat) : Prop where
  positive : 0 < z
  unit : z % 3 ≠ 0
  equation : 3 * z + 1 = 2 ^ (e + 1) * y
  potential : 2 * e + phi (z % 81) ≤ 3 + phi (y % 81)

/-- The finite residue policy lifts to a genuine positive integer inverse step
for every positive unit integer `y`. -/
theorem actual_one_step_exists {y : Nat}
    (hy : 0 < y) (hunit : y % 3 ≠ 0) :
    ∃ e z : Nat, ActualStep y z e := by
  let r : Fin 243 := ⟨y % 243, Nat.mod_lt _ (by norm_num)⟩
  have hrunit : r.val % 3 ≠ 0 := by
    simpa [r] using hunit
  obtain ⟨e, x, hrem, hxlt, hxunit, hpot⟩ := one_step_exists r hrunit
  let qa := (2 ^ (e + 1) * r.val) / 243
  let qy := y / 243
  let z := x + 81 * (qa + 2 ^ (e + 1) * qy)
  have haDecomp :
      2 ^ (e + 1) * r.val = (3 * x + 1) + 243 * qa := by
    have h := Nat.mod_add_div (2 ^ (e + 1) * r.val) 243
    dsimp [qa]
    rw [hrem] at h
    omega
  have hyDecomp : y = r.val + 243 * qy := by
    have h := Nat.mod_add_div y 243
    dsimp [r, qy]
    omega
  have hzmod81 : z % 81 = x := by
    dsimp [z]
    simp [Nat.add_mod, Nat.mul_mod, Nat.mod_eq_of_lt hxlt]
  have hymod81 : y % 81 = r.val % 81 := by
    simpa [r] using
      (Nat.mod_mod_of_dvd y (by norm_num : 81 ∣ 243)).symm
  have hzunit : z % 3 ≠ 0 := by
    have hzmod3 : z % 3 = x % 3 := by
      dsimp [z]
      simp [Nat.add_mod, Nat.mul_mod]
    simpa [hzmod3] using hxunit
  have hxne : x ≠ 0 := by
    intro hx
    subst x
    simp at hxunit
  have hzpos : 0 < z := by
    have hxpos : 0 < x := Nat.pos_of_ne_zero hxne
    dsimp [z]
    omega
  have heq : 3 * z + 1 = 2 ^ (e + 1) * y := by
    calc
      3 * z + 1 = (3 * x + 1) + 243 * (qa + 2 ^ (e + 1) * qy) := by
        dsimp [z]
        ring
      _ = 2 ^ (e + 1) * r.val + 243 * (2 ^ (e + 1) * qy) := by
        rw [haDecomp]
        ring
      _ = 2 ^ (e + 1) * (r.val + 243 * qy) := by ring
      _ = 2 ^ (e + 1) * y := by rw [← hyDecomp]
  have hpotential : 2 * e + phi (z % 81) ≤ 3 + phi (y % 81) := by
    simpa [hzmod81, hymod81] using hpot
  exact ⟨e, z, ⟨hzpos, hzunit, heq, hpotential⟩⟩

/-- A chain of actual positive-unit inverse odd steps. -/
inductive InverseChain : Nat → Nat → Nat → Nat → Prop
  | nil (y : Nat) : InverseChain y y 0 0
  | cons {y z w e R E : Nat}
      (hstep : ActualStep y z e)
      (hrest : InverseChain z w R E) :
      InverseChain y w (R + 1) (e + E)

/-- Every positive unit integer admits an actual inverse chain of any requested
number `R` of odd steps. -/
theorem inverseChain_exists {y : Nat}
    (hy : 0 < y) (hunit : y % 3 ≠ 0) (R : Nat) :
    ∃ z E : Nat, InverseChain y z R E := by
  induction R generalizing y with
  | zero =>
      exact ⟨y, 0, InverseChain.nil y⟩
  | succ R ih =>
      obtain ⟨e, z, hstep⟩ := actual_one_step_exists hy hunit
      obtain ⟨w, E, hrest⟩ := ih hstep.positive hstep.unit
      refine ⟨w, e + E, ?_⟩
      simpa [Nat.succ_eq_add_one] using InverseChain.cons hstep hrest

/-- Every actual inverse chain carries the abstract potential certificate. -/
theorem inverseChain_controlled
    {y z R E : Nat} (h : InverseChain y z R E) :
    Controlled R E (phi (y % 81)) (phi (z % 81)) := by
  induction h with
  | nil y =>
      exact Controlled.nil _
  | @cons y z w e R E hstep hrest ih =>
      exact Controlled.cons hstep.potential ih

/-- Full actual-path surface: for every positive unit target and every odd
step depth `R`, there is a positive-unit inverse path whose total shortcut
length `L = R + E` obeys `2L ≤ 5R + 10`. -/
theorem actual_path_exists_with_length
    {y : Nat} (hy : 0 < y) (hunit : y % 3 ≠ 0) (R : Nat) :
    ∃ z E : Nat,
      InverseChain y z R E ∧ 2 * (R + E) ≤ 5 * R + 10 := by
  obtain ⟨z, E, hchain⟩ := inverseChain_exists hy hunit R
  have hcontrolled := inverseChain_controlled hchain
  have hp0 : phi (y % 81) ≤ 10 := by
    exact phi_le_ten ⟨y % 81, Nat.mod_lt _ (by norm_num)⟩
  exact ⟨z, E, hchain, total_length_bound hcontrolled hp0⟩

#print axioms UnitInverseSteering.actual_one_step_exists
#print axioms UnitInverseSteering.actual_path_exists_with_length

end UnitInverseSteering

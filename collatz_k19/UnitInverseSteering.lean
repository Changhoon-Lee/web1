import Mathlib

namespace UnitInverseSteering

/-- A bounded potential on the unit residue classes modulo `81`. -/
def phi : Nat → Nat
  | 1 => 4
  | 2 => 2
  | 4 => 4
  | 5 => 5
  | 7 => 6
  | 8 => 2
  | 10 => 3
  | 11 => 3
  | 13 => 0
  | 14 => 4
  | 16 => 7
  | 17 => 1
  | 19 => 4
  | 20 => 1
  | 22 => 2
  | 23 => 7
  | 25 => 8
  | 26 => 0
  | 28 => 2
  | 29 => 3
  | 31 => 6
  | 32 => 5
  | 34 => 9
  | 35 => 5
  | 37 => 2
  | 38 => 2
  | 40 => 1
  | 41 => 6
  | 43 => 7
  | 44 => 0
  | 46 => 5
  | 47 => 1
  | 49 => 3
  | 50 => 6
  | 52 => 9
  | 53 => 2
  | 55 => 5
  | 56 => 0
  | 58 => 7
  | 59 => 4
  | 61 => 8
  | 62 => 4
  | 64 => 3
  | 65 => 4
  | 67 => 4
  | 68 => 7
  | 70 => 6
  | 71 => 0
  | 73 => 6
  | 74 => 0
  | 76 => 0
  | 77 => 8
  | 79 => 10
  | 80 => 0
  | _ => 0

/-- The certified even-step choice, indexed by a unit residue modulo `243`. -/
def policyE : Nat → Nat
  | 1 => 1
  | 2 => 0
  | 4 => 1
  | 5 => 2
  | 7 => 3
  | 8 => 0
  | 10 => 1
  | 11 => 0
  | 13 => 1
  | 14 => 2
  | 16 => 3
  | 17 => 0
  | 19 => 3
  | 20 => 0
  | 22 => 1
  | 23 => 4
  | 25 => 5
  | 26 => 0
  | 28 => 1
  | 29 => 0
  | 31 => 1
  | 32 => 2
  | 34 => 3
  | 35 => 0
  | 37 => 1
  | 38 => 2
  | 40 => 1
  | 41 => 2
  | 43 => 5
  | 44 => 0
  | 46 => 3
  | 47 => 2
  | 49 => 1
  | 50 => 4
  | 52 => 5
  | 53 => 0
  | 55 => 1
  | 56 => 0
  | 58 => 1
  | 59 => 2
  | 61 => 3
  | 62 => 0
  | 64 => 1
  | 65 => 0
  | 67 => 1
  | 68 => 2
  | 70 => 3
  | 71 => 0
  | 73 => 1
  | 74 => 0
  | 76 => 1
  | 77 => 2
  | 79 => 3
  | 80 => 0
  | 82 => 1
  | 83 => 0
  | 85 => 1
  | 86 => 4
  | 88 => 3
  | 89 => 0
  | 91 => 1
  | 92 => 2
  | 94 => 1
  | 95 => 2
  | 97 => 5
  | 98 => 0
  | 100 => 3
  | 101 => 2
  | 103 => 1
  | 104 => 4
  | 106 => 5
  | 107 => 0
  | 109 => 1
  | 110 => 0
  | 112 => 1
  | 113 => 4
  | 115 => 3
  | 116 => 0
  | 118 => 1
  | 119 => 2
  | 121 => 1
  | 122 => 2
  | 124 => 3
  | 125 => 0
  | 127 => 1
  | 128 => 0
  | 130 => 1
  | 131 => 4
  | 133 => 5
  | 134 => 0
  | 136 => 1
  | 137 => 0
  | 139 => 1
  | 140 => 2
  | 142 => 3
  | 143 => 0
  | 145 => 3
  | 146 => 0
  | 148 => 1
  | 149 => 2
  | 151 => 3
  | 152 => 0
  | 154 => 1
  | 155 => 0
  | 157 => 1
  | 158 => 2
  | 160 => 3
  | 161 => 0
  | 163 => 1
  | 164 => 0
  | 166 => 1
  | 167 => 2
  | 169 => 3
  | 170 => 0
  | 172 => 3
  | 173 => 2
  | 175 => 1
  | 176 => 2
  | 178 => 5
  | 179 => 0
  | 181 => 3
  | 182 => 0
  | 184 => 1
  | 185 => 2
  | 187 => 5
  | 188 => 0
  | 190 => 1
  | 191 => 0
  | 193 => 1
  | 194 => 4
  | 196 => 3
  | 197 => 0
  | 199 => 1
  | 200 => 2
  | 202 => 1
  | 203 => 2
  | 205 => 3
  | 206 => 0
  | 208 => 3
  | 209 => 2
  | 211 => 1
  | 212 => 4
  | 214 => 3
  | 215 => 0
  | 217 => 1
  | 218 => 0
  | 220 => 1
  | 221 => 2
  | 223 => 3
  | 224 => 0
  | 226 => 3
  | 227 => 0
  | 229 => 1
  | 230 => 2
  | 232 => 3
  | 233 => 0
  | 235 => 1
  | 236 => 0
  | 238 => 1
  | 239 => 2
  | 241 => 3
  | 242 => 0
  | _ => 0

/-- The resulting unit predecessor residue modulo `81`. -/
def policyX : Nat → Nat
  | 1 => 1
  | 2 => 1
  | 4 => 5
  | 5 => 13
  | 7 => 37
  | 8 => 5
  | 10 => 13
  | 11 => 7
  | 13 => 17
  | 14 => 37
  | 16 => 4
  | 17 => 11
  | 19 => 20
  | 20 => 13
  | 22 => 29
  | 23 => 2
  | 25 => 47
  | 26 => 17
  | 28 => 37
  | 29 => 19
  | 31 => 41
  | 32 => 4
  | 34 => 19
  | 35 => 23
  | 37 => 49
  | 38 => 20
  | 40 => 53
  | 41 => 28
  | 43 => 26
  | 44 => 29
  | 46 => 2
  | 47 => 44
  | 49 => 65
  | 50 => 47
  | 52 => 56
  | 53 => 35
  | 55 => 73
  | 56 => 37
  | 58 => 77
  | 59 => 76
  | 61 => 1
  | 62 => 41
  | 64 => 4
  | 65 => 43
  | 67 => 8
  | 68 => 19
  | 70 => 49
  | 71 => 47
  | 73 => 16
  | 74 => 49
  | 76 => 20
  | 77 => 43
  | 79 => 16
  | 80 => 53
  | 82 => 28
  | 83 => 55
  | 85 => 32
  | 86 => 26
  | 88 => 64
  | 89 => 59
  | 91 => 40
  | 92 => 2
  | 94 => 44
  | 95 => 10
  | 97 => 44
  | 98 => 65
  | 100 => 47
  | 101 => 26
  | 103 => 56
  | 104 => 56
  | 106 => 74
  | 107 => 71
  | 109 => 64
  | 110 => 73
  | 112 => 68
  | 113 => 71
  | 115 => 46
  | 116 => 77
  | 118 => 76
  | 119 => 74
  | 121 => 80
  | 122 => 1
  | 124 => 13
  | 125 => 2
  | 127 => 7
  | 128 => 4
  | 130 => 11
  | 131 => 20
  | 133 => 2
  | 134 => 8
  | 136 => 19
  | 137 => 10
  | 139 => 23
  | 140 => 49
  | 142 => 28
  | 143 => 14
  | 145 => 44
  | 146 => 16
  | 148 => 35
  | 149 => 73
  | 151 => 76
  | 152 => 20
  | 154 => 43
  | 155 => 22
  | 157 => 47
  | 158 => 16
  | 160 => 43
  | 161 => 26
  | 163 => 55
  | 164 => 28
  | 166 => 59
  | 167 => 40
  | 169 => 10
  | 170 => 32
  | 172 => 26
  | 173 => 56
  | 175 => 71
  | 176 => 64
  | 178 => 71
  | 179 => 38
  | 181 => 74
  | 182 => 40
  | 184 => 2
  | 185 => 7
  | 187 => 20
  | 188 => 44
  | 190 => 10
  | 191 => 46
  | 193 => 14
  | 194 => 44
  | 196 => 73
  | 197 => 50
  | 199 => 22
  | 200 => 47
  | 202 => 26
  | 203 => 55
  | 205 => 40
  | 206 => 56
  | 208 => 56
  | 209 => 71
  | 211 => 38
  | 212 => 74
  | 214 => 7
  | 215 => 62
  | 217 => 46
  | 218 => 64
  | 220 => 50
  | 221 => 22
  | 223 => 55
  | 224 => 68
  | 226 => 71
  | 227 => 70
  | 229 => 62
  | 230 => 46
  | 232 => 22
  | 233 => 74
  | 235 => 70
  | 236 => 76
  | 238 => 74
  | 239 => 70
  | 241 => 70
  | 242 => 80
  | _ => 0

/-- A fully computational Boolean checker for the finite policy. -/
def policyGoodBool (y : Nat) : Bool :=
  (y % 3 == 0) ||
    let e := policyE y
    let x := policyX y
    ((2 ^ (e + 1) * y) % 243 == 3 * x + 1) &&
      decide (x < 81) &&
      !(x % 3 == 0) &&
      decide (2 * e + phi x ≤ 3 + phi (y % 81))

/-- All 162 unit residue classes modulo `243` pass the exact Boolean policy
checker. Nonunit residues are accepted vacuously. -/
theorem finite_policy_valid : ∀ y : Fin 243, policyGoodBool y.val = true := by
  intro y
  fin_cases y <;> native_decide

/-- Existential surface of the finite certificate. -/
theorem one_step_exists (y : Fin 243) (hy : y.val % 3 ≠ 0) :
    ∃ e x : Nat,
      (2 ^ (e + 1) * y.val) % 243 = 3 * x + 1 ∧
      x < 81 ∧
      x % 3 ≠ 0 ∧
      2 * e + phi x ≤ 3 + phi (y.val % 81) := by
  refine ⟨policyE y.val, policyX y.val, ?_⟩
  have h := finite_policy_valid y
  simp [policyGoodBool, hy] at h
  rcases h with ⟨hABC, hD⟩
  rcases hABC with ⟨hAB, hC⟩
  rcases hAB with ⟨hA, hB⟩
  exact ⟨hA, hB, hC, hD⟩

/-- The potential is globally bounded by `10` on residues modulo `81`. -/
theorem phi_le_ten : ∀ x : Fin 81, phi x.val ≤ 10 := by
  intro x
  fin_cases x <;> native_decide

/-- Abstract chain of certified inverse odd steps. `R` is the number of odd
steps, `E` is the accumulated number of intervening even steps, and `p0,pR`
are the endpoint potentials. -/
inductive Controlled : Nat → Nat → Nat → Nat → Prop
  | nil (p : Nat) : Controlled 0 0 p p
  | cons {R E p0 p1 pR e : Nat}
      (hstep : 2 * e + p1 ≤ 3 + p0)
      (hrest : Controlled R E p1 pR) :
      Controlled (R + 1) (e + E) p0 pR

/-- Telescoping of the local inequality `2e + p_next ≤ 3 + p_current`. -/
theorem controlled_bound
    {R E p0 pR : Nat} (h : Controlled R E p0 pR) :
    2 * E + pR ≤ 3 * R + p0 := by
  induction h with
  | nil p =>
      omega
  | @cons R E p0 p1 pR e hstep hrest ih =>
      omega

/-- If the initial potential is at most `10`, then `2E ≤ 3R + 10`. -/
theorem even_cost_bound
    {R E p0 pR : Nat} (h : Controlled R E p0 pR)
    (hp0 : p0 ≤ 10) :
    2 * E ≤ 3 * R + 10 := by
  have hmain := controlled_bound h
  omega

/-- Consequently the complete parity length `L = R + E` obeys
`2L ≤ 5R + 10`, i.e. `L ≤ floor(5R/2 + 5)`. -/
theorem total_length_bound
    {R E p0 pR : Nat} (h : Controlled R E p0 pR)
    (hp0 : p0 ≤ 10) :
    2 * (R + E) ≤ 5 * R + 10 := by
  have hE := even_cost_bound h hp0
  omega

#print axioms UnitInverseSteering.finite_policy_valid
#print axioms UnitInverseSteering.controlled_bound
#print axioms UnitInverseSteering.total_length_bound

end UnitInverseSteering

import Mathlib

namespace T089Compatibility

/-- A symbolic node in the exact backward T089 discrepancy recurrence. -/
structure Node where
  C : ℤ
  D : ℤ
  a : ℤ
  r : ℕ
  x : ℤ
  y : ℤ

/-- One exact affine recurrence step, together with an explicit Bézout witness
showing that the multiplier `A` is invertible modulo the current denominator. -/
structure Step (A : ℤ) (n m : Node) : Prop where
  numerator : n.C = n.a * n.D + A * m.C
  denominator : n.D = (3 : ℤ) ^ n.r * m.D
  bezout : n.x * A + n.y * n.D = 1

/-- Adjacent nodes form a valid symbolic backward chain. -/
def GoodChain (A : ℤ) : List Node → Prop
  | [] => True
  | [_] => True
  | n :: m :: rest => Step A n m ∧ GoodChain A (m :: rest)

/-- Every denominator divides its corresponding compatibility numerator. -/
def AllDivisible : List Node → Prop
  | [] => True
  | n :: rest => n.D ∣ n.C ∧ AllDivisible rest

/-- The single top-level compatibility condition. -/
def HeadDivisible : List Node → Prop
  | [] => True
  | n :: _ => n.D ∣ n.C

/-- Explicit Bézout cancellation: if `D` divides `A*C` and `A` is invertible
modulo `D`, then `D` divides `C`. -/
theorem cancel_factor_of_bezout
    {A D C : ℤ} (x y : ℤ)
    (hbezout : x * A + y * D = 1)
    (hdiv : D ∣ A * C) :
    D ∣ C := by
  rcases hdiv with ⟨k, hk⟩
  refine ⟨x * k + y * C, ?_⟩
  calc
    C = 1 * C := by ring
    _ = (x * A + y * D) * C := by rw [hbezout]
    _ = x * (A * C) + D * (y * C) := by ring
    _ = x * (D * k) + D * (y * C) := by rw [hk]
    _ = D * (x * k + y * C) := by ring

/-- One recurrence step propagates divisibility by the current denominator to
the next compatibility numerator. -/
theorem divisibility_step
    {A C D Cnext a : ℤ} (x y : ℤ)
    (hbezout : x * A + y * D = 1)
    (hC : C = a * D + A * Cnext)
    (hdiv : D ∣ C) :
    D ∣ Cnext := by
  rcases hdiv with ⟨k, hk⟩
  apply cancel_factor_of_bezout x y hbezout
  refine ⟨k - a, ?_⟩
  calc
    A * Cnext = C - a * D := by rw [hC]; ring
    _ = D * k - a * D := by rw [hk]
    _ = D * (k - a) := by ring

/-- The head congruence propagates through every exact affine recurrence step. -/
theorem allDivisible_of_head
    {A : ℤ} {nodes : List Node}
    (hgood : GoodChain A nodes)
    (hhead : HeadDivisible nodes) :
    AllDivisible nodes := by
  cases nodes with
  | nil =>
      trivial
  | cons n rest =>
      cases rest with
      | nil =>
          change n.D ∣ n.C ∧ True
          exact ⟨hhead, trivial⟩
      | cons m rest =>
          change Step A n m ∧ GoodChain A (m :: rest) at hgood
          change n.D ∣ n.C at hhead
          change n.D ∣ n.C ∧ AllDivisible (m :: rest)
          refine ⟨hhead, ?_⟩
          apply allDivisible_of_head hgood.2
          change m.D ∣ m.C
          have hlarge : n.D ∣ m.C :=
            divisibility_step n.x n.y hgood.1.bezout hgood.1.numerator hhead
          rcases hlarge with ⟨k, hk⟩
          refine ⟨(3 : ℤ) ^ n.r * k, ?_⟩
          calc
            m.C = n.D * k := hk
            _ = ((3 : ℤ) ^ n.r * m.D) * k := by rw [hgood.1.denominator]
            _ = m.D * ((3 : ℤ) ^ n.r * k) := by ring
termination_by nodes.length

/-- All exact intermediate divisibility conditions are equivalent to the one
head compatibility congruence. This is the abstract Lean form of the T089
single-numerator collapse. -/
theorem headDivisible_iff_all
    {A : ℤ} {nodes : List Node}
    (hgood : GoodChain A nodes) :
    HeadDivisible nodes ↔ AllDivisible nodes := by
  constructor
  · exact allDivisible_of_head hgood
  · intro hall
    cases nodes with
    | nil => trivial
    | cons n rest =>
        exact hall.1

#print axioms T089Compatibility.headDivisible_iff_all

end T089Compatibility

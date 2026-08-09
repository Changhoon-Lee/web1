import Mathlib

namespace CollatzCanonicalFirstHit

universe u
variable {α : Type u}

/-- A source reaches a target under a deterministic map. -/
def Reaches (f : α → α) (source target : α) : Prop :=
  ∃ L : Nat, Function.iterate f L source = target

/-- The canonical record uses the first time at which a deterministic orbit
reaches the fixed target. -/
@[ext]
structure CanonicalHit (f : α → α) (target : α) where
  source : α
  length : Nat
  endpoint : Function.iterate f length source = target
  minimal : ∀ k : Nat, k < length → Function.iterate f k source ≠ target

/-- A deterministic orbit has at most one first-hit length for a fixed source
and target. -/
theorem firstHit_length_unique
    {f : α → α} {target : α}
    (a b : CanonicalHit f target)
    (hsource : a.source = b.source) :
    a.length = b.length := by
  by_contra hne
  have hcases : a.length < b.length ∨ b.length < a.length := by omega
  rcases hcases with hlt | hgt
  · exact b.minimal a.length hlt (by simpa [hsource] using a.endpoint)
  · exact a.minimal b.length hgt (by simpa [← hsource] using b.endpoint)

/-- The numerical source uniquely determines the complete canonical first-hit
record. Hence canonical records have no cross-length numerical collision. -/
theorem canonicalHit_ext_of_source_eq
    {f : α → α} {target : α}
    {a b : CanonicalHit f target}
    (hsource : a.source = b.source) : a = b := by
  apply CanonicalHit.ext
  · exact hsource
  · exact firstHit_length_unique a b hsource

/-- Projection from canonical records to numerical sources is injective. -/
theorem canonicalHit_source_injective
    {f : α → α} {target : α} :
    Function.Injective (fun h : CanonicalHit f target => h.source) := by
  intro a b h
  exact canonicalHit_ext_of_source_eq h

/-- Every reachable source has a canonical first-hit record, obtained by
least-number minimization. -/
noncomputable def canonicalize
    {f : α → α} {target : α}
    (x : {source : α // Reaches f source target}) :
    CanonicalHit f target := by
  refine
    { source := x.1
      length := Nat.find x.2
      endpoint := Nat.find_spec x.2
      minimal := ?_ }
  intro k hk hhit
  have hle : Nat.find x.2 ≤ k := Nat.find_min' x.2 hhit
  omega

@[simp]
theorem canonicalize_source
    {f : α → α} {target : α}
    (x : {source : α // Reaches f source target}) :
    (canonicalize x).source = x.1 := rfl

/-- Canonicalization is lossless. -/
theorem canonicalize_injective
    {f : α → α} {target : α} :
    Function.Injective (canonicalize (f := f) (target := target)) := by
  intro x y h
  apply Subtype.ext
  have hs := congrArg CanonicalHit.source h
  simpa using hs

#print axioms CollatzCanonicalFirstHit.firstHit_length_unique
#print axioms CollatzCanonicalFirstHit.canonicalHit_source_injective
#print axioms CollatzCanonicalFirstHit.canonicalize_injective

end CollatzCanonicalFirstHit

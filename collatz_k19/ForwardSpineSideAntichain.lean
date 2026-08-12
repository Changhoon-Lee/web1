import Mathlib

/-!
# Side predecessors along an injective forward spine form an antichain

A nonperiodic deterministic orbit supplies a genuinely nonlocal state that is
absent from a purely local reactivation theorem.  At each forward-spine node,
choose a predecessor different from the preceding spine node.  Distinct chosen
side predecessors cannot reach one another: if one did, deterministic iteration
would force the later side predecessor to equal the preceding spine node.

This is the canonical antichain surface needed by a bad-component occupation
argument.  The theorem is stated for an arbitrary deterministic map.
-/

namespace ForwardSpineSideAntichain

/-- Reachability under an arbitrary deterministic self-map. -/
def ReachesBy {α : Type*} (f : α → α) (source target : α) : Prop :=
  ∃ steps : Nat, f^[steps] source = target

/-- Side predecessors attached to distinct points of an injective forward orbit
are pairwise reachability-incomparable.  `side j` maps to orbit point `j+1` and
is required not to be the preceding orbit point `j`. -/
theorem side_predecessors_antichain
    {α : Type*} (f : α → α) (root : α) (side : Nat → α)
    (horbitInjective : Function.Injective
      (fun index : Nat => f^[index] root))
    (hside : ∀ index,
      f (side index) = f^[index + 1] root)
    (hoffSpine : ∀ index,
      side index ≠ f^[index] root) :
    ∀ {first second : Nat}, first ≠ second →
      ¬ ReachesBy f (side first) (side second) := by
  intro first second hne hreach
  rcases hreach with ⟨steps, hsteps⟩
  by_cases hzero : steps = 0
  · subst steps
    simp only [Function.iterate_zero_apply] at hsteps
    have horbitEq :
        f^[first + 1] root = f^[second + 1] root := by
      rw [← hside first, ← hside second, hsteps]
    have hindex := horbitInjective horbitEq
    omega
  · obtain ⟨tail, rfl⟩ := Nat.exists_eq_succ_of_ne_zero hzero
    have htail :
        f^[tail] (f (side first)) = side second := by
      simpa [Function.iterate_add_apply] using hsteps
    have hsideOrbit :
        side second = f^[tail + (first + 1)] root := by
      calc
        side second = f^[tail] (f (side first)) := htail.symm
        _ = f^[tail] (f^[first + 1] root) := by rw [hside first]
        _ = f^[tail + (first + 1)] root := by
          rw [Function.iterate_add_apply]
    have horbitEq :
        f^[tail + (first + 1) + 1] root =
          f^[second + 1] root := by
      calc
        f^[tail + (first + 1) + 1] root =
            f (f^[tail + (first + 1)] root) := by
          rw [Function.iterate_succ_apply']
        _ = f (side second) := by rw [← hsideOrbit]
        _ = f^[second + 1] root := hside second
    have hindex := horbitInjective horbitEq
    have hpreceding : tail + (first + 1) = second := by omega
    exact hoffSpine second (by simpa [hpreceding] using hsideOrbit)

#print axioms ForwardSpineSideAntichain.side_predecessors_antichain

end ForwardSpineSideAntichain

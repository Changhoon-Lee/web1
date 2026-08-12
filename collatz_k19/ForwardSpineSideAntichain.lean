import Mathlib

/-!
# Side predecessors along an injective forward spine form an antichain

A nonperiodic deterministic orbit supplies a genuinely nonlocal state that is
absent from a purely local reactivation theorem. At selected forward-spine
times, choose a predecessor different from the preceding spine node. Distinct
chosen side predecessors cannot reach one another: if one did, deterministic
iteration would force the later side predecessor to equal its preceding spine
node.

The selected-time theorem is the form needed for Collatz, where a genuine side
branch is available at infinitely many, but not necessarily all, orbit times.
-/

namespace ForwardSpineSideAntichain

/-- Reachability under an arbitrary deterministic self-map. -/
def ReachesBy {α : Type*} (f : α → α) (source target : α) : Prop :=
  ∃ steps : Nat, f^[steps] source = target

/-- Side predecessors attached to distinct selected points of an injective
forward orbit are pairwise reachability-incomparable. `side j` maps to the orbit
point at time `time j + 1` and differs from the preceding orbit point at time
`time j`. -/
theorem selected_side_predecessors_antichain
    {α : Type*} (f : α → α) (root : α)
    (time : Nat → Nat) (side : Nat → α)
    (horbitInjective : Function.Injective
      (fun index : Nat => f^[index] root))
    (htimeInjective : Function.Injective time)
    (hside : ∀ index,
      f (side index) = f^[time index + 1] root)
    (hoffSpine : ∀ index,
      side index ≠ f^[time index] root) :
    ∀ {first second : Nat}, first ≠ second →
      ¬ ReachesBy f (side first) (side second) := by
  intro first second hne hreach
  rcases hreach with ⟨steps, hsteps⟩
  by_cases hzero : steps = 0
  · subst steps
    simp only [Function.iterate_zero_apply] at hsteps
    have horbitEq :
        f^[time first + 1] root = f^[time second + 1] root := by
      rw [← hside first, ← hside second, hsteps]
    have htimeSucc := horbitInjective horbitEq
    have htime : time first = time second := by omega
    exact hne (htimeInjective htime)
  · obtain ⟨tail, rfl⟩ := Nat.exists_eq_succ_of_ne_zero hzero
    have htail :
        f^[tail] (f (side first)) = side second := by
      simpa [Function.iterate_add_apply] using hsteps
    have hsideOrbit :
        side second = f^[tail + (time first + 1)] root := by
      calc
        side second = f^[tail] (f (side first)) := htail.symm
        _ = f^[tail] (f^[time first + 1] root) := by rw [hside first]
        _ = f^[tail + (time first + 1)] root := by
          simpa only [Function.iterate_add_apply, Nat.add_assoc]
    have horbitEq :
        f^[tail + (time first + 1) + 1] root =
          f^[time second + 1] root := by
      calc
        f^[tail + (time first + 1) + 1] root =
            f (f^[tail + (time first + 1)] root) := by
          rw [Function.iterate_succ_apply']
        _ = f (side second) := by rw [← hsideOrbit]
        _ = f^[time second + 1] root := hside second
    have hindex := horbitInjective horbitEq
    have hpreceding : tail + (time first + 1) = time second := by omega
    exact hoffSpine second (by simpa [hpreceding] using hsideOrbit)

/-- Consecutive-time specialization of the selected branching-time theorem. -/
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
  exact selected_side_predecessors_antichain f root id side
    horbitInjective (fun _ _ h => h)
    (by simpa using hside) (by simpa using hoffSpine)

#print axioms ForwardSpineSideAntichain.selected_side_predecessors_antichain
#print axioms ForwardSpineSideAntichain.side_predecessors_antichain

end ForwardSpineSideAntichain

import Erdos1135.KrasikovLagarias.AdaptiveCriticalChoice

/-!
# Exact delay two for adaptive KL normal forms

Every adaptive normalizer expands only a node whose current shift is
nonnegative. The three legal child increments are `-2`, `alpha - 2`, and
`alpha - 1`, with `alpha > 0`. Hence every child of an expanded node has
shift at least `-2`. Starting from the root shift `0`, every terminal in every
full adaptive normal form lies in the exact interval `[-2,0)`.

This replaces the generic compactness delay by the sharp universal delay
`nu = 2`.
-/

namespace Erdos1135
namespace KrasikovLagarias

open AdaptiveEliminationPolicy
open AdaptiveEliminationTree
open EliminationCriticalTree
open EliminationPolicy
open EliminationResidue
open Retarded

namespace EliminationCriticalTree

mutual

/-- Every terminal label in a finite elimination tree lies above `lower`. -/
def Tree.TerminalsAbove {k : Nat} (lower : Real) : Tree k → Prop
  | .terminal label => lower ≤ label.value
  | .principalOnly _ principal => principal.TerminalsAbove lower
  | .principalMin _ principal auxiliary =>
      principal.TerminalsAbove lower ∧ auxiliary.TerminalsAbove lower

/-- Every terminal label in a nonempty auxiliary family lies above `lower`. -/
def NonemptyFamily.TerminalsAbove {k : Nat} (lower : Real) :
    NonemptyFamily k → Prop
  | .one tree => tree.TerminalsAbove lower
  | .cons tree tail =>
      tree.TerminalsAbove lower ∧ tail.TerminalsAbove lower

end

mutual

/-- Replacing an arbitrary lower shift bound by the certified terminal lower
bound `-2` preserves the upper retarded margin. -/
theorem Tree.sharpen_delay_two {k : Nat} {tree : Tree k}
    (habove : tree.TerminalsAbove (-2 : Real))
    {mu nu : Real} (hbounds : tree.toExpr.ShiftBounds mu nu) :
    tree.toExpr.ShiftBounds mu 2 := by
  cases tree with
  | terminal label =>
      exact ⟨habove, hbounds.2⟩
  | principalOnly label principal =>
      exact principal.sharpen_delay_two habove hbounds
  | principalMin label principal auxiliary =>
      exact ⟨principal.sharpen_delay_two habove.1 hbounds.1,
        auxiliary.sharpen_delay_two habove.2 hbounds.2⟩

/-- Family version of `Tree.sharpen_delay_two`. -/
theorem NonemptyFamily.sharpen_delay_two {k : Nat}
    {family : NonemptyFamily k}
    (habove : family.TerminalsAbove (-2 : Real))
    {mu nu : Real}
    (hbounds : family.toExprMinimum.ShiftBounds mu nu) :
    family.toExprMinimum.ShiftBounds mu 2 := by
  cases family with
  | one tree =>
      exact tree.sharpen_delay_two habove hbounds
  | cons tree tail =>
      exact ⟨tree.sharpen_delay_two habove.1 hbounds.1,
        tail.sharpen_delay_two habove.2 hbounds.2⟩

end

end EliminationCriticalTree

namespace AdaptiveSharpDelayTwo

/-- Every legal child of an advanced adaptive parent has shift at least `-2`.
This is the local overshoot lemma behind the sharp global delay. -/
theorem legalChild_current_ge_neg_two {k : Nat} {hk : 2 ≤ k}
    {potential : AdaptiveEliminationPolicy.ForcedPotential k hk}
    {child parent : State k}
    (edge : AdaptiveEliminationPolicy.LegalChild potential child parent) :
    (-2 : Real) ≤ child.current.value := by
  cases edge with
  | principal parent hadvanced =>
      change (-2 : Real) ≤
        (parent.current.principalChild (Nat.le_trans (by omega) hk)).value
      simp
      linarith
  | auxiliary parent hadvanced hallowed =>
      cases hallowed <;>
        simp [State.descend] <;>
        linarith [alpha_pos]

mutual

/-- Every terminal in a normalized adaptive tree lies above `-2`, provided its
root state does. -/
theorem normalized_terminalsAboveNegTwo {k : Nat} {hk : 2 ≤ k}
    {potential : AdaptiveEliminationPolicy.ForcedPotential k hk}
    {state : State k} {tree : Tree k}
    (normalized : AdaptiveEliminationTree.Normalized
      (hk := hk) potential state tree)
    (hstate : (-2 : Real) ≤ state.current.value) :
    tree.TerminalsAbove (-2 : Real) := by
  cases normalized with
  | terminal state hretarded =>
      exact hstate
  | l1 state hadvanced hrow principalNormalized auxiliaryNormalized =>
      refine ⟨normalized_terminalsAboveNegTwo principalNormalized ?_,
        normalizedFamily_terminalsAboveNegTwo auxiliaryNormalized⟩
      exact legalChild_current_ge_neg_two
        (potential := potential) (hk := hk)
        (AdaptiveEliminationPolicy.LegalChild.principal
          (potential := potential) state hadvanced)
  | l2 state hadvanced hrow principalNormalized =>
      apply normalized_terminalsAboveNegTwo principalNormalized
      exact legalChild_current_ge_neg_two
        (potential := potential) (hk := hk)
        (AdaptiveEliminationPolicy.LegalChild.principal
          (potential := potential) state hadvanced)
  | l3 state hadvanced hrow principalNormalized auxiliaryNormalized =>
      refine ⟨normalized_terminalsAboveNegTwo principalNormalized ?_,
        normalizedFamily_terminalsAboveNegTwo auxiliaryNormalized⟩
      exact legalChild_current_ge_neg_two
        (potential := potential) (hk := hk)
        (AdaptiveEliminationPolicy.LegalChild.principal
          (potential := potential) state hadvanced)

/-- Every normalized adaptive auxiliary family has all terminal shifts above
`-2`. -/
theorem normalizedFamily_terminalsAboveNegTwo {k : Nat} {hk : 2 ≤ k}
    {potential : AdaptiveEliminationPolicy.ForcedPotential k hk}
    {parent : State k} {source normalized : NonemptyFamily k}
    (familyNormalized : AdaptiveEliminationTree.NormalizedFamily
      (hk := hk) potential parent source normalized) :
    normalized.TerminalsAbove (-2 : Real) := by
  cases familyNormalized with
  | one label tree hlegal normalized =>
      exact normalized_terminalsAboveNegTwo normalized
        (legalChild_current_ge_neg_two
          (potential := potential) (hk := hk) hlegal)
  | cons label tree hlegal normalized tailNormalized =>
      exact ⟨normalized_terminalsAboveNegTwo normalized
          (legalChild_current_ge_neg_two
            (potential := potential) (hk := hk) hlegal),
        normalizedFamily_terminalsAboveNegTwo tailNormalized⟩

end

/-- The fixed adaptive full trees share one positive upper margin and the exact
universal delay `2`. -/
theorem fullTree_uniform_shiftBounds_two {k : Nat} {hk : 2 ≤ k}
    [Nonempty (PrincipalIndex k)]
    (potential : AdaptiveEliminationPolicy.ForcedPotential k hk) :
    ∃ mu : Real, 0 < mu ∧
      ∀ index : PrincipalIndex k,
        (AdaptiveCriticalChoice.fullTree potential index).toExpr.ShiftBounds
          mu 2 := by
  obtain ⟨mu, nu, hmu, hnu, hbounds⟩ :=
    AdaptiveCriticalChoice.exists_uniform_shiftBounds potential
  refine ⟨mu, hmu, ?_⟩
  intro index
  have hroot : (-2 : Real) ≤ (State.root index).current.value := by
    norm_num [State.root, Label.root, Label.value,
      EliminationShift.root, EliminationShift.value]
  exact Tree.sharpen_delay_two
    (normalized_terminalsAboveNegTwo
      (AdaptiveCriticalChoice.fullTree_normalized potential index) hroot)
    (hbounds index)

#print axioms Erdos1135.KrasikovLagarias.AdaptiveSharpDelayTwo.fullTree_uniform_shiftBounds_two

end AdaptiveSharpDelayTwo
end KrasikovLagarias
end Erdos1135

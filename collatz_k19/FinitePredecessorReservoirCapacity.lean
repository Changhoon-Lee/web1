import Mathlib.Algebra.BigOperators.Group.Finset.Sigma
import EqualDepthPredecessorAntichain

/-!
# Finite capacity of equal-depth predecessor reservoirs

Distinct equal-depth preimages of a nonperiodic target have pairwise disjoint
predecessor reservoirs.  Their exact finite counts therefore add without any
collision loss, and the total is bounded by the common numerical cutoff.
-/

namespace Erdos1135
namespace KrasikovLagarias

open Terras
open scoped BigOperators

/-- A finite family of distinct equal-depth preimages of a nonperiodic target
has pairwise disjoint full predecessor reservoirs. -/
theorem predecessorFinset_pairwiseDisjoint_of_equal_depth_family
    {targets : Finset Nat} {target depth ceiling : Nat}
    (hpreimage : ∀ u ∈ targets, accelerated^[depth] u = target)
    (hcycle : ¬ InAcceleratedCycle target) :
    (↑targets : Set Nat).PairwiseDisjoint
      (fun u => predecessorFinset u ceiling) := by
  intro first hfirst second hsecond hne
  exact predecessorFinset_disjoint_of_equal_depth_preimages
    (hpreimage first hfirst) (hpreimage second hsecond) hne hcycle

/-- Exact finite terminal capacity: the sum of all full predecessor-reservoir
cardinalities is at most the number of positive integers below the common
cutoff. -/
theorem sum_predecessorFinset_card_le_Icc_card
    {targets : Finset Nat} {target depth ceiling : Nat}
    (hpreimage : ∀ u ∈ targets, accelerated^[depth] u = target)
    (hcycle : ¬ InAcceleratedCycle target) :
    ∑ u ∈ targets, (predecessorFinset u ceiling).card ≤
      (Finset.Icc 1 ceiling).card := by
  let hpairwise : (↑targets : Set Nat).PairwiseDisjoint
      (fun u => predecessorFinset u ceiling) :=
    predecessorFinset_pairwiseDisjoint_of_equal_depth_family hpreimage hcycle
  let reservoir : Finset Nat :=
    targets.disjiUnion (fun u => predecessorFinset u ceiling) hpairwise
  have hsubset : reservoir ⊆ Finset.Icc 1 ceiling := by
    intro source hsource
    change source ∈
      targets.disjiUnion (fun u => predecessorFinset u ceiling) hpairwise at hsource
    rw [Finset.mem_disjiUnion] at hsource
    rcases hsource with ⟨u, hu, hsource⟩
    rw [mem_predecessorFinset] at hsource
    exact Finset.mem_Icc.mpr ⟨by omega, hsource.2.1⟩
  have hcard : reservoir.card ≤ (Finset.Icc 1 ceiling).card :=
    Finset.card_le_card hsubset
  change
    (targets.disjiUnion (fun u => predecessorFinset u ceiling) hpairwise).card ≤
      (Finset.Icc 1 ceiling).card at hcard
  simpa only [Finset.card_disjiUnion] using hcard

/-- Since `Icc 1 ceiling` has exactly `ceiling` elements in `Nat`, the total
predecessor count of a finite equal-depth antichain is at most `ceiling`. -/
theorem sum_predecessorCount_le_cutoff
    {targets : Finset Nat} {target depth ceiling : Nat}
    (hpreimage : ∀ u ∈ targets, accelerated^[depth] u = target)
    (hcycle : ¬ InAcceleratedCycle target) :
    ∑ u ∈ targets, predecessorCount u ceiling ≤ ceiling := by
  have h := sum_predecessorFinset_card_le_Icc_card hpreimage hcycle
  simpa [predecessorCount] using h

#print axioms Erdos1135.KrasikovLagarias.sum_predecessorCount_le_cutoff

end KrasikovLagarias
end Erdos1135

import Mathlib.Algebra.BigOperators.Group.Finset.Sigma
import Erdos1135.KrasikovLagarias.Envelope

/-!
# Terminal capacity for arbitrary reachability antichains

Equal first-hit depth is sufficient for disjoint predecessor reservoirs, but it
is not necessary.  For a deterministic map, if one source reaches two targets,
then one target lies on the forward orbit of the other.  Hence any finite family
of pairwise reachability-incomparable targets has pairwise disjoint predecessor
reservoirs, with no common-depth or nonperiodicity hypothesis.
-/

namespace Erdos1135
namespace KrasikovLagarias

open Terras
open scoped BigOperators

/-- Two nodes reached by one deterministic accelerated orbit are comparable in
forward reachability. -/
theorem reaches_or_reaches_of_common_source
    {source first second : Nat}
    (hfirst : Reaches source first)
    (hsecond : Reaches source second) :
    Reaches first second ∨ Reaches second first := by
  rcases hfirst with ⟨firstSteps, hfirst⟩
  rcases hsecond with ⟨secondSteps, hsecond⟩
  rcases le_total firstSteps secondSteps with hsteps | hsteps
  · left
    refine ⟨secondSteps - firstSteps, ?_⟩
    calc
      accelerated^[secondSteps - firstSteps] first =
          accelerated^[secondSteps - firstSteps]
            (accelerated^[firstSteps] source) := by rw [hfirst]
      _ = accelerated^[(secondSteps - firstSteps) + firstSteps] source := by
        rw [Function.iterate_add_apply]
      _ = accelerated^[secondSteps] source := by
        congr 2
        omega
      _ = second := hsecond
  · right
    refine ⟨firstSteps - secondSteps, ?_⟩
    calc
      accelerated^[firstSteps - secondSteps] second =
          accelerated^[firstSteps - secondSteps]
            (accelerated^[secondSteps] source) := by rw [hsecond]
      _ = accelerated^[(firstSteps - secondSteps) + secondSteps] source := by
        rw [Function.iterate_add_apply]
      _ = accelerated^[firstSteps] source := by
        congr 2
        omega
      _ = first := hfirst

/-- Pairwise reachability-incomparable targets have pairwise disjoint bounded
predecessor reservoirs. -/
theorem predecessorFinset_pairwiseDisjoint_of_reachability_antichain
    {targets : Finset Nat} {ceiling : Nat}
    (hantichain : ∀ {first second : Nat},
      first ∈ targets → second ∈ targets → first ≠ second →
      ¬ Reaches first second) :
    (↑targets : Set Nat).PairwiseDisjoint
      (fun target => predecessorFinset target ceiling) := by
  intro first hfirst second hsecond hne
  change Disjoint (predecessorFinset first ceiling)
    (predecessorFinset second ceiling)
  rw [Finset.disjoint_left]
  intro source hsourceFirst hsourceSecond
  rw [mem_predecessorFinset] at hsourceFirst hsourceSecond
  rcases reaches_or_reaches_of_common_source
      hsourceFirst.2.2 hsourceSecond.2.2 with hreach | hreach
  · exact (hantichain hfirst hsecond hne) hreach
  · exact (hantichain hsecond hfirst hne.symm) hreach

/-- Exact finite cardinality bound before evaluating the size of `Icc`. -/
theorem sum_predecessorFinset_card_le_Icc_card_of_reachability_antichain
    {targets : Finset Nat} {ceiling : Nat}
    (hantichain : ∀ {first second : Nat},
      first ∈ targets → second ∈ targets → first ≠ second →
      ¬ Reaches first second) :
    ∑ target ∈ targets, (predecessorFinset target ceiling).card ≤
      (Finset.Icc 1 ceiling).card := by
  let hpairwise : (↑targets : Set Nat).PairwiseDisjoint
      (fun target => predecessorFinset target ceiling) :=
    predecessorFinset_pairwiseDisjoint_of_reachability_antichain hantichain
  let reservoir : Finset Nat :=
    targets.disjiUnion (fun target => predecessorFinset target ceiling) hpairwise
  have hsubset : reservoir ⊆ Finset.Icc 1 ceiling := by
    intro source hsource
    change source ∈ targets.disjiUnion
      (fun target => predecessorFinset target ceiling) hpairwise at hsource
    rw [Finset.mem_disjiUnion] at hsource
    rcases hsource with ⟨target, htarget, hsource⟩
    rw [mem_predecessorFinset] at hsource
    exact Finset.mem_Icc.mpr ⟨by omega, hsource.2.1⟩
  have hcard : reservoir.card ≤ (Finset.Icc 1 ceiling).card :=
    Finset.card_le_card hsubset
  change
    (targets.disjiUnion (fun target => predecessorFinset target ceiling)
      hpairwise).card ≤ (Finset.Icc 1 ceiling).card at hcard
  simpa only [Finset.card_disjiUnion] using hcard

/-- Exact finite capacity for an arbitrary reachability antichain. -/
theorem sum_predecessorCount_le_cutoff_of_reachability_antichain
    {targets : Finset Nat} {ceiling : Nat}
    (hantichain : ∀ {first second : Nat},
      first ∈ targets → second ∈ targets → first ≠ second →
      ¬ Reaches first second) :
    ∑ target ∈ targets, predecessorCount target ceiling ≤ ceiling := by
  have h :=
    sum_predecessorFinset_card_le_Icc_card_of_reachability_antichain
      (ceiling := ceiling) hantichain
  simpa [predecessorCount] using h

#print axioms Erdos1135.KrasikovLagarias.reaches_or_reaches_of_common_source
#print axioms Erdos1135.KrasikovLagarias.sum_predecessorCount_le_cutoff_of_reachability_antichain

end KrasikovLagarias
end Erdos1135

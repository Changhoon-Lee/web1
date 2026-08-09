import Erdos1135.KrasikovLagarias.Envelope

/-!
# Depth-truncated bounded Collatz predecessor counts, explicit-cutoff version

The three KL source branches consume exactly two, two, and one accelerated
steps. This file records the corresponding finite-set inequalities with every
ceiling inference made explicit.
-/

namespace Erdos1135
namespace KrasikovLagarias

open Terras

/-- Reach `target` under a common orbit ceiling and within `depth` accelerated
steps. -/
def BoundedReachesWithinV2
    (source target ceiling depth : Nat) : Prop :=
  ∃ steps : Nat,
    steps ≤ depth ∧
    accelerated^[steps] source = target ∧
    ∀ index, index ≤ steps → accelerated^[index] source ≤ ceiling

namespace BoundedReachesWithinV2

theorem boundedReaches {source target ceiling depth : Nat}
    (h : BoundedReachesWithinV2 source target ceiling depth) :
    BoundedReaches source target ceiling := by
  rcases h with ⟨steps, _, htarget, hpath⟩
  exact ⟨steps, htarget, hpath⟩

theorem mono_depth {source target ceiling lower upper : Nat}
    (hdepth : lower ≤ upper)
    (h : BoundedReachesWithinV2 source target ceiling lower) :
    BoundedReachesWithinV2 source target ceiling upper := by
  rcases h with ⟨steps, hsteps, htarget, hpath⟩
  exact ⟨steps, hsteps.trans hdepth, htarget, hpath⟩

theorem trans {source middle target ceiling firstDepth secondDepth : Nat}
    (hsource : BoundedReachesWithinV2 source middle ceiling firstDepth)
    (htarget : BoundedReachesWithinV2 middle target ceiling secondDepth) :
    BoundedReachesWithinV2 source target ceiling (firstDepth + secondDepth) := by
  rcases hsource with ⟨sourceSteps, hsourceDepth, hsourceTarget, hsourcePath⟩
  rcases htarget with ⟨targetSteps, htargetDepth, htargetTarget, htargetPath⟩
  refine ⟨targetSteps + sourceSteps, by omega, ?_, ?_⟩
  · rw [Function.iterate_add_apply, hsourceTarget, htargetTarget]
  · intro index hindex
    by_cases hbefore : index ≤ sourceSteps
    · exact hsourcePath index hbefore
    · have hsourceSteps : sourceSteps ≤ index := by omega
      have hremaining : index - sourceSteps ≤ targetSteps := by omega
      calc
        accelerated^[index] source =
            accelerated^[index - sourceSteps + sourceSteps] source := by
              congr 2 <;> omega
        _ = accelerated^[index - sourceSteps]
            (accelerated^[sourceSteps] source) := by
              rw [Function.iterate_add_apply]
        _ = accelerated^[index - sourceSteps] middle := by rw [hsourceTarget]
        _ ≤ ceiling := htargetPath (index - sourceSteps) hremaining

end BoundedReachesWithinV2

private theorem within_one {source target ceiling : Nat}
    (hstep : accelerated source = target)
    (hsource : source ≤ ceiling) (htarget : target ≤ ceiling) :
    BoundedReachesWithinV2 source target ceiling 1 := by
  refine ⟨1, le_rfl, by simpa using hstep, ?_⟩
  intro index hindex
  interval_cases index
  · simpa using hsource
  · simpa [hstep] using htarget

/-- The principal `4 * target` branch costs two accelerated steps. -/
theorem four_mul_within_two_v2 {target ceiling : Nat}
    (hceiling : 4 * target ≤ ceiling) :
    BoundedReachesWithinV2 (4 * target) target ceiling 2 := by
  have htwoCeiling : 2 * target ≤ ceiling := by omega
  have htargetCeiling : target ≤ ceiling := by omega
  have hfirst : BoundedReachesWithinV2
      (4 * target) (2 * target) ceiling 1 := by
    apply within_one
    · have heven : Even (4 * target) := by
        convert even_two_mul (2 * target) using 1 <;> omega
      rw [accelerated_eq_div_two_of_even heven]
      omega
    · exact hceiling
    · exact htwoCeiling
  have hsecond : BoundedReachesWithinV2
      (2 * target) target ceiling 1 := by
    apply within_one
    · rw [accelerated_eq_div_two_of_even (even_two_mul target)]
      omega
    · exact htwoCeiling
    · exact htargetCeiling
  simpa using hfirst.trans hsecond

/-- The odd predecessor branch costs one accelerated step. -/
theorem oddPredecessor_within_one_v2 {target ceiling : Nat}
    (htarget : 0 < target) (hmod : target % 3 = 2)
    (hceiling : 2 * target ≤ ceiling) :
    BoundedReachesWithinV2 (oddPredecessor target) target ceiling 1 := by
  have hoddCeiling : oddPredecessor target ≤ ceiling :=
    (oddPredecessor_lt_two_mul htarget hmod).le.trans hceiling
  have htargetCeiling : target ≤ ceiling := by omega
  exact within_one (accelerated_oddPredecessor hmod)
    hoddCeiling htargetCeiling

/-- The doubled odd predecessor branch costs two accelerated steps. -/
theorem two_oddPredecessor_within_two_v2 {target ceiling : Nat}
    (htarget : 0 < target) (hmod : target % 3 = 2)
    (hceiling : 4 * target ≤ ceiling) :
    BoundedReachesWithinV2 (2 * oddPredecessor target) target ceiling 2 := by
  have htwoTarget : 2 * target ≤ ceiling := by omega
  have htargetCeiling : target ≤ ceiling := by omega
  have hoddLt : oddPredecessor target < 2 * target :=
    oddPredecessor_lt_two_mul htarget hmod
  have hoddCeiling : oddPredecessor target ≤ ceiling :=
    hoddLt.le.trans htwoTarget
  have htwoOddCeiling : 2 * oddPredecessor target ≤ ceiling := by
    have hthree : 3 * oddPredecessor target = 2 * target - 1 :=
      three_mul_oddPredecessor hmod
    omega
  have hfirst : BoundedReachesWithinV2
      (2 * oddPredecessor target) (oddPredecessor target) ceiling 1 := by
    apply within_one
    · rw [accelerated_eq_div_two_of_even
        (even_two_mul (oddPredecessor target))]
      omega
    · exact htwoOddCeiling
    · exact hoddCeiling
  have hsecond : BoundedReachesWithinV2
      (oddPredecessor target) target ceiling 1 := by
    exact within_one (accelerated_oddPredecessor hmod)
      hoddCeiling htargetCeiling
  simpa using hfirst.trans hsecond

noncomputable def depthBoundedPredecessorFinsetV2
    (target ceiling depth : Nat) : Finset Nat := by
  classical
  exact (Finset.Icc 1 ceiling).filter fun source =>
    BoundedReachesWithinV2 source target ceiling depth

noncomputable def depthBoundedPredecessorCountV2
    (target ceiling depth : Nat) : Nat :=
  (depthBoundedPredecessorFinsetV2 target ceiling depth).card

@[simp] theorem mem_depthBoundedPredecessorFinsetV2
    {source target ceiling depth : Nat} :
    source ∈ depthBoundedPredecessorFinsetV2 target ceiling depth ↔
      1 ≤ source ∧ source ≤ ceiling ∧
        BoundedReachesWithinV2 source target ceiling depth := by
  classical
  simp [depthBoundedPredecessorFinsetV2, and_assoc]

private theorem depthV2_subset_bounded
    (target ceiling depth : Nat) :
    depthBoundedPredecessorFinsetV2 target ceiling depth ⊆
      boundedPredecessorFinset target ceiling := by
  intro source hsource
  rw [mem_depthBoundedPredecessorFinsetV2] at hsource
  rw [mem_boundedPredecessorFinset]
  exact ⟨hsource.1, hsource.2.1, hsource.2.2.boundedReaches⟩

theorem depthBoundedPredecessorCountV2_mono_depth
    {target ceiling lower upper : Nat} (hdepth : lower ≤ upper) :
    depthBoundedPredecessorCountV2 target ceiling lower ≤
      depthBoundedPredecessorCountV2 target ceiling upper := by
  apply Finset.card_le_card
  intro source hsource
  rw [mem_depthBoundedPredecessorFinsetV2] at hsource ⊢
  exact ⟨hsource.1, hsource.2.1,
    hsource.2.2.mono_depth hdepth⟩

private theorem depthV2_subset_of_within
    {firstTarget secondTarget ceiling sourceDepth targetDepth totalDepth : Nat}
    (htarget : BoundedReachesWithinV2
      firstTarget secondTarget ceiling targetDepth)
    (hdepth : sourceDepth + targetDepth ≤ totalDepth) :
    depthBoundedPredecessorFinsetV2 firstTarget ceiling sourceDepth ⊆
      depthBoundedPredecessorFinsetV2 secondTarget ceiling totalDepth := by
  intro source hsource
  rw [mem_depthBoundedPredecessorFinsetV2] at hsource ⊢
  exact ⟨hsource.1, hsource.2.1,
    (hsource.2.2.trans htarget).mono_depth hdepth⟩

/-- D3: the principal branch costs two steps and the odd branch one. -/
theorem depthCountV2_four_odd_le
    {target ceiling budget : Nat}
    (htarget : 0 < target) (hmod : target % 3 = 2)
    (hcycle : ¬ InAcceleratedCycle target)
    (hceiling : 4 * target ≤ ceiling) (hbudget : 2 ≤ budget) :
    depthBoundedPredecessorCountV2 (4 * target) ceiling (budget - 2) +
        depthBoundedPredecessorCountV2 (oddPredecessor target) ceiling
          (budget - 1) ≤
      depthBoundedPredecessorCountV2 target ceiling budget := by
  have htwoTarget : 2 * target ≤ ceiling := by omega
  have hfourPath : BoundedReachesWithinV2
      (4 * target) target ceiling 2 := four_mul_within_two_v2 hceiling
  have hoddPath : BoundedReachesWithinV2
      (oddPredecessor target) target ceiling 1 :=
    oddPredecessor_within_one_v2 htarget hmod htwoTarget
  have hfourSubset := depthV2_subset_of_within hfourPath
    (show (budget - 2) + 2 ≤ budget by omega)
  have hoddSubset := depthV2_subset_of_within hoddPath
    (show (budget - 1) + 1 ≤ budget by omega)
  have hdisjointOrdinary :
      Disjoint (boundedPredecessorFinset (2 * target) ceiling)
        (boundedPredecessorFinset (oddPredecessor target) ceiling) :=
    boundedPredecessorFinset_disjoint_of_common_preimages
      (by rw [accelerated_eq_div_two_of_even (even_two_mul target)]; omega)
      (accelerated_oddPredecessor hmod)
      (two_mul_ne_oddPredecessor htarget hmod) hcycle
  have hfourToTwo : BoundedReaches (4 * target) (2 * target) ceiling := by
    apply boundedReaches_one
    · have heven : Even (4 * target) := by
        convert even_two_mul (2 * target) using 1 <;> omega
      rw [accelerated_eq_div_two_of_even heven]
      omega
    · exact hceiling
    · exact htwoTarget
  have hfourOrdinary :=
    boundedPredecessorFinset_subset_of_boundedReaches hfourToTwo
  have hdisjoint :
      Disjoint
        (depthBoundedPredecessorFinsetV2 (4 * target) ceiling (budget - 2))
        (depthBoundedPredecessorFinsetV2 (oddPredecessor target) ceiling
          (budget - 1)) := by
    rw [Finset.disjoint_left]
    intro source hfour hodd
    exact (Finset.disjoint_left.mp hdisjointOrdinary)
      (hfourOrdinary (depthV2_subset_bounded _ _ _ hfour))
      (depthV2_subset_bounded _ _ _ hodd)
  rw [depthBoundedPredecessorCountV2, depthBoundedPredecessorCountV2,
    ← Finset.card_union_of_disjoint hdisjoint]
  exact Finset.card_le_card (Finset.union_subset hfourSubset hoddSubset)

/-- D1: both the principal and doubled odd branches cost two steps. -/
theorem depthCountV2_four_twoOdd_le
    {target ceiling budget : Nat}
    (htarget : 0 < target) (hmod : target % 3 = 2)
    (hcycle : ¬ InAcceleratedCycle target)
    (hceiling : 4 * target ≤ ceiling) (hbudget : 2 ≤ budget) :
    depthBoundedPredecessorCountV2 (4 * target) ceiling (budget - 2) +
        depthBoundedPredecessorCountV2 (2 * oddPredecessor target) ceiling
          (budget - 2) ≤
      depthBoundedPredecessorCountV2 target ceiling budget := by
  have htwoTarget : 2 * target ≤ ceiling := by omega
  have hfourPath : BoundedReachesWithinV2
      (4 * target) target ceiling 2 := four_mul_within_two_v2 hceiling
  have htwoOddPath : BoundedReachesWithinV2
      (2 * oddPredecessor target) target ceiling 2 :=
    two_oddPredecessor_within_two_v2 htarget hmod hceiling
  have hfourSubset := depthV2_subset_of_within hfourPath
    (show (budget - 2) + 2 ≤ budget by omega)
  have htwoOddSubset := depthV2_subset_of_within htwoOddPath
    (show (budget - 2) + 2 ≤ budget by omega)
  have hdisjointOrdinary :
      Disjoint (boundedPredecessorFinset (2 * target) ceiling)
        (boundedPredecessorFinset (oddPredecessor target) ceiling) :=
    boundedPredecessorFinset_disjoint_of_common_preimages
      (by rw [accelerated_eq_div_two_of_even (even_two_mul target)]; omega)
      (accelerated_oddPredecessor hmod)
      (two_mul_ne_oddPredecessor htarget hmod) hcycle
  have hfourToTwo : BoundedReaches (4 * target) (2 * target) ceiling := by
    apply boundedReaches_one
    · have heven : Even (4 * target) := by
        convert even_two_mul (2 * target) using 1 <;> omega
      rw [accelerated_eq_div_two_of_even heven]
      omega
    · exact hceiling
    · exact htwoTarget
  have htwoOddToOdd : BoundedReaches (2 * oddPredecessor target)
      (oddPredecessor target) ceiling := by
    have hoddLt := oddPredecessor_lt_two_mul htarget hmod
    have hoddCeiling : oddPredecessor target ≤ ceiling :=
      hoddLt.le.trans htwoTarget
    have htwoOddCeiling : 2 * oddPredecessor target ≤ ceiling := by
      have hthree : 3 * oddPredecessor target = 2 * target - 1 :=
        three_mul_oddPredecessor hmod
      omega
    exact boundedReaches_one
      (by rw [accelerated_eq_div_two_of_even
        (even_two_mul (oddPredecessor target))]; omega)
      htwoOddCeiling hoddCeiling
  have hfourOrdinary :=
    boundedPredecessorFinset_subset_of_boundedReaches hfourToTwo
  have htwoOddOrdinary :=
    boundedPredecessorFinset_subset_of_boundedReaches htwoOddToOdd
  have hdisjoint :
      Disjoint
        (depthBoundedPredecessorFinsetV2 (4 * target) ceiling (budget - 2))
        (depthBoundedPredecessorFinsetV2
          (2 * oddPredecessor target) ceiling (budget - 2)) := by
    rw [Finset.disjoint_left]
    intro source hfour htwoOdd
    exact (Finset.disjoint_left.mp hdisjointOrdinary)
      (hfourOrdinary (depthV2_subset_bounded _ _ _ hfour))
      (htwoOddOrdinary (depthV2_subset_bounded _ _ _ htwoOdd))
  rw [depthBoundedPredecessorCountV2, depthBoundedPredecessorCountV2,
    ← Finset.card_union_of_disjoint hdisjoint]
  exact Finset.card_le_card (Finset.union_subset hfourSubset htwoOddSubset)

#print axioms Erdos1135.KrasikovLagarias.depthCountV2_four_odd_le
#print axioms Erdos1135.KrasikovLagarias.depthCountV2_four_twoOdd_le

end KrasikovLagarias
end Erdos1135

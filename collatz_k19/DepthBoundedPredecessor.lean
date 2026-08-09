import Erdos1135.KrasikovLagarias.Envelope

/-!
# Depth-truncated bounded Collatz predecessor counts

This module refines the bounded-orbit predecessor surface by an explicit
accelerated-step budget.  The three KL source branches consume exactly two,
two, and one accelerated steps respectively.  The resulting finite-set
inequalities are the arithmetic input needed by a depth-budgeted retarded
induction.
-/

namespace Erdos1135
namespace KrasikovLagarias

open Terras

/-- Reach `target` under a common orbit ceiling and within `depth` accelerated
steps. -/
def BoundedReachesWithin
    (source target ceiling depth : Nat) : Prop :=
  ∃ steps : Nat,
    steps ≤ depth ∧
    accelerated^[steps] source = target ∧
    ∀ index, index ≤ steps → accelerated^[index] source ≤ ceiling

namespace BoundedReachesWithin

theorem reaches {source target ceiling depth : Nat}
    (h : BoundedReachesWithin source target ceiling depth) :
    Reaches source target := by
  rcases h with ⟨steps, _, htarget, _⟩
  exact ⟨steps, htarget⟩

theorem boundedReaches {source target ceiling depth : Nat}
    (h : BoundedReachesWithin source target ceiling depth) :
    BoundedReaches source target ceiling := by
  rcases h with ⟨steps, _, htarget, hpath⟩
  exact ⟨steps, htarget, hpath⟩

theorem mono_depth {source target ceiling lower upper : Nat}
    (hdepth : lower ≤ upper)
    (h : BoundedReachesWithin source target ceiling lower) :
    BoundedReachesWithin source target ceiling upper := by
  rcases h with ⟨steps, hsteps, htarget, hpath⟩
  exact ⟨steps, hsteps.trans hdepth, htarget, hpath⟩

theorem trans {source middle target ceiling firstDepth secondDepth : Nat}
    (hsource : BoundedReachesWithin source middle ceiling firstDepth)
    (htarget : BoundedReachesWithin middle target ceiling secondDepth) :
    BoundedReachesWithin source target ceiling (firstDepth + secondDepth) := by
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

end BoundedReachesWithin

/-- One exact accelerated edge under a common ceiling. -/
theorem boundedReachesWithin_one {source target ceiling : Nat}
    (hstep : accelerated source = target)
    (hsource : source ≤ ceiling) (htarget : target ≤ ceiling) :
    BoundedReachesWithin source target ceiling 1 := by
  refine ⟨1, le_rfl, by simpa using hstep, ?_⟩
  intro index hindex
  interval_cases index
  · simpa using hsource
  · simpa [hstep] using htarget

/-- Reflexive depth-zero witness. -/
theorem boundedReachesWithin_refl {target ceiling : Nat}
    (htarget : target ≤ ceiling) :
    BoundedReachesWithin target target ceiling 0 := by
  refine ⟨0, le_rfl, rfl, ?_⟩
  intro index hindex
  have hzero : index = 0 := by omega
  simpa [hzero] using htarget

/-- The principal `4 * target` branch consumes exactly two accelerated steps. -/
theorem four_mul_boundedReachesWithin {target ceiling : Nat}
    (hceiling : 4 * target ≤ ceiling) :
    BoundedReachesWithin (4 * target) target ceiling 2 := by
  have hfirst : BoundedReachesWithin (4 * target) (2 * target) ceiling 1 := by
    apply boundedReachesWithin_one
    · have heven : Even (4 * target) := by
        convert even_two_mul (2 * target) using 1 <;> omega
      rw [accelerated_eq_div_two_of_even heven]
      omega
    · exact hceiling
    · omega
  have hsecond : BoundedReachesWithin (2 * target) target ceiling 1 := by
    apply boundedReachesWithin_one
    · rw [accelerated_eq_div_two_of_even (even_two_mul target)]
      omega
    · omega
    · omega
  simpa using hfirst.trans hsecond

/-- The odd predecessor branch consumes exactly one accelerated step. -/
theorem oddPredecessor_boundedReachesWithin {target ceiling : Nat}
    (htarget : 0 < target) (hmod : target % 3 = 2)
    (hceiling : 2 * target ≤ ceiling) :
    BoundedReachesWithin (oddPredecessor target) target ceiling 1 := by
  apply boundedReachesWithin_one (accelerated_oddPredecessor hmod)
  · exact (oddPredecessor_lt_two_mul htarget hmod).le.trans hceiling
  · omega

/-- The doubled odd predecessor branch consumes exactly two accelerated steps. -/
theorem two_oddPredecessor_boundedReachesWithin {target ceiling : Nat}
    (htarget : 0 < target) (hmod : target % 3 = 2)
    (hceiling : 4 * target ≤ ceiling) :
    BoundedReachesWithin (2 * oddPredecessor target) target ceiling 2 := by
  have hoddCeiling : oddPredecessor target ≤ ceiling :=
    (oddPredecessor_lt_two_mul htarget hmod).le.trans (by omega)
  have htwoOddCeiling : 2 * oddPredecessor target ≤ ceiling := by
    have hlt := oddPredecessor_lt_two_mul htarget hmod
    omega
  have hfirst : BoundedReachesWithin (2 * oddPredecessor target)
      (oddPredecessor target) ceiling 1 := by
    apply boundedReachesWithin_one
    · rw [accelerated_eq_div_two_of_even
        (even_two_mul (oddPredecessor target))]
      omega
    · exact htwoOddCeiling
    · exact hoddCeiling
  have hsecond : BoundedReachesWithin (oddPredecessor target)
      target ceiling 1 := by
    apply boundedReachesWithin_one (accelerated_oddPredecessor hmod)
    · exact hoddCeiling
    · omega
  simpa using hfirst.trans hsecond

/-- Positive depth-truncated bounded predecessors. -/
noncomputable def depthBoundedPredecessorFinset
    (target ceiling depth : Nat) : Finset Nat := by
  classical
  exact (Finset.Icc 1 ceiling).filter fun source =>
    BoundedReachesWithin source target ceiling depth

noncomputable def depthBoundedPredecessorCount
    (target ceiling depth : Nat) : Nat :=
  (depthBoundedPredecessorFinset target ceiling depth).card

@[simp] theorem mem_depthBoundedPredecessorFinset
    {source target ceiling depth : Nat} :
    source ∈ depthBoundedPredecessorFinset target ceiling depth ↔
      1 ≤ source ∧ source ≤ ceiling ∧
        BoundedReachesWithin source target ceiling depth := by
  classical
  simp [depthBoundedPredecessorFinset, and_assoc]

theorem depthBoundedPredecessorFinset_subset_bounded
    (target ceiling depth : Nat) :
    depthBoundedPredecessorFinset target ceiling depth ⊆
      boundedPredecessorFinset target ceiling := by
  intro source hsource
  rw [mem_depthBoundedPredecessorFinset] at hsource
  rw [mem_boundedPredecessorFinset]
  exact ⟨hsource.1, hsource.2.1, hsource.2.2.boundedReaches⟩

theorem depthBoundedPredecessorFinset_mono_depth
    {target ceiling lower upper : Nat} (hdepth : lower ≤ upper) :
    depthBoundedPredecessorFinset target ceiling lower ⊆
      depthBoundedPredecessorFinset target ceiling upper := by
  intro source hsource
  rw [mem_depthBoundedPredecessorFinset] at hsource ⊢
  exact ⟨hsource.1, hsource.2.1,
    hsource.2.2.mono_depth hdepth⟩

theorem depthBoundedPredecessorCount_mono_depth
    {target ceiling lower upper : Nat} (hdepth : lower ≤ upper) :
    depthBoundedPredecessorCount target ceiling lower ≤
      depthBoundedPredecessorCount target ceiling upper :=
  Finset.card_le_card (depthBoundedPredecessorFinset_mono_depth hdepth)

/-- Appending a fixed bounded target path consumes the corresponding amount of
depth budget. -/
theorem depthBoundedPredecessorFinset_subset_of_within
    {firstTarget secondTarget ceiling sourceDepth targetDepth totalDepth : Nat}
    (htarget : BoundedReachesWithin firstTarget secondTarget ceiling targetDepth)
    (hdepth : sourceDepth + targetDepth ≤ totalDepth) :
    depthBoundedPredecessorFinset firstTarget ceiling sourceDepth ⊆
      depthBoundedPredecessorFinset secondTarget ceiling totalDepth := by
  intro source hsource
  rw [mem_depthBoundedPredecessorFinset] at hsource ⊢
  refine ⟨hsource.1, hsource.2.1, ?_⟩
  exact (hsource.2.2.trans htarget).mono_depth hdepth

private theorem depthFinsets_disjoint_of_boundedSupersets
    {first second ceiling firstDepth secondDepth : Nat}
    (hdisjoint : Disjoint (boundedPredecessorFinset first ceiling)
      (boundedPredecessorFinset second ceiling)) :
    Disjoint (depthBoundedPredecessorFinset first ceiling firstDepth)
      (depthBoundedPredecessorFinset second ceiling secondDepth) := by
  rw [Finset.disjoint_left]
  intro source hfirst hsecond
  have hfirst' :=
    depthBoundedPredecessorFinset_subset_bounded first ceiling firstDepth hfirst
  have hsecond' :=
    depthBoundedPredecessorFinset_subset_bounded second ceiling secondDepth hsecond
  exact (Finset.disjoint_left.mp hdisjoint) hfirst' hsecond'

/-- Exact D3 depth-budgeted branch inequality: the principal branch costs two
steps and the odd branch costs one. -/
theorem depthBoundedPredecessorCount_four_odd_branches_le
    {target ceiling budget : Nat}
    (htarget : 0 < target) (hmod : target % 3 = 2)
    (hcycle : ¬ InAcceleratedCycle target)
    (hceiling : 4 * target ≤ ceiling) (hbudget : 2 ≤ budget) :
    depthBoundedPredecessorCount (4 * target) ceiling (budget - 2) +
        depthBoundedPredecessorCount (oddPredecessor target) ceiling
          (budget - 1) ≤
      depthBoundedPredecessorCount target ceiling budget := by
  have hfourPath := four_mul_boundedReachesWithin hceiling
  have hoddPath := oddPredecessor_boundedReachesWithin htarget hmod (by omega)
  have hfourSubset := depthBoundedPredecessorFinset_subset_of_within
    hfourPath (show (budget - 2) + 2 ≤ budget by omega)
  have hoddSubset := depthBoundedPredecessorFinset_subset_of_within
    hoddPath (show (budget - 1) + 1 ≤ budget by omega)
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
    · omega
  have hfourOrdinary :
      boundedPredecessorFinset (4 * target) ceiling ⊆
        boundedPredecessorFinset (2 * target) ceiling :=
    boundedPredecessorFinset_subset_of_boundedReaches hfourToTwo
  have hdisjoint :
      Disjoint
        (depthBoundedPredecessorFinset (4 * target) ceiling (budget - 2))
        (depthBoundedPredecessorFinset (oddPredecessor target) ceiling
          (budget - 1)) := by
    rw [Finset.disjoint_left]
    intro source hfour hodd
    have hfourB := depthBoundedPredecessorFinset_subset_bounded
      (4 * target) ceiling (budget - 2) hfour
    have hoddB := depthBoundedPredecessorFinset_subset_bounded
      (oddPredecessor target) ceiling (budget - 1) hodd
    exact (Finset.disjoint_left.mp hdisjointOrdinary)
      (hfourOrdinary hfourB) hoddB
  rw [depthBoundedPredecessorCount, depthBoundedPredecessorCount,
    ← Finset.card_union_of_disjoint hdisjoint]
  exact Finset.card_le_card (Finset.union_subset hfourSubset hoddSubset)

/-- Exact D1 depth-budgeted branch inequality: both the principal and doubled
odd branches cost two accelerated steps. -/
theorem depthBoundedPredecessorCount_four_twoOdd_branches_le
    {target ceiling budget : Nat}
    (htarget : 0 < target) (hmod : target % 3 = 2)
    (hcycle : ¬ InAcceleratedCycle target)
    (hceiling : 4 * target ≤ ceiling) (hbudget : 2 ≤ budget) :
    depthBoundedPredecessorCount (4 * target) ceiling (budget - 2) +
        depthBoundedPredecessorCount (2 * oddPredecessor target) ceiling
          (budget - 2) ≤
      depthBoundedPredecessorCount target ceiling budget := by
  have hfourPath := four_mul_boundedReachesWithin hceiling
  have htwoOddPath :=
    two_oddPredecessor_boundedReachesWithin htarget hmod hceiling
  have hfourSubset := depthBoundedPredecessorFinset_subset_of_within
    hfourPath (show (budget - 2) + 2 ≤ budget by omega)
  have htwoOddSubset := depthBoundedPredecessorFinset_subset_of_within
    htwoOddPath (show (budget - 2) + 2 ≤ budget by omega)
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
    · omega
  have htwoOddToOdd : BoundedReaches (2 * oddPredecessor target)
      (oddPredecessor target) ceiling := by
    apply boundedReaches_one
    · rw [accelerated_eq_div_two_of_even
        (even_two_mul (oddPredecessor target))]
      omega
    · have hlt := oddPredecessor_lt_two_mul htarget hmod
      omega
    · exact (oddPredecessor_lt_two_mul htarget hmod).le.trans (by omega)
  have hfourOrdinary :=
    boundedPredecessorFinset_subset_of_boundedReaches hfourToTwo
  have htwoOddOrdinary :=
    boundedPredecessorFinset_subset_of_boundedReaches htwoOddToOdd
  have hdisjoint :
      Disjoint
        (depthBoundedPredecessorFinset (4 * target) ceiling (budget - 2))
        (depthBoundedPredecessorFinset (2 * oddPredecessor target) ceiling
          (budget - 2)) := by
    rw [Finset.disjoint_left]
    intro source hfour htwoOdd
    have hfourB := depthBoundedPredecessorFinset_subset_bounded
      (4 * target) ceiling (budget - 2) hfour
    have htwoOddB := depthBoundedPredecessorFinset_subset_bounded
      (2 * oddPredecessor target) ceiling (budget - 2) htwoOdd
    exact (Finset.disjoint_left.mp hdisjointOrdinary)
      (hfourOrdinary hfourB) (htwoOddOrdinary htwoOddB)
  rw [depthBoundedPredecessorCount, depthBoundedPredecessorCount,
    ← Finset.card_union_of_disjoint hdisjoint]
  exact Finset.card_le_card (Finset.union_subset hfourSubset htwoOddSubset)

#print axioms Erdos1135.KrasikovLagarias.depthBoundedPredecessorCount_four_odd_branches_le
#print axioms Erdos1135.KrasikovLagarias.depthBoundedPredecessorCount_four_twoOdd_branches_le

end KrasikovLagarias
end Erdos1135

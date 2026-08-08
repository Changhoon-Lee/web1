import Erdos1135.KrasikovLagarias.Envelope

/-!
# Equal-depth Collatz preimages form an antichain over a nonperiodic target

If two distinct nodes arrive at the same nonperiodic target after the same
number of accelerated steps, no orbit can reach both nodes.  Consequently
their full and bounded predecessor sets are disjoint.  This is the exact
output-load lemma needed after collapsing a T089 labeled family to distinct
actual integer source values.
-/

namespace Erdos1135
namespace KrasikovLagarias

open Terras

/-- Two equal-depth preimages that are both visited by one deterministic orbit
must either be equal or force the common target to be periodic. -/
theorem eq_or_inAcceleratedCycle_of_reaches_equal_depth_preimages
    {source first second target depth : Nat}
    (hfirstReach : Reaches source first)
    (hsecondReach : Reaches source second)
    (hfirstTarget : accelerated^[depth] first = target)
    (hsecondTarget : accelerated^[depth] second = target) :
    first = second ∨ InAcceleratedCycle target := by
  rcases hfirstReach with ⟨firstSteps, hfirstReach⟩
  rcases hsecondReach with ⟨secondSteps, hsecondReach⟩
  have orient : ∀ {earlier later : Nat} {earlierSteps laterSteps : Nat},
      earlierSteps ≤ laterSteps →
      accelerated^[earlierSteps] source = earlier →
      accelerated^[laterSteps] source = later →
      accelerated^[depth] earlier = target →
      accelerated^[depth] later = target →
      earlier = later ∨ InAcceleratedCycle target := by
    intro earlier later earlierSteps laterSteps hsteps
      hearlier hlater hearlierTarget hlaterTarget
    let period := laterSteps - earlierSteps
    have hreach : accelerated^[period] earlier = later := by
      calc
        accelerated^[period] earlier =
            accelerated^[period] (accelerated^[earlierSteps] source) := by
              rw [hearlier]
        _ = accelerated^[period + earlierSteps] source := by
          rw [Function.iterate_add_apply]
        _ = accelerated^[laterSteps] source := by
          congr 2
          dsimp [period]
          omega
        _ = later := hlater
    by_cases hperiod : period = 0
    · left
      simpa [hperiod] using hreach
    · right
      refine ⟨period, Nat.pos_of_ne_zero hperiod, ?_⟩
      calc
        accelerated^[period] target =
            accelerated^[period] (accelerated^[depth] earlier) := by
              rw [hearlierTarget]
        _ = accelerated^[period + depth] earlier := by
          rw [Function.iterate_add_apply]
        _ = accelerated^[depth + period] earlier := by rw [add_comm]
        _ = accelerated^[depth] (accelerated^[period] earlier) := by
          rw [Function.iterate_add_apply]
        _ = accelerated^[depth] later := by rw [hreach]
        _ = target := hlaterTarget
  rcases le_total firstSteps secondSteps with hsteps | hsteps
  · exact orient hsteps hfirstReach hsecondReach hfirstTarget hsecondTarget
  · rcases orient hsteps hsecondReach hfirstReach hsecondTarget hfirstTarget with
      heq | hcycle
    · exact Or.inl heq.symm
    · exact Or.inr hcycle

/-- Distinct equal-depth preimages of a nonperiodic target have disjoint full
predecessor sets at every common cutoff. -/
theorem predecessorFinset_disjoint_of_equal_depth_preimages
    {first second target depth ceiling : Nat}
    (hfirstTarget : accelerated^[depth] first = target)
    (hsecondTarget : accelerated^[depth] second = target)
    (hne : first ≠ second)
    (hcycle : ¬ InAcceleratedCycle target) :
    Disjoint (predecessorFinset first ceiling)
      (predecessorFinset second ceiling) := by
  rw [Finset.disjoint_left]
  intro source hfirst hsecond
  rw [mem_predecessorFinset] at hfirst hsecond
  rcases eq_or_inAcceleratedCycle_of_reaches_equal_depth_preimages
      hfirst.2.2 hsecond.2.2 hfirstTarget hsecondTarget with
    heq | hperiodic
  · exact hne heq
  · exact hcycle hperiodic

/-- The same antichain statement for bounded-orbit predecessor sets. -/
theorem boundedPredecessorFinset_disjoint_of_equal_depth_preimages
    {first second target depth ceiling : Nat}
    (hfirstTarget : accelerated^[depth] first = target)
    (hsecondTarget : accelerated^[depth] second = target)
    (hne : first ≠ second)
    (hcycle : ¬ InAcceleratedCycle target) :
    Disjoint (boundedPredecessorFinset first ceiling)
      (boundedPredecessorFinset second ceiling) := by
  rw [Finset.disjoint_left]
  intro source hfirst hsecond
  rw [mem_boundedPredecessorFinset] at hfirst hsecond
  rcases eq_or_inAcceleratedCycle_of_reaches_equal_depth_preimages
      hfirst.2.2.reaches hsecond.2.2.reaches hfirstTarget hsecondTarget with
    heq | hperiodic
  · exact hne heq
  · exact hcycle hperiodic

#print axioms Erdos1135.KrasikovLagarias.predecessorFinset_disjoint_of_equal_depth_preimages
#print axioms Erdos1135.KrasikovLagarias.boundedPredecessorFinset_disjoint_of_equal_depth_preimages

end KrasikovLagarias
end Erdos1135

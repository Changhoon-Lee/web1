import DepthPhiUniformCertificate

/-!
# Maximum-sharp uniform finite depth budget

The sum-based common budget is formally convenient but unnecessarily large.
Because the principal residue type is finite and nonempty, the exact finite
maximum of the residue-dependent adaptive budgets exists.  This module replaces
the sum by that maximum and transfers the actual numerical first-hit lower
bound to the sharp common ceiling.

No claim is made here about the numerical value of the maximum.  Computing and
authenticating that value for the K19 forced potential is a finite certificate
task, separate from this kernel proof.
-/

namespace Erdos1135
namespace KrasikovLagarias
namespace DepthBudgetMaxUniformTarget

open AdaptiveCriticalChoice
open AdaptiveEliminationPolicy
open AdaptiveEliminationTree
open DepthBoundedEnvelopeV2
open DepthBoundedPredecessorV2
open DepthBudgetTarget
open DepthPhiUniformCertificate
open EliminationResidue
open EliminationSourceSystem
open Retarded

/-- Exact maximum of the residue-dependent adaptive first-hit budgets. -/
noncomputable def maximumDepthBudget
    {k : Nat} {hk : 2 ≤ k} [Nonempty (PrincipalIndex k)]
    (potential : AdaptiveEliminationPolicy.ForcedPotential k hk) : Nat :=
  (Finset.univ : Finset (PrincipalIndex k)).sup'
    Finset.univ_nonempty
    (fun index =>
      2 * AdaptiveCriticalChoice.criticalFuel potential (State.root index))

/-- Every local budget lies below the exact finite maximum. -/
theorem local_budget_le_maximum
    {k : Nat} {hk : 2 ≤ k} [Nonempty (PrincipalIndex k)]
    (potential : AdaptiveEliminationPolicy.ForcedPotential k hk)
    (index : PrincipalIndex k) :
    2 * AdaptiveCriticalChoice.criticalFuel potential (State.root index) ≤
      maximumDepthBudget potential := by
  exact Finset.le_sup'
    (s := (Finset.univ : Finset (PrincipalIndex k)))
    (f := fun current =>
      2 * AdaptiveCriticalChoice.criticalFuel potential (State.root current))
    (Finset.mem_univ index)

/-- Generic maximum-sharp uniform depth-budget theorem. -/
theorem maximum_uniform_depth_budgeted_lower_bound
    {k : Nat} {hk : 2 ≤ k}
    [Nonempty (PrincipalIndex k)]
    (potential : AdaptiveEliminationPolicy.ForcedPotential k hk)
    (values : PrincipalIndex k → Real → Nat → Real)
    (coefficients : PrincipalIndex k → Real) {lambda base : Real}
    (hone : 1 < lambda)
    (hsourceSolution : ∀ budget,
      DifferenceSystem.IsSolution (sourceSystem hk) 2
        (fun index time => values index time budget))
    (hvaluesPositive : ∀ index time budget,
      0 ≤ time → 0 < values index time budget)
    (hsourceFeasible : DifferenceSystem.IsFeasible
      (sourceSystem hk) coefficients lambda)
    (hcoefficientsPositive : ∀ index, 0 < coefficients index)
    (hvalueZero : ∀ index budget,
      base * coefficients index ≤ values index 0 budget)
    (hbudgetMonotone : ∀ index time,
      Monotone (values index time)) :
    ∀ index y, 0 ≤ y →
      base * coefficients index * lambda ^ y ≤
        values index y (maximumDepthBudget potential) := by
  intro index y hy
  have hlocal := DepthBudgetTarget.depth_budgeted_lower_bound
    potential values coefficients hone hsourceSolution hvaluesPositive
    hsourceFeasible hcoefficientsPositive hvalueZero index y hy
  exact hlocal.trans
    (hbudgetMonotone index y (local_budget_le_maximum potential index))

/-- Maximum-sharp theorem instantiated with actual numerical first-hit counts. -/
theorem maximum_uniform_actual_firstHit_lower_bound
    {k : Nat} {hk : 2 ≤ k}
    [Nonempty (PrincipalIndex k)]
    (potential : AdaptiveEliminationPolicy.ForcedPotential k hk)
    (coefficients : PrincipalIndex k → Real) {lambda base : Real}
    (hone : 1 < lambda)
    (hsourceFeasible : DifferenceSystem.IsFeasible
      (sourceSystem hk) coefficients lambda)
    (hcoefficientsPositive : ∀ index, 0 < coefficients index)
    (hbase : ∀ index, base * coefficients index ≤ 1) :
    ∀ index y, 0 ≤ y →
      base * coefficients index * lambda ^ y ≤
        depthPhiValues k index y (maximumDepthBudget potential) := by
  apply maximum_uniform_depth_budgeted_lower_bound
    potential (depthPhiValues k) coefficients hone
  · intro budget
    exact depthPhiValues_sourceSolution (hk := hk) budget
  · intro index time budget htime
    exact depthPhiValues_positive index time budget htime
  · exact hsourceFeasible
  · exact hcoefficientsPositive
  · intro index budget
    exact (hbase index).trans
      (one_le_depthPhiValues_zero index budget)
  · intro index time
    exact depthPhiValues_monotone_budget index time

#print axioms Erdos1135.KrasikovLagarias.DepthBudgetMaxUniformTarget.local_budget_le_maximum
#print axioms Erdos1135.KrasikovLagarias.DepthBudgetMaxUniformTarget.maximum_uniform_actual_firstHit_lower_bound

end DepthBudgetMaxUniformTarget
end KrasikovLagarias
end Erdos1135

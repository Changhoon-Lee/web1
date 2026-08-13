import DepthBudgetTarget

/-!
# Uniform finite depth budget for adaptive K19-style envelopes

`DepthBudgetTarget.depth_budgeted_lower_bound` supplies the same exponential
coefficient lower bound at a finite first-hit budget depending on the principal
residue.  Since the principal state space is finite, the sum of those local
budgets is one common budget.  Monotonicity in the first-hit budget then gives a
single numerical depth ceiling valid for every principal residue.

This theorem is generic.  Instantiating it with `DepthBoundedPredecessorV2`
turns an adaptive coefficient certificate into a uniform finite-depth
first-hit count theorem.  It does not by itself extract an antichain from the
cumulative depths; exact-depth or prefix-free extraction remains a separate
obligation.
-/

namespace Erdos1135
namespace KrasikovLagarias
namespace DepthBudgetUniformTarget

open AdaptiveCriticalChoice
open AdaptiveEliminationPolicy
open AdaptiveEliminationTree
open DepthBudgetTarget
open EliminationCriticalTree
open EliminationPolicy
open EliminationResidue
open EliminationSourceSystem
open Retarded

/-- A common finite budget obtained by summing all residue-dependent adaptive
budgets.  The sum is deliberately used instead of a maximum to keep the
finite-order proof elementary and robust. -/
noncomputable def uniformDepthBudget {k : Nat} {hk : 2 ≤ k}
    (potential : AdaptiveEliminationPolicy.ForcedPotential k hk) : Nat :=
  ∑ index : PrincipalIndex k,
    2 * AdaptiveCriticalChoice.criticalFuel potential (State.root index)

/-- Every residue-dependent adaptive budget is bounded by the common finite
budget. -/
theorem local_budget_le_uniform {k : Nat} {hk : 2 ≤ k}
    (potential : AdaptiveEliminationPolicy.ForcedPotential k hk)
    (index : PrincipalIndex k) :
    2 * AdaptiveCriticalChoice.criticalFuel potential (State.root index) ≤
      uniformDepthBudget potential := by
  classical
  dsimp [uniformDepthBudget]
  exact Finset.single_le_sum
    (fun _ _ => Nat.zero_le _)
    (Finset.mem_univ index)

/-- Uniform finite-depth version of the adaptive budget target theorem.

The only additional hypothesis beyond `depth_budgeted_lower_bound` is
monotonicity in the numerical first-hit budget. -/
theorem uniform_depth_budgeted_lower_bound
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
        values index y (uniformDepthBudget potential) := by
  intro index y hy
  have hlocal := DepthBudgetTarget.depth_budgeted_lower_bound
    potential values coefficients hone hsourceSolution hvaluesPositive
    hsourceFeasible hcoefficientsPositive hvalueZero index y hy
  exact hlocal.trans
    (hbudgetMonotone index y (local_budget_le_uniform potential index))

#print axioms Erdos1135.KrasikovLagarias.DepthBudgetUniformTarget.local_budget_le_uniform
#print axioms Erdos1135.KrasikovLagarias.DepthBudgetUniformTarget.uniform_depth_budgeted_lower_bound

end DepthBudgetUniformTarget
end KrasikovLagarias
end Erdos1135

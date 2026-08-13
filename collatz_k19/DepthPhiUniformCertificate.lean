import DepthBudgetUniformTarget

/-!
# Uniform finite-depth certificate for actual first-hit predecessor counts

The preceding depth-budget theorems are generic in a family of values.  This
module instantiates them with `DepthBoundedPredecessorV2.depthPhi`, whose source
system recurrence was proved directly from numerical first-hit predecessor
sets.

Given a feasible coefficient vector and a base normalization that fits below
one at time zero, one common finite budget works for every principal residue.
The conclusion is an actual count of numerical sources with bounded first-hit
depth, not merely an elimination expression.

The result is cumulative over depths at most the common budget.  Turning that
cumulative count into a prefix-free or exact-depth antichain with sufficiently
small loss remains a separate obligation.
-/

namespace Erdos1135
namespace KrasikovLagarias
namespace DepthPhiUniformCertificate

open DepthBoundedEnvelopeV2
open DepthBoundedPredecessorV2
open DepthBudgetUniformTarget
open EliminationResidue
open EliminationSourceSystem
open Terras

/-- Every depth envelope has value at least one at time zero, uniformly in the
budget and principal residue. -/
theorem one_le_depthPhiValues_zero
    {k : Nat} (index : PrincipalIndex k) (budget : Nat) :
    (1 : Real) ≤ depthPhiValues k index 0 budget := by
  have hpositive : 0 < depthPhi k (residue index) 0 budget :=
    depthPhi_positive k (residue index) 0 budget
  have honeNat : 1 ≤ depthPhi k (residue index) 0 budget := by
    omega
  exact_mod_cast honeNat

/-- The real-valued numerical depth envelope is monotone in its first-hit
budget. -/
theorem depthPhiValues_monotone_budget
    {k : Nat} (index : PrincipalIndex k) (time : Real) :
    Monotone (depthPhiValues k index time) := by
  intro first second hle
  exact_mod_cast
    (depthPhi_monotone_budget k (residue index) time hle)

/-- Actual numerical first-hit certificate with one common finite depth budget
for every principal residue. -/
theorem uniform_actual_firstHit_lower_bound
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
        depthPhiValues k index y (uniformDepthBudget potential) := by
  apply uniform_depth_budgeted_lower_bound
    potential (depthPhiValues k) coefficients hone
  · intro budget
    exact depthPhiValues_sourceSolution (hk := hk) budget
  · intro index time budget htime
    exact depthPhiValues_positive index time budget htime
  · exact hsourceFeasible
  · exact hcoefficientsPositive
  · intro index budget
    exact (hbase index).trans (one_le_depthPhiValues_zero index budget)
  · intro index time
    exact depthPhiValues_monotone_budget index time

#print axioms Erdos1135.KrasikovLagarias.DepthPhiUniformCertificate.one_le_depthPhiValues_zero
#print axioms Erdos1135.KrasikovLagarias.DepthPhiUniformCertificate.uniform_actual_firstHit_lower_bound

end DepthPhiUniformCertificate
end KrasikovLagarias
end Erdos1135

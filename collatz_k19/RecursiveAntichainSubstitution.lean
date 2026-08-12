import ReachabilityAntichainCapacity

/-!
# Recursive substitution of reachability antichains

Suppose a finite or infinite family of parent targets is a reachability
antichain.  Replace each parent by an arbitrary antichain lying in its inverse
subtree.  No equal-depth hypothesis is needed: the union of all replacement
fibres is again a reachability antichain.

The same common-source comparability also shows that a numerical child cannot
belong to the inverse subtrees of two distinct antichain parents.  Thus the
parent label is canonical rather than an additional history multiplicity.
-/

namespace Erdos1135
namespace KrasikovLagarias

open Terras

/-- A common predecessor of two members of a reachability antichain determines
those members uniquely. -/
theorem unique_antichain_parent_of_common_predecessor
    {parents : Set Nat} {child first second : Nat}
    (hantichain : ∀ {a b : Nat},
      a ∈ parents → b ∈ parents → a ≠ b → ¬ Reaches a b)
    (hfirst : first ∈ parents) (hsecond : second ∈ parents)
    (hchildFirst : Reaches child first)
    (hchildSecond : Reaches child second) :
    first = second := by
  by_contra hne
  rcases reaches_or_reaches_of_common_source hchildFirst hchildSecond with
      hforward | hbackward
  · exact (hantichain hfirst hsecond hne) hforward
  · exact (hantichain hsecond hfirst hne.symm) hbackward

/-- Fibrewise inverse-subtree substitution preserves a reachability antichain.
The replacement fibres may have different depths and different shapes. -/
theorem fibered_predecessor_union_antichain
    {parents children : Set Nat} (parent : Nat → Nat)
    (hparentMem : ∀ {x : Nat}, x ∈ children → parent x ∈ parents)
    (hchildReachesParent : ∀ {x : Nat},
      x ∈ children → Reaches x (parent x))
    (hparentAntichain : ∀ {a b : Nat},
      a ∈ parents → b ∈ parents → a ≠ b → ¬ Reaches a b)
    (hfiberAntichain : ∀ {x y : Nat},
      x ∈ children → y ∈ children → x ≠ y →
      parent x = parent y → ¬ Reaches x y) :
    ∀ {x y : Nat},
      x ∈ children → y ∈ children → x ≠ y → ¬ Reaches x y := by
  intro x y hx hy hxy hreachXY
  by_cases hsame : parent x = parent y
  · exact (hfiberAntichain hx hy hxy hsame) hreachXY
  · have hxReachesParentY : Reaches x (parent y) :=
      hreachXY.trans (hchildReachesParent hy)
    rcases reaches_or_reaches_of_common_source
        (hchildReachesParent hx) hxReachesParentY with
      hforward | hbackward
    · exact (hparentAntichain (hparentMem hx) (hparentMem hy) hsame) hforward
    · exact (hparentAntichain (hparentMem hy) (hparentMem hx) hsame.symm)
        hbackward

#print axioms Erdos1135.KrasikovLagarias.unique_antichain_parent_of_common_predecessor
#print axioms Erdos1135.KrasikovLagarias.fibered_predecessor_union_antichain

end KrasikovLagarias
end Erdos1135

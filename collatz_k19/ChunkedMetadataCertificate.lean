import Erdos1135.KrasikovLagarias.ChunkedStreamingCertificate
import Mathlib.Tactic

/-!
# Exact interval composition for adaptive-certificate metadata bounds

The public `MetadataValid` proposition contains a pointwise bound over every
entry of the decoded potential array. Directly deciding that dependent
proposition at K19 constructs an enormous `Fin` decision procedure. This module
checks the unchanged pointwise predicate through the already proved
constant-list-memory `NativeRange.allFrom`, permits exact interval composition,
and reconstructs the original public `MetadataValid` proposition.
-/

namespace Erdos1135
namespace KrasikovLagarias

namespace AdaptiveForcedPotentialCertificate

/-- Check `count` consecutive entries of the unchanged decoded potential array. -/
def metadataBoundsCheckRange (cert : AdaptiveForcedPotentialCertificate)
    (start count : Nat) : Bool :=
  NativeRange.allFrom
    (fun rawIndex =>
      if hindex : rawIndex < cert.values.size then
        decide (cert.values[rawIndex]'hindex ≤ cert.bound)
      else
        false)
    start count

/-- Consecutive metadata-bound intervals compose without re-running either
native check. -/
theorem metadataBoundsCheckRange_append
    (cert : AdaptiveForcedPotentialCertificate) (start left right : Nat)
    (hleft : cert.metadataBoundsCheckRange start left = true)
    (hright : cert.metadataBoundsCheckRange (start + left) right = true) :
    cert.metadataBoundsCheckRange start (left + right) = true :=
  NativeRange.allFrom_append _ _ _ _ hleft hright

/-- The level lower bound, exact decoded-array size, and one full composed bound
interval imply the original public `MetadataValid` proposition. -/
theorem metadataValid_of_size_and_full_bounds
    {cert : AdaptiveForcedPotentialCertificate}
    (hk : 2 ≤ cert.k)
    (hsize : cert.values.size = principalCount cert.k)
    (hbounds :
      cert.metadataBoundsCheckRange 0 (principalCount cert.k) = true) :
    cert.MetadataValid := by
  refine ⟨hk, hsize, ?_⟩
  intro index
  unfold metadataBoundsCheckRange at hbounds
  have hall :=
    (NativeRange.allFrom_eq_true_iff
      (fun rawIndex =>
        if hindex : rawIndex < cert.values.size then
          decide (cert.values[rawIndex]'hindex ≤ cert.bound)
        else
          false)
      0 (principalCount cert.k)).mp hbounds
  have hprincipal : index.val < principalCount cert.k := by
    rw [← hsize]
    exact index.isLt
  have hvalue := hall index.val hprincipal
  simpa only [Nat.zero_add, dif_pos index.isLt, decide_eq_true_eq] using hvalue

end AdaptiveForcedPotentialCertificate

end KrasikovLagarias
end Erdos1135

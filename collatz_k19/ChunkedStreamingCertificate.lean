import Erdos1135.KrasikovLagarias.StreamingCertificate
import Mathlib.Tactic

/-!
# Exact interval composition for large native certificate checks

This module permits finite-certificate and adaptive-potential row checks to be
split into consecutive intervals. Each interval can be discharged by a separate
`native_decide`. The interval proofs are then recombined in Lean into the
unchanged public `Valid` propositions.
-/

namespace Erdos1135
namespace KrasikovLagarias

namespace NativeRange

/-- Two consecutive successful range checks compose exactly. -/
theorem allFrom_append (predicate : Nat → Bool) (start left right : Nat)
    (hleft : allFrom predicate start left = true)
    (hright : allFrom predicate (start + left) right = true) :
    allFrom predicate start (left + right) = true := by
  apply (allFrom_eq_true_iff predicate start (left + right)).mpr
  intro offset hoffset
  have hleftMeaning :=
    (allFrom_eq_true_iff predicate start left).mp hleft
  have hrightMeaning :=
    (allFrom_eq_true_iff predicate (start + left) right).mp hright
  by_cases hinLeft : offset < left
  · exact hleftMeaning offset hinLeft
  · have hleftLe : left ≤ offset := Nat.le_of_not_gt hinLeft
    have hresidualLt : offset - left < right :=
      (Nat.sub_lt_iff_lt_add' hleftLe).2 hoffset
    have hvalue := hrightMeaning (offset - left) hresidualLt
    have hsum : left + (offset - left) = offset := by
      calc
        left + (offset - left) = (offset - left) + left := Nat.add_comm _ _
        _ = offset := Nat.sub_add_cancel hleftLe
    have hindex : (start + left) + (offset - left) = start + offset := by
      calc
        (start + left) + (offset - left) =
            start + (left + (offset - left)) := by
              rw [Nat.add_assoc]
        _ = start + offset := by rw [hsum]
    rw [hindex] at hvalue
    exact hvalue

end NativeRange

namespace FiniteCertificate

/-- Check one consecutive interval of certificate rows. -/
def rowsCheckRange (cert : FiniteCertificate) (start count : Nat) : Bool :=
  NativeRange.allFrom
    (fun index => decide (cert.RowValid index)) start count

/-- Exact logical meaning of one interval check. -/
theorem rowsCheckRange_eq_true_iff (cert : FiniteCertificate)
    (start count : Nat) :
    cert.rowsCheckRange start count = true ↔
      ∀ offset, offset < count → cert.RowValid (start + offset) := by
  unfold rowsCheckRange
  rw [NativeRange.allFrom_eq_true_iff]
  simp

/-- Consecutive certificate intervals compose without re-running either check. -/
theorem rowsCheckRange_append (cert : FiniteCertificate)
    (start left right : Nat)
    (hleft : cert.rowsCheckRange start left = true)
    (hright : cert.rowsCheckRange (start + left) right = true) :
    cert.rowsCheckRange start (left + right) = true :=
  NativeRange.allFrom_append _ _ _ _ hleft hright

/-- Metadata plus a full interval proof yields the original mathematical
`FiniteCertificate.Valid` proposition. -/
theorem valid_of_metadata_and_full_range {cert : FiniteCertificate}
    (hmetadata : cert.MetadataValid)
    (hrows : cert.rowsCheckRange 0 cert.principalCount = true) :
    cert.Valid := by
  refine ⟨hmetadata, ?_⟩
  intro index hindex
  have hvalue :=
    (cert.rowsCheckRange_eq_true_iff 0 cert.principalCount).mp
      hrows index hindex
  simpa using hvalue

end FiniteCertificate

namespace AdaptiveForcedPotentialCertificate

open EliminationResidue

/-- Check one consecutive raw-index interval of adaptive-potential rows. -/
def rowsCheckRange (cert : AdaptiveForcedPotentialCertificate)
    (hmetadata : cert.MetadataValid) (start count : Nat) : Bool :=
  NativeRange.allFrom
    (fun rawIndex =>
      if hindex : rawIndex < principalCount cert.k then
        decide (cert.RowValid hmetadata ⟨rawIndex, hindex⟩)
      else
        false)
    start count

/-- Consecutive adaptive-potential intervals compose exactly. -/
theorem rowsCheckRange_append (cert : AdaptiveForcedPotentialCertificate)
    (hmetadata : cert.MetadataValid) (start left right : Nat)
    (hleft : cert.rowsCheckRange hmetadata start left = true)
    (hright : cert.rowsCheckRange hmetadata (start + left) right = true) :
    cert.rowsCheckRange hmetadata start (left + right) = true :=
  NativeRange.allFrom_append _ _ _ _ hleft hright

/-- Metadata plus a full raw-index interval proof yields the unchanged public
`AdaptiveForcedPotentialCertificate.Valid` proposition. -/
theorem valid_of_metadata_and_full_range
    {cert : AdaptiveForcedPotentialCertificate}
    (hmetadata : cert.MetadataValid)
    (hrows : cert.rowsCheckRange hmetadata 0 (principalCount cert.k) = true) :
    cert.Valid := by
  refine ⟨hmetadata, ?_⟩
  intro index
  unfold rowsCheckRange at hrows
  have hall :=
    (NativeRange.allFrom_eq_true_iff
      (fun rawIndex =>
        if hindex : rawIndex < principalCount cert.k then
          decide (cert.RowValid hmetadata ⟨rawIndex, hindex⟩)
        else
          false)
      0 (principalCount cert.k)).mp hrows
  have hvalue := hall index.val index.isLt
  simpa [index.isLt] using hvalue

end AdaptiveForcedPotentialCertificate

end KrasikovLagarias
end Erdos1135

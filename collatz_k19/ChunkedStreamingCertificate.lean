import Erdos1135.KrasikovLagarias.StreamingCertificate
import Mathlib.Tactic

/-!
# Exact interval composition for large native certificate checks

This module permits a finite-certificate row check to be split into consecutive
intervals. Each interval can be discharged by a separate `native_decide`.
The interval proofs are then recombined in Lean into the unchanged
`FiniteCertificate.Valid` proposition.
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
    convert hvalue using 1 <;> omega

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

end KrasikovLagarias
end Erdos1135

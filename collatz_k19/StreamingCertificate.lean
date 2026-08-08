import Erdos1135.KrasikovLagarias.AdaptiveForcedPotentialCertificate
import Erdos1135.KrasikovLagarias.RealCertificate
import Mathlib.Tactic

/-!
# Constant-list-memory native certificate checks

The pinned public finite checkers enumerate all rows through `List.range` or
`List.finRange`. At level 19 this means an intermediate list with
`3^18 = 387420489` indices. This module supplies a structurally recursive,
tail-position range loop and proves that it has exactly the same mathematical
meaning as the existing `Valid` predicates.

Only executable enumeration is changed. Row formulas, coefficients, payload
contents, and the disclosed `native_decide` trust boundary are unchanged.
-/

namespace Erdos1135
namespace KrasikovLagarias

namespace NativeRange

/-- Check `count` consecutive natural indices beginning at `start` without
constructing `List.range count`. -/
def allFrom (predicate : Nat → Bool) (start : Nat) : Nat → Bool
  | 0 => true
  | Nat.succ count =>
      if predicate start = true then
        allFrom predicate (start + 1) count
      else
        false

/-- Exact logical meaning of `allFrom`, stated with offsets from `start`. -/
theorem allFrom_eq_true_iff (predicate : Nat → Bool) (start count : Nat) :
    allFrom predicate start count = true ↔
      ∀ offset, offset < count → predicate (start + offset) = true := by
  induction count generalizing start with
  | zero =>
      simp [allFrom]
  | succ count ih =>
      constructor
      · intro hcheck offset hoffset
        by_cases hhead : predicate start = true
        · have htail : allFrom predicate (start + 1) count = true := by
            simpa [allFrom, hhead] using hcheck
          cases offset with
          | zero =>
              simpa using hhead
          | succ offset =>
              have hoffset' : offset < count := by omega
              have hvalue :=
                (ih (start := start + 1)).mp htail offset hoffset'
              convert hvalue using 1 <;> omega
        · simp [allFrom, hhead] at hcheck
      · intro hall
        have hhead : predicate start = true := by
          simpa using hall 0 (by omega)
        have htail : allFrom predicate (start + 1) count = true := by
          apply (ih (start := start + 1)).mpr
          intro offset hoffset
          have hvalue := hall (Nat.succ offset) (by omega)
          convert hvalue using 1 <;> omega
        simpa [allFrom, hhead] using htail

end NativeRange

namespace FiniteCertificate

/-- Row component of `FiniteCertificate.check`, without materializing
`List.range cert.principalCount`. -/
def rowsCheckStreaming (cert : FiniteCertificate) : Bool :=
  NativeRange.allFrom
    (fun index => decide (cert.RowValid index)) 0 cert.principalCount

theorem rowsCheckStreaming_eq_true_iff (cert : FiniteCertificate) :
    cert.rowsCheckStreaming = true ↔
      ∀ index, index < cert.principalCount → cert.RowValid index := by
  unfold rowsCheckStreaming
  rw [NativeRange.allFrom_eq_true_iff]
  simp

/-- Full finite-certificate check with unchanged metadata and row predicates. -/
def streamingCheck (cert : FiniteCertificate) : Bool :=
  decide cert.MetadataValid && cert.rowsCheckStreaming

theorem streamingCheck_eq_true_iff (cert : FiniteCertificate) :
    cert.streamingCheck = true ↔ cert.Valid := by
  simp [streamingCheck, Valid, rowsCheckStreaming_eq_true_iff]

theorem valid_of_streamingCheck {cert : FiniteCertificate}
    (hcheck : cert.streamingCheck = true) : cert.Valid :=
  (cert.streamingCheck_eq_true_iff).mp hcheck

end FiniteCertificate

namespace AdaptiveForcedPotentialCertificate

/-- Adaptive-potential row check without materializing
`List.finRange (principalCount cert.k)`. -/
def rowsCheckStreaming (cert : AdaptiveForcedPotentialCertificate)
    (hmeta : cert.MetadataValid) : Bool :=
  NativeRange.allFrom
    (fun rawIndex =>
      if hindex : rawIndex < principalCount cert.k then
        decide (cert.RowValid hmeta ⟨rawIndex, hindex⟩)
      else
        false)
    0 (principalCount cert.k)

theorem rowsCheckStreaming_eq_true_iff
    (cert : AdaptiveForcedPotentialCertificate) (hmeta : cert.MetadataValid) :
    cert.rowsCheckStreaming hmeta = true ↔
      ∀ index : PrincipalIndex cert.k, cert.RowValid hmeta index := by
  unfold rowsCheckStreaming
  rw [NativeRange.allFrom_eq_true_iff]
  simp only [Nat.zero_add]
  constructor
  · intro hall index
    have hvalue := hall index.val index.isLt
    simpa [index.isLt] using hvalue
  · intro hall rawIndex hindex
    simp [hindex, hall ⟨rawIndex, hindex⟩]

/-- Full adaptive-potential check with the same dependent metadata proof and
`Valid` proposition as the pinned public checker. -/
def streamingCheck (cert : AdaptiveForcedPotentialCertificate) : Bool :=
  if hcheck : cert.metadataCheck = true then
    cert.rowsCheckStreaming ((cert.metadataCheck_eq_true_iff).mp hcheck)
  else
    false

theorem streamingCheck_eq_true_iff
    (cert : AdaptiveForcedPotentialCertificate) :
    cert.streamingCheck = true ↔ cert.Valid := by
  by_cases hcheck : cert.metadataCheck = true
  · constructor
    · intro hvalid
      rw [streamingCheck, dif_pos hcheck] at hvalid
      exact ⟨(cert.metadataCheck_eq_true_iff).mp hcheck,
        (cert.rowsCheckStreaming_eq_true_iff _).mp hvalid⟩
    · intro hvalid
      rw [streamingCheck, dif_pos hcheck]
      apply (cert.rowsCheckStreaming_eq_true_iff _).mpr
      simpa only [Subsingleton.elim hvalid.metadata
        ((cert.metadataCheck_eq_true_iff).mp hcheck)] using hvalid.rows
  · constructor
    · intro hvalid
      simp [streamingCheck, hcheck] at hvalid
    · intro hvalid
      exact (hcheck ((cert.metadataCheck_eq_true_iff).mpr hvalid.metadata)).elim

theorem valid_of_streamingCheck
    {cert : AdaptiveForcedPotentialCertificate}
    (hcheck : cert.streamingCheck = true) : cert.Valid :=
  (cert.streamingCheck_eq_true_iff).mp hcheck

def forcedPotential_of_streamingCheck
    {cert : AdaptiveForcedPotentialCertificate}
    (hcheck : cert.streamingCheck = true) :
    AdaptiveEliminationPolicy.ForcedPotential cert.k
      (cert.valid_of_streamingCheck hcheck).metadata.1 :=
  (cert.valid_of_streamingCheck hcheck).toForcedPotential

end AdaptiveForcedPotentialCertificate

end KrasikovLagarias
end Erdos1135

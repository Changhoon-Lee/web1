import Mathlib

namespace RankedFiberDoubleCounting

universe u v

/-- Rank each labeled edge inside its canonical-output fiber. Injectivity of
`(out, rank)` is an exact finite reverse-load certificate. -/
theorem card_edges_le_outputs_mul_load
    {Edge : Type u} {Output : Type v}
    [Fintype Edge] [Fintype Output]
    (D : Nat)
    (out : Edge → Output)
    (rank : Edge → Fin D)
    (hinj : Function.Injective (fun e => (out e, rank e))) :
    Fintype.card Edge ≤ Fintype.card Output * D := by
  have h := Fintype.card_le_of_injective (fun e => (out e, rank e)) hinj
  simpa using h

/-- Edge mass plus a ranked reverse-load certificate gives the exact canonical
image lower bound, with no further numerical collision factor. -/
theorem input_mass_le_load_mul_outputs
    {Input : Type u} {Edge : Type v} {Output : Type*}
    [Fintype Input] [Fintype Edge] [Fintype Output]
    (B D : Nat)
    (out : Edge → Output)
    (rank : Edge → Fin D)
    (hedges : B * Fintype.card Input ≤ Fintype.card Edge)
    (hinj : Function.Injective (fun e => (out e, rank e))) :
    B * Fintype.card Input ≤ D * Fintype.card Output := by
  have hload := card_edges_le_outputs_mul_load D out rank hinj
  calc
    B * Fintype.card Input ≤ Fintype.card Edge := hedges
    _ ≤ Fintype.card Output * D := hload
    _ = D * Fintype.card Output := by omega

#print axioms RankedFiberDoubleCounting.card_edges_le_outputs_mul_load
#print axioms RankedFiberDoubleCounting.input_mass_le_load_mul_outputs

end RankedFiberDoubleCounting

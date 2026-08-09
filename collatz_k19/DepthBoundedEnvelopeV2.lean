import DepthBoundedPredecessorV2

/-!
# Depth-budgeted Krasikov--Lagarias lower envelope

The ordinary KL envelope takes the infimum of bounded-orbit predecessor counts
in one residue class.  Here the count also carries a natural accelerated-step
budget.  The exact D1/D2/D3 source inequalities survive with budget costs
`2/2/1`, and the level-min identity is unchanged.
-/

namespace Erdos1135
namespace KrasikovLagarias

open Terras

noncomputable def depthBoundedPredecessorCountRealV2
    (target : Nat) (cutoff : Real) (depth : Nat) : Nat :=
  depthBoundedPredecessorCountV2 target ⌊cutoff⌋₊ depth

noncomputable def scaledDepthBoundedPredecessorCountV2
    (target : Nat) (y : Real) (depth : Nat) : Nat :=
  depthBoundedPredecessorCountRealV2 target
    ((2 : Real) ^ y * target) depth

def depthEnvelopeValueSetV2
    (k residue : Nat) (y : Real) (depth : Nat) : Set Nat :=
  {value | ∃ target : Nat,
    AdmissibleTarget k residue target ∧
      value = scaledDepthBoundedPredecessorCountV2 target y depth}

noncomputable def depthPhiV2
    (k residue : Nat) (y : Real) (depth : Nat) : Nat :=
  sInf (depthEnvelopeValueSetV2 k residue y depth)

theorem depthEnvelopeValueSetV2_congr_residue
    {k first second : Nat} (y : Real) (depth : Nat)
    (hresidue : Nat.ModEq (3 ^ k) first second) :
    depthEnvelopeValueSetV2 k first y depth =
      depthEnvelopeValueSetV2 k second y depth := by
  ext value
  simp only [depthEnvelopeValueSetV2, Set.mem_setOf_eq]
  constructor
  · rintro ⟨target, htarget, hvalue⟩
    exact ⟨target, (admissibleTarget_congr_residue hresidue).mp htarget, hvalue⟩
  · rintro ⟨target, htarget, hvalue⟩
    exact ⟨target, (admissibleTarget_congr_residue hresidue).mpr htarget, hvalue⟩

theorem depthPhiV2_congr_residue
    {k first second : Nat} (y : Real) (depth : Nat)
    (hresidue : Nat.ModEq (3 ^ k) first second) :
    depthPhiV2 k first y depth = depthPhiV2 k second y depth := by
  rw [depthPhiV2, depthPhiV2,
    depthEnvelopeValueSetV2_congr_residue y depth hresidue]

theorem depthEnvelopeValueSetV2_nonempty
    {k residue : Nat} (y : Real) (depth : Nat)
    (hclass : TargetClassNonempty k residue) :
    (depthEnvelopeValueSetV2 k residue y depth).Nonempty := by
  rcases hclass with ⟨target, htarget⟩
  exact ⟨scaledDepthBoundedPredecessorCountV2 target y depth,
    target, htarget, rfl⟩

theorem depthPhiV2_mem
    {k residue : Nat} (y : Real) (depth : Nat)
    (hclass : TargetClassNonempty k residue) :
    depthPhiV2 k residue y depth ∈
      depthEnvelopeValueSetV2 k residue y depth := by
  exact Nat.sInf_mem (depthEnvelopeValueSetV2_nonempty y depth hclass)

theorem depthPhiV2_le_scaled
    {k residue target depth : Nat} (y : Real)
    (htarget : AdmissibleTarget k residue target) :
    depthPhiV2 k residue y depth ≤
      scaledDepthBoundedPredecessorCountV2 target y depth := by
  apply Nat.sInf_le
  exact ⟨target, htarget, rfl⟩

private theorem depthFinsetV2_mono_ceiling
    {target lower upper depth : Nat} (hceiling : lower ≤ upper) :
    depthBoundedPredecessorFinsetV2 target lower depth ⊆
      depthBoundedPredecessorFinsetV2 target upper depth := by
  intro source hsource
  rw [mem_depthBoundedPredecessorFinsetV2] at hsource ⊢
  exact ⟨hsource.1, hsource.2.1.trans hceiling, hsource.2.2⟩

theorem depthBoundedPredecessorCountRealV2_mono_cutoff
    {target depth : Nat} :
    Monotone (fun cutoff : Real =>
      depthBoundedPredecessorCountRealV2 target cutoff depth) := by
  intro lower upper hcutoff
  apply Finset.card_le_card
  exact depthFinsetV2_mono_ceiling (Nat.floor_mono hcutoff)

theorem scaledDepthBoundedPredecessorCountV2_mono_time
    {target depth : Nat} :
    Monotone (fun y : Real =>
      scaledDepthBoundedPredecessorCountV2 target y depth) := by
  intro lower upper htime
  apply depthBoundedPredecessorCountRealV2_mono_cutoff
  exact mul_le_mul_of_nonneg_right
    (Real.rpow_le_rpow_of_exponent_le (by norm_num) htime)
    (Nat.cast_nonneg target)

theorem scaledDepthBoundedPredecessorCountV2_mono_depth
    {target : Nat} (y : Real) :
    Monotone (scaledDepthBoundedPredecessorCountV2 target y) := by
  intro lower upper hdepth
  exact depthBoundedPredecessorCountV2_mono_depth hdepth

private theorem target_mem_depth_finset_v2
    {target ceiling depth : Nat} (htarget : 0 < target)
    (hceiling : target ≤ ceiling) :
    target ∈ depthBoundedPredecessorFinsetV2 target ceiling depth := by
  rw [mem_depthBoundedPredecessorFinsetV2]
  refine ⟨htarget, hceiling, ?_⟩
  exact ⟨0, Nat.zero_le _, rfl, by
    intro index hindex
    have hzero : index = 0 := by omega
    simpa [hzero] using hceiling⟩

theorem scaledDepthBoundedPredecessorCountV2_pos
    {target depth : Nat} (htarget : 0 < target)
    {y : Real} (hy : 0 ≤ y) :
    0 < scaledDepthBoundedPredecessorCountV2 target y depth := by
  unfold scaledDepthBoundedPredecessorCountV2
  unfold depthBoundedPredecessorCountRealV2
  have hceiling : target ≤ ⌊(2 : Real) ^ y * target⌋₊ := by
    apply Nat.le_floor
    calc
      (target : Real) = 1 * target := by ring
      _ ≤ (2 : Real) ^ y * target := by
        gcongr
        exact Real.one_le_rpow (by norm_num) hy
  have hmem := target_mem_depth_finset_v2 htarget hceiling
  have hcard : 0 <
      (depthBoundedPredecessorFinsetV2 target
        ⌊(2 : Real) ^ y * target⌋₊ depth).card :=
    Finset.card_pos.mpr ⟨target, hmem⟩
  exact hcard

theorem depthPhiV2_pos
    {k residue depth : Nat} (hclass : TargetClassNonempty k residue)
    {y : Real} (hy : 0 ≤ y) :
    0 < depthPhiV2 k residue y depth := by
  rcases depthPhiV2_mem y depth hclass with ⟨target, htarget, hvalue⟩
  rw [hvalue]
  exact scaledDepthBoundedPredecessorCountV2_pos htarget.1 hy

theorem depthPhiV2_mono_time
    {k residue depth : Nat} (hclass : TargetClassNonempty k residue) :
    Monotone (fun y : Real => depthPhiV2 k residue y depth) := by
  intro lower upper htime
  rcases depthPhiV2_mem upper depth hclass with ⟨target, htarget, hvalue⟩
  calc
    depthPhiV2 k residue lower depth ≤
        scaledDepthBoundedPredecessorCountV2 target lower depth :=
      depthPhiV2_le_scaled lower htarget
    _ ≤ scaledDepthBoundedPredecessorCountV2 target upper depth :=
      scaledDepthBoundedPredecessorCountV2_mono_time htime
    _ = depthPhiV2 k residue upper depth := hvalue.symm

theorem depthPhiV2_mono_depth
    {k residue : Nat} (hclass : TargetClassNonempty k residue) (y : Real) :
    Monotone (depthPhiV2 k residue y) := by
  intro lower upper hdepth
  rcases depthPhiV2_mem y upper hclass with ⟨target, htarget, hvalue⟩
  calc
    depthPhiV2 k residue y lower ≤
        scaledDepthBoundedPredecessorCountV2 target y lower :=
      depthPhiV2_le_scaled y htarget
    _ ≤ scaledDepthBoundedPredecessorCountV2 target y upper :=
      scaledDepthBoundedPredecessorCountV2_mono_depth y hdepth
    _ = depthPhiV2 k residue y upper := hvalue.symm

theorem depthEnvelopeValueSetV2_level_partition
    {k residue depth : Nat} (y : Real)
    (hk : 1 ≤ k) (hresidue : residue < 3 ^ (k - 1)) :
    depthEnvelopeValueSetV2 (k - 1) residue y depth =
      (depthEnvelopeValueSetV2 k residue y depth ∪
        depthEnvelopeValueSetV2 k (residue + 3 ^ (k - 1)) y depth) ∪
      depthEnvelopeValueSetV2 k (residue + 2 * 3 ^ (k - 1)) y depth := by
  ext value
  simp only [depthEnvelopeValueSetV2, Set.mem_setOf_eq, Set.mem_union]
  constructor
  · rintro ⟨target, htarget, hvalue⟩
    rcases (admissibleTarget_level_partition hk hresidue).mp htarget with
      hfirst | hsecond | hthird
    · exact Or.inl (Or.inl ⟨target, hfirst, hvalue⟩)
    · exact Or.inl (Or.inr ⟨target, hsecond, hvalue⟩)
    · exact Or.inr ⟨target, hthird, hvalue⟩
  · rintro ((⟨target, htarget, hvalue⟩ | ⟨target, htarget, hvalue⟩) |
      ⟨target, htarget, hvalue⟩)
    · exact ⟨target, (admissibleTarget_level_partition hk hresidue).mpr
        (Or.inl htarget), hvalue⟩
    · exact ⟨target, (admissibleTarget_level_partition hk hresidue).mpr
        (Or.inr (Or.inl htarget)), hvalue⟩
    · exact ⟨target, (admissibleTarget_level_partition hk hresidue).mpr
        (Or.inr (Or.inr htarget)), hvalue⟩

private theorem natSetV2_bddBelow (values : Set Nat) : BddBelow values :=
  ⟨0, fun _ _ => Nat.zero_le _⟩

theorem depthPhiV2_level_min
    {k residue depth : Nat} (y : Real)
    (hk : 1 ≤ k) (hresidue : residue < 3 ^ (k - 1))
    (hfirst : TargetClassNonempty k residue)
    (hsecond : TargetClassNonempty k (residue + 3 ^ (k - 1)))
    (hthird : TargetClassNonempty k (residue + 2 * 3 ^ (k - 1))) :
    depthPhiV2 (k - 1) residue y depth =
      min (min (depthPhiV2 k residue y depth)
        (depthPhiV2 k (residue + 3 ^ (k - 1)) y depth))
        (depthPhiV2 k (residue + 2 * 3 ^ (k - 1)) y depth) := by
  rw [depthPhiV2,
    depthEnvelopeValueSetV2_level_partition y hk hresidue]
  rw [csInf_union (natSetV2_bddBelow _)
    (Set.Nonempty.inl (depthEnvelopeValueSetV2_nonempty y depth hfirst))
    (natSetV2_bddBelow _)
    (depthEnvelopeValueSetV2_nonempty y depth hthird)]
  rw [csInf_union (natSetV2_bddBelow _)
    (depthEnvelopeValueSetV2_nonempty y depth hfirst)
    (natSetV2_bddBelow _)
    (depthEnvelopeValueSetV2_nonempty y depth hsecond)]
  rfl

private theorem scaledDepthV2_four_le
    {target budget : Nat} {y : Real}
    (htarget : 0 < target) (hy : 2 ≤ y) (hbudget : 2 ≤ budget) :
    scaledDepthBoundedPredecessorCountV2 (4 * target) (y - 2) (budget - 2) ≤
      scaledDepthBoundedPredecessorCountV2 target y budget := by
  unfold scaledDepthBoundedPredecessorCountV2
  unfold depthBoundedPredecessorCountRealV2
  rw [scaledCutoff_four_mul]
  apply Finset.card_le_card
  intro source hsource
  rw [mem_depthBoundedPredecessorFinsetV2] at hsource ⊢
  have hpath := four_mul_within_two_v2
    (four_mul_le_scaledCutoff_floor hy)
  exact ⟨hsource.1, hsource.2.1,
    (hsource.2.2.trans hpath).mono_depth (by omega)⟩

private theorem scaledDepthV2_four_odd_le
    {target budget : Nat}
    (htarget : 0 < target) (hmod : target % 3 = 2)
    (hcycle : ¬ InAcceleratedCycle target)
    {y : Real} (hy : 2 ≤ y) (hbudget : 2 ≤ budget) :
    scaledDepthBoundedPredecessorCountV2 (4 * target) (y - 2) (budget - 2) +
        scaledDepthBoundedPredecessorCountV2 (oddPredecessor target)
          (y + alpha - 1) (budget - 1) ≤
      scaledDepthBoundedPredecessorCountV2 target y budget := by
  let commonCutoff := (2 : Real) ^ y * target
  let oddCutoff := (2 : Real) ^ (y + alpha - 1) * oddPredecessor target
  have hoddCutoff : oddCutoff ≤ commonCutoff :=
    oddPredecessor_scaledCutoff_le hmod y
  calc
    scaledDepthBoundedPredecessorCountV2 (4 * target) (y - 2) (budget - 2) +
        scaledDepthBoundedPredecessorCountV2 (oddPredecessor target)
          (y + alpha - 1) (budget - 1) =
        depthBoundedPredecessorCountV2 (4 * target) ⌊commonCutoff⌋₊
            (budget - 2) +
          depthBoundedPredecessorCountV2 (oddPredecessor target) ⌊oddCutoff⌋₊
            (budget - 1) := by
      simp only [scaledDepthBoundedPredecessorCountV2,
        depthBoundedPredecessorCountRealV2, commonCutoff, oddCutoff]
      rw [scaledCutoff_four_mul]
    _ ≤ depthBoundedPredecessorCountV2 (4 * target) ⌊commonCutoff⌋₊
            (budget - 2) +
          depthBoundedPredecessorCountV2 (oddPredecessor target) ⌊commonCutoff⌋₊
            (budget - 1) := by
      apply Nat.add_le_add_left
      apply Finset.card_le_card
      exact depthFinsetV2_mono_ceiling (Nat.floor_mono hoddCutoff)
    _ ≤ depthBoundedPredecessorCountV2 target ⌊commonCutoff⌋₊ budget := by
      exact depthCountV2_four_odd_le htarget hmod hcycle
        (four_mul_le_scaledCutoff_floor hy) hbudget
    _ = scaledDepthBoundedPredecessorCountV2 target y budget := rfl

private theorem scaledDepthV2_four_twoOdd_le
    {target budget : Nat}
    (htarget : 0 < target) (hmod : target % 3 = 2)
    (hcycle : ¬ InAcceleratedCycle target)
    {y : Real} (hy : 2 ≤ y) (hbudget : 2 ≤ budget) :
    scaledDepthBoundedPredecessorCountV2 (4 * target) (y - 2) (budget - 2) +
        scaledDepthBoundedPredecessorCountV2 (2 * oddPredecessor target)
          (y + alpha - 2) (budget - 2) ≤
      scaledDepthBoundedPredecessorCountV2 target y budget := by
  let commonCutoff := (2 : Real) ^ y * target
  let oddCutoff :=
    (2 : Real) ^ (y + alpha - 2) * (2 * oddPredecessor target)
  have hoddCutoff : oddCutoff ≤ commonCutoff :=
    two_oddPredecessor_scaledCutoff_le hmod y
  calc
    scaledDepthBoundedPredecessorCountV2 (4 * target) (y - 2) (budget - 2) +
        scaledDepthBoundedPredecessorCountV2 (2 * oddPredecessor target)
          (y + alpha - 2) (budget - 2) =
        depthBoundedPredecessorCountV2 (4 * target) ⌊commonCutoff⌋₊
            (budget - 2) +
          depthBoundedPredecessorCountV2 (2 * oddPredecessor target)
            ⌊oddCutoff⌋₊ (budget - 2) := by
      simp only [scaledDepthBoundedPredecessorCountV2,
        depthBoundedPredecessorCountRealV2, commonCutoff, oddCutoff]
      rw [scaledCutoff_four_mul]
      simp only [Nat.cast_mul, Nat.cast_ofNat]
    _ ≤ depthBoundedPredecessorCountV2 (4 * target) ⌊commonCutoff⌋₊
            (budget - 2) +
          depthBoundedPredecessorCountV2 (2 * oddPredecessor target)
            ⌊commonCutoff⌋₊ (budget - 2) := by
      apply Nat.add_le_add_left
      apply Finset.card_le_card
      exact depthFinsetV2_mono_ceiling (Nat.floor_mono hoddCutoff)
    _ ≤ depthBoundedPredecessorCountV2 target ⌊commonCutoff⌋₊ budget := by
      exact depthCountV2_four_twoOdd_le htarget hmod hcycle
        (four_mul_le_scaledCutoff_floor hy) hbudget
    _ = scaledDepthBoundedPredecessorCountV2 target y budget := rfl

/-- Depth-budgeted D2. -/
theorem depthPhiV2_four_mul_le
    {k residue budget : Nat}
    (hclass : TargetClassNonempty k residue)
    {y : Real} (hy : 2 ≤ y) (hbudget : 2 ≤ budget) :
    depthPhiV2 k (4 * residue) (y - 2) (budget - 2) ≤
      depthPhiV2 k residue y budget := by
  rcases depthPhiV2_mem y budget hclass with ⟨target, htarget, hvalue⟩
  have hfourTarget : AdmissibleTarget k (4 * residue) (4 * target) := by
    exact ⟨Nat.mul_pos (by norm_num) htarget.1, htarget.2.1.mul_left 4,
      four_mul_not_inAcceleratedCycle htarget.2.2⟩
  calc
    depthPhiV2 k (4 * residue) (y - 2) (budget - 2) ≤
        scaledDepthBoundedPredecessorCountV2
          (4 * target) (y - 2) (budget - 2) :=
      depthPhiV2_le_scaled (y - 2) hfourTarget
    _ ≤ scaledDepthBoundedPredecessorCountV2 target y budget :=
      scaledDepthV2_four_le htarget.1 hy hbudget
    _ = depthPhiV2 k residue y budget := hvalue.symm

/-- Depth-budgeted D1. -/
theorem depthPhiV2_difference_d1
    {k residue budget : Nat} (hk : 2 ≤ k)
    (hresidue : residue % 9 = 2)
    (hclass : TargetClassNonempty k residue)
    {y : Real} (hy : 2 ≤ y) (hbudget : 2 ≤ budget) :
    depthPhiV2 k (4 * residue) (y - 2) (budget - 2) +
        depthPhiV2 (k - 1) ((4 * residue - 2) / 3)
          (y + alpha - 2) (budget - 2) ≤
      depthPhiV2 k residue y budget := by
  have hresidueThree : residue % 3 = 2 := by omega
  rcases depthPhiV2_mem y budget hclass with ⟨target, htarget, hvalue⟩
  have htargetMod := mod_three_eq_of_admissibleTarget (by omega)
    hresidueThree htarget
  have hfourTarget : AdmissibleTarget k (4 * residue) (4 * target) :=
    ⟨Nat.mul_pos (by norm_num) htarget.1, htarget.2.1.mul_left 4,
      four_mul_not_inAcceleratedCycle htarget.2.2⟩
  have hoddTarget := admissibleTarget_two_oddPredecessor
    (by omega : 1 ≤ k) hresidueThree htarget
  rw [← two_oddPredecessor_eq_div hresidueThree]
  calc
    depthPhiV2 k (4 * residue) (y - 2) (budget - 2) +
        depthPhiV2 (k - 1) (2 * oddPredecessor residue)
          (y + alpha - 2) (budget - 2) ≤
        scaledDepthBoundedPredecessorCountV2
            (4 * target) (y - 2) (budget - 2) +
          scaledDepthBoundedPredecessorCountV2
            (2 * oddPredecessor target) (y + alpha - 2) (budget - 2) :=
      Nat.add_le_add
        (depthPhiV2_le_scaled (y - 2) hfourTarget)
        (depthPhiV2_le_scaled (y + alpha - 2) hoddTarget)
    _ ≤ scaledDepthBoundedPredecessorCountV2 target y budget :=
      scaledDepthV2_four_twoOdd_le htarget.1 htargetMod htarget.2.2 hy hbudget
    _ = depthPhiV2 k residue y budget := hvalue.symm

/-- Depth-budgeted D3. -/
theorem depthPhiV2_difference_d3
    {k residue budget : Nat} (hk : 2 ≤ k)
    (hresidue : residue % 9 = 8)
    (hclass : TargetClassNonempty k residue)
    {y : Real} (hy : 2 ≤ y) (hbudget : 2 ≤ budget) :
    depthPhiV2 k (4 * residue) (y - 2) (budget - 2) +
        depthPhiV2 (k - 1) ((2 * residue - 1) / 3)
          (y + alpha - 1) (budget - 1) ≤
      depthPhiV2 k residue y budget := by
  have hresidueThree : residue % 3 = 2 := by omega
  rcases depthPhiV2_mem y budget hclass with ⟨target, htarget, hvalue⟩
  have htargetMod := mod_three_eq_of_admissibleTarget (by omega)
    hresidueThree htarget
  have hfourTarget : AdmissibleTarget k (4 * residue) (4 * target) :=
    ⟨Nat.mul_pos (by norm_num) htarget.1, htarget.2.1.mul_left 4,
      four_mul_not_inAcceleratedCycle htarget.2.2⟩
  have hoddTarget := admissibleTarget_oddPredecessor
    (by omega : 1 ≤ k) hresidueThree htarget
  rw [← oddPredecessor_eq_div hresidueThree]
  calc
    depthPhiV2 k (4 * residue) (y - 2) (budget - 2) +
        depthPhiV2 (k - 1) (oddPredecessor residue)
          (y + alpha - 1) (budget - 1) ≤
        scaledDepthBoundedPredecessorCountV2
            (4 * target) (y - 2) (budget - 2) +
          scaledDepthBoundedPredecessorCountV2
            (oddPredecessor target) (y + alpha - 1) (budget - 1) :=
      Nat.add_le_add
        (depthPhiV2_le_scaled (y - 2) hfourTarget)
        (depthPhiV2_le_scaled (y + alpha - 1) hoddTarget)
    _ ≤ scaledDepthBoundedPredecessorCountV2 target y budget :=
      scaledDepthV2_four_odd_le htarget.1 htargetMod htarget.2.2 hy hbudget
    _ = depthPhiV2 k residue y budget := hvalue.symm

#print axioms Erdos1135.KrasikovLagarias.depthPhiV2_level_min
#print axioms Erdos1135.KrasikovLagarias.depthPhiV2_difference_d1
#print axioms Erdos1135.KrasikovLagarias.depthPhiV2_four_mul_le
#print axioms Erdos1135.KrasikovLagarias.depthPhiV2_difference_d3

end KrasikovLagarias
end Erdos1135

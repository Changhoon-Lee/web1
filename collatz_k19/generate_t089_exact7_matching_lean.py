#!/usr/bin/env python3
"""Generate a compact Lean/native_decide certificate from the matching TSV."""
from __future__ import annotations
from collections import defaultdict
from pathlib import Path
import argparse


def lean_array(xs) -> str:
    return "#[" + ",".join(map(str, xs)) + "]"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("matching", type=Path)
    ap.add_argument("output", type=Path)
    args = ap.parse_args()

    rows = []
    for line in args.matching.read_text().splitlines()[1:]:
        u, v, d = map(int, line.split("\t"))
        rows.append((u, v, d))
    by_u = defaultdict(list)
    by_v = defaultdict(list)
    for u, v, d in rows:
        by_u[u].append((v, d))
        by_v[v].append(u)
    us = sorted(by_u)
    assert len(us) == 3432
    assert all(len(by_u[u]) == 2 for u in us)
    rank = {}
    for v in sorted(by_v):
        assert len(by_v[v]) <= 5
        for r, u in enumerate(sorted(by_v[v])):
            rank[(u, v)] = r

    v0=[]; v1=[]; d0=[]; d1=[]; r0=[]; r1=[]
    for u in us:
        pair=sorted(by_u[u])
        (a,da),(b,db)=pair
        v0.append(a); d0.append(da); r0.append(rank[(u,a)])
        v1.append(b); d1.append(db); r1.append(rank[(u,b)])

    content=f'''import Mathlib

namespace T089Exact7Capacity5

/-- Chronological 14-bit shortcut-Collatz affine constant. -/
def wordConstant (w : Nat) : Nat :=
  (List.range 14).foldl
    (fun k j => if Nat.testBit w j then 3 * k + 2 ^ j else k) 0

def popcount14 (w : Nat) : Nat :=
  (List.range 14).foldl
    (fun n j => if Nat.testBit w j then n + 1 else n) 0

def original : Array Nat := {lean_array(us)}
def alt0 : Array Nat := {lean_array(v0)}
def alt1 : Array Nat := {lean_array(v1)}
def intercept0 : Array Int := {lean_array(d0)}
def intercept1 : Array Int := {lean_array(d1)}
def rank0 : Array Nat := {lean_array(r0)}
def rank1 : Array Nat := {lean_array(r1)}

def rowGood (i : Nat) : Bool :=
  let u := original[i]!
  let v0 := alt0[i]!
  let v1 := alt1[i]!
  let d0 := intercept0[i]!
  let d1 := intercept1[i]!
  let r0 := rank0[i]!
  let r1 := rank1[i]!
  decide (popcount14 u = 7) &&
  decide (popcount14 v0 = 6) &&
  decide (popcount14 v1 = 6) &&
  decide (((wordConstant u : Int) - wordConstant v0) = 729 * d0) &&
  decide (((wordConstant u : Int) - wordConstant v1) = 729 * d1) &&
  decide (d0 % 3 ≠ 0) && decide (d1 % 3 ≠ 0) &&
  decide (d0 ≤ 331) && decide (d1 ≤ 331) &&
  decide (r0 < 5) && decide (r1 < 5) &&
  decide (v0 ≠ v1)

def coverageGood : Bool :=
  (List.range 16384).all fun w =>
    decide (popcount14 w = 7) == original.contains w

def keys : List Nat :=
  (List.range original.size).flatMap fun i =>
    [5 * alt0[i]! + rank0[i]!, 5 * alt1[i]! + rank1[i]!]

def certificateGood : Bool :=
  decide (original.size = 3432) &&
  decide (alt0.size = original.size) &&
  decide (alt1.size = original.size) &&
  decide (intercept0.size = original.size) &&
  decide (intercept1.size = original.size) &&
  decide (rank0.size = original.size) &&
  decide (rank1.size = original.size) &&
  decide original.toList.Nodup &&
  decide keys.Nodup &&
  coverageGood &&
  (List.range original.size).all rowGood

/-- All 3,432 critical words have two legal unit alternatives, and `(word,rank)`
with rank below five is injective. -/
theorem capacityFiveCertificate : certificateGood = true := by
  native_decide

/-- Exact integer form of
`(7/2)^(-1449/16000) + 4/35 > 1`. -/
theorem criticalMarginInteger :
    7 ^ 1449 * 31 ^ 16000 < 2 ^ 1449 * 35 ^ 16000 := by
  native_decide

#print axioms T089Exact7Capacity5.capacityFiveCertificate
#print axioms T089Exact7Capacity5.criticalMarginInteger

end T089Exact7Capacity5
'''
    args.output.write_text(content)
    print(f"LEAN_ROWS={{len(us)}}")
    print("LEAN_CERTIFICATE_GENERATED=PASS")


if __name__ == "__main__":
    main()

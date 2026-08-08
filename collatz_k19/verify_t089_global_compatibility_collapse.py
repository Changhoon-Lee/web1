#!/usr/bin/env python3
"""Exact regression for the T089 single-numerator and terminal-fiber theorems."""
from __future__ import annotations
from itertools import product
import random


def backward_integral(A: int, a: tuple[int, ...], r: tuple[int, ...]):
    d = [0] * (len(a) + 1)
    for i in range(len(a) - 1, -1, -1):
        den = 3 ** r[i]
        if d[i + 1] % den != 0:
            return False, d
        d[i] = a[i] + A * (d[i + 1] // den)
    return True, d


def numerator(A: int, a: tuple[int, ...], r: tuple[int, ...]):
    n = len(a)
    if n == 0:
        return 0, 1, 0
    prefix = [0] * n
    for j in range(1, n):
        prefix[j] = prefix[j - 1] + r[j - 1]
    R = prefix[-1]
    C = sum(A**j * a[j] * 3 ** (R - prefix[j]) for j in range(n))
    return C, 3**R, R


def forward_mod(A: int, a: tuple[int, ...], r: tuple[int, ...], K: int, x: int) -> int:
    mod = 3**K
    invA = pow(A, -1, mod)
    for ai, ri in zip(a, r):
        x = (3**ri * invA * (x - ai)) % mod
    return x


def main() -> None:
    integer_cases = 0
    A = 16
    for n in range(1, 6):
        for r in product(range(3), repeat=n):
            for a in product(range(-3, 4), repeat=n):
                ok, d = backward_integral(A, a, r)
                C, D, _ = numerator(A, a, r)
                assert ok == (C % D == 0)
                if ok:
                    assert d[0] == C // D
                integer_cases += 1

    fiber_cases = 0
    for K in range(1, 7):
        mod = 3**K
        for n in range(1, 4):
            for r in product(range(3), repeat=n):
                S = sum(r)
                for a in product(range(-2, 3), repeat=n):
                    pre = [x for x in range(mod) if forward_mod(A, a, r, K, x) == 0]
                    assert len(pre) in (0, 3 ** min(S, K))
                    if K >= S:
                        C, D, _ = numerator(A, a, r)
                        compatible = C % D == 0
                        assert bool(pre) == compatible
                        if compatible:
                            x0 = C // D
                            assert len(pre) == 3**S
                            alias_mod = 3 ** (K - S)
                            assert all((x - x0) % alias_mod == 0 for x in pre)
                    fiber_cases += 1

    rng = random.Random(20260808)
    random_cases = 100_000
    A = 2**14
    for _ in range(random_cases):
        n = rng.randint(1, 16)
        a = tuple(rng.randint(-(10**18), 10**18) for _ in range(n))
        r = tuple(rng.randint(0, 6) for _ in range(n))
        ok, d = backward_integral(A, a, r)
        C, D, _ = numerator(A, a, r)
        assert ok == (C % D == 0)
        if ok:
            assert d[0] == C // D

    print("T089_GLOBAL_COMPATIBILITY_COLLAPSE=PASS")
    print(f"INTEGER_EXHAUSTIVE_CASES={integer_cases}")
    print(f"MODULAR_FIBER_EXHAUSTIVE_CASES={fiber_cases}")
    print(f"LARGE_INTEGER_RANDOM_CASES={random_cases}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Exact 14-bit enumeration of critical seven-odd alternatives.

For a chronological shortcut-Collatz parity word w of length 14, K(w) is
defined by

    2^14 T_w(n) = 3^r n + K(w).

For an original word u with seven odd steps and a candidate word v with six
odd steps, the same-target affine source relation is

    V = 3 M + (K(u)-K(v))/3^6.

The candidate is integer-compatible iff 3^6 divides the difference, and the
alternative source is a 3-adic unit iff the quotient is not divisible by 3.
"""
from collections import defaultdict
from math import comb

L = 14
POW3_6 = 3**6
POW3_7 = 3**7


def word_constant(word: int) -> int:
    k = 0
    for j in range(L):
        if (word >> j) & 1:
            k = 3 * k + (1 << j)
    return k


def replay_constant(word: int) -> tuple[int, int]:
    # Independent closed-form replay: sum 2^j 3^(number of later odd bits).
    ones_after = 0
    k = 0
    for j in range(L - 1, -1, -1):
        if (word >> j) & 1:
            k += (1 << j) * (3**ones_after)
            ones_after += 1
    return k, ones_after


def main() -> None:
    by_mod_729: dict[int, list[tuple[int, int]]] = defaultdict(list)
    constants: dict[int, int] = {}
    for w in range(1 << L):
        k = word_constant(w)
        k2, r2 = replay_constant(w)
        assert k == k2
        assert r2 == w.bit_count()
        constants[w] = k
        if w.bit_count() == 6:
            by_mod_729[k % POW3_6].append((w, k))

    histogram: dict[int, int] = defaultdict(int)
    min_count = 10**9
    max_count = 0
    min_words: list[int] = []
    total_pairs = 0
    min_d = None
    max_d = None
    max_abs_d = 0
    valuation_failures = 0

    for u in range(1 << L):
        if u.bit_count() != 7:
            continue
        ku = constants[u]
        matches: list[tuple[int, int]] = []
        for v, kv in by_mod_729[ku % POW3_6]:
            diff = ku - kv
            assert diff % POW3_6 == 0
            d = diff // POW3_6
            if d % 3 == 0:
                continue
            # Exact valuation-six compatibility.
            assert diff % POW3_7 != 0
            matches.append((v, d))
            min_d = d if min_d is None else min(min_d, d)
            max_d = d if max_d is None else max(max_d, d)
            max_abs_d = max(max_abs_d, abs(d))
        count = len(matches)
        histogram[count] += 1
        total_pairs += count
        if count < min_count:
            min_count = count
            min_words = [u]
        elif count == min_count:
            min_words.append(u)
        max_count = max(max_count, count)

        # Independent modular characterization.
        direct = sum(
            1
            for v, kv in by_mod_729[ku % POW3_6]
            if (ku - kv) % POW3_6 == 0 and (ku - kv) % POW3_7 != 0
        )
        if direct != count:
            valuation_failures += 1

    assert sum(histogram.values()) == comb(14, 7) == 3432
    assert sum(len(vs) for vs in by_mod_729.values()) == comb(14, 6) == 3003
    assert valuation_failures == 0

    print(f"L={L}")
    print(f"EXACT6_WORDS={comb(14,6)}")
    print(f"EXACT7_WORDS={comb(14,7)}")
    print(f"TOTAL_UNIT_ALTERNATIVE_PAIRS={total_pairs}")
    print(f"MIN_UNIT_ALTERNATIVES={min_count}")
    print(f"MAX_UNIT_ALTERNATIVES={max_count}")
    print(f"MIN_ATTAINERS={len(min_words)}")
    print("MIN_ATTAINER_WORDS=" + ",".join(map(str, min_words[:64])))
    print(f"MIN_INTERCEPT={min_d}")
    print(f"MAX_INTERCEPT={max_d}")
    print(f"MAX_ABS_INTERCEPT={max_abs_d}")
    print(f"VALUATION_REPLAY_FAILURES={valuation_failures}")
    for count in sorted(histogram):
        print(f"HIST_{count}={histogram[count]}")

    if min_count >= 2:
        print("EVERY_EXACT7_HAS_TWO_UNIT_EXACT6_ALTERNATIVES=PASS")
        print("CRITICAL_THREE_BRANCH_CANDIDATE=PASS")
    else:
        print("EVERY_EXACT7_HAS_TWO_UNIT_EXACT6_ALTERNATIVES=FAIL")
        print("CRITICAL_THREE_BRANCH_CANDIDATE=FAIL")
        raise SystemExit(7)


if __name__ == "__main__":
    main()

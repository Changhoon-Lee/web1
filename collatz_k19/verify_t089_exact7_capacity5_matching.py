#!/usr/bin/env python3
"""Certificate-only verifier for the exact-seven capacity-five matching."""
from __future__ import annotations
from collections import defaultdict
from hashlib import sha256
from pathlib import Path
import argparse

L = 14
P6 = 3**6
P7 = 3**7


def closed_constant(word: int) -> int:
    # Independent closed form, read from the target end.
    later = 0
    out = 0
    for j in range(L - 1, -1, -1):
        if (word >> j) & 1:
            out += (1 << j) * (3**later)
            later += 1
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("certificate", type=Path)
    args = ap.parse_args()
    raw = args.certificate.read_bytes()
    lines = raw.decode("utf-8").splitlines()
    assert lines and lines[0] == "u\tv\td"

    left = defaultdict(int)
    right = defaultdict(int)
    seen_edges = set()
    min_d = 10**9
    max_d = -10**9
    for line in lines[1:]:
        u_s, v_s, d_s = line.split("\t")
        u, v, d = int(u_s), int(v_s), int(d_s)
        assert 0 <= u < 1 << L and 0 <= v < 1 << L
        assert u.bit_count() == 7
        assert v.bit_count() == 6
        assert (u, v) not in seen_edges
        seen_edges.add((u, v))
        ku = closed_constant(u)
        kv = closed_constant(v)
        assert ku - kv == P6 * d
        assert (ku - kv) % P7 != 0
        assert d % 3 != 0
        left[u] += 1
        right[v] += 1
        min_d = min(min_d, d)
        max_d = max(max_d, d)

    assert len(left) == 3432
    assert len(seen_edges) == 6864
    assert all(c == 2 for c in left.values())
    assert max(right.values()) <= 5
    assert max_d <= 331
    # Sufficient finite large-source threshold:
    # M >= 662 => 3M+d <= (7/2)M for every selected edge.
    assert 2 * max_d <= 662

    margin_integer = (2**1449) * (35**16000) - (7**1449) * (31**16000)
    assert margin_integer > 0

    print(f"ROWS={len(seen_edges)}")
    print(f"LEFT_WORDS={len(left)}")
    print(f"RIGHT_WORDS_USED={len(right)}")
    print(f"MAX_REVERSE_LOAD={max(right.values())}")
    print(f"MIN_INTERCEPT={min_d}")
    print(f"MAX_INTERCEPT={max_d}")
    print(f"CERTIFICATE_SHA256={sha256(raw).hexdigest()}")
    print("INDEPENDENT_CLOSED_FORM_REPLAY=PASS")
    print("HEIGHT_7_OVER_2_FROM_M_GE_662=PASS")
    print("CRITICAL_MARGIN_INTEGER=PASS")
    print("CERTIFICATE_VERDICT=PASS")


if __name__ == "__main__":
    main()

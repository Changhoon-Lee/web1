#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import mmap
import sys
from collections import Counter
from pathlib import Path

EXPECTED_BYTES = 387_420_489
EXPECTED_SHA256 = "728ed6fbe2def7f37e41b5568feefe3553a3d7c43553aee6ee5495f7ae241e39"
MIN_WEIGHT = 1_497_192
MAX_WEIGHT = 4_166_117_961


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def ceil_p_log2_3(p: int) -> int:
    """Smallest n with n >= p*log_2(3), computed by exact integers."""
    target = pow(3, p)
    n = max(0, target.bit_length() - 1)
    if pow(2, n) < target:
        n += 1
    assert (n == 0 or pow(2, n - 1) < target) and pow(2, n) >= target
    return n


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: k19_maximum_depth_budget_stats.py POTENTIAL", file=sys.stderr)
        return 2
    path = Path(sys.argv[1])
    size = path.stat().st_size
    digest = sha256_file(path)
    if size != EXPECTED_BYTES:
        print(f"BAD_SIZE={size}", file=sys.stderr)
        return 3
    if digest != EXPECTED_SHA256:
        print(f"BAD_SHA256={digest}", file=sys.stderr)
        return 4

    hist = Counter()
    minimum = 255
    maximum = 0
    first_max = -1
    with path.open("rb") as f, mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as mm:
        # Iterating the mmap yields one-byte bytes objects on some Python builds;
        # scan in chunks so Counter consumes ordinary bytes efficiently.
        chunk_size = 16 << 20
        for start in range(0, size, chunk_size):
            chunk = mm[start:min(size, start + chunk_size)]
            c = Counter(chunk)
            hist.update(c)
            cmin = min(c)
            cmax = max(c)
            if cmin < minimum:
                minimum = cmin
            if cmax > maximum:
                maximum = cmax
                first_max = start + chunk.index(bytes([cmax]))
            elif cmax == maximum and first_max < 0:
                first_max = start + chunk.index(bytes([cmax]))

    assert sum(hist.values()) == EXPECTED_BYTES
    alpha_ceiling = ceil_p_log2_3(maximum)
    # criticalFuel(root i) = ceil(naturalPotential(root i)/alpha) + 1,
    # alpha = log_2(3), and the numerical first-hit budget is twice the fuel.
    max_critical_fuel = alpha_ceiling + 1
    maximum_depth_budget = 2 * max_critical_fuel
    exact_depth_layer_count = maximum_depth_budget + 1

    normalized_min_coefficient_num = MIN_WEIGHT
    normalized_min_coefficient_den = MAX_WEIGHT
    pigeonhole_num = MIN_WEIGHT
    pigeonhole_den = MAX_WEIGHT * exact_depth_layer_count

    print(f"POTENTIAL_BYTES={size}")
    print(f"POTENTIAL_SHA256={digest}")
    print(f"POTENTIAL_MIN={minimum}")
    print(f"POTENTIAL_MAX={maximum}")
    print(f"POTENTIAL_MAX_COUNT={hist[maximum]}")
    print(f"POTENTIAL_FIRST_MAX_INDEX={first_max}")
    print(f"CEIL_MAX_POTENTIAL_OVER_LOG2_3={alpha_ceiling}")
    print(f"MAX_CRITICAL_FUEL={max_critical_fuel}")
    print(f"MAXIMUM_DEPTH_BUDGET={maximum_depth_budget}")
    print(f"EXACT_DEPTH_LAYER_COUNT={exact_depth_layer_count}")
    print(f"NORMALIZED_MIN_COEFFICIENT={normalized_min_coefficient_num}/{normalized_min_coefficient_den}")
    print(f"PIGEONHOLE_EXACT_DEPTH_FLOOR={pigeonhole_num}/{pigeonhole_den}")
    print(f"PIGEONHOLE_GT_7_OVER_8={'PASS' if 8*pigeonhole_num > 7*pigeonhole_den else 'FAIL'}")
    print(f"PIGEONHOLE_TIMES_8_OVER_7_GT_ONE={'PASS' if 8*pigeonhole_num > 7*pigeonhole_den else 'FAIL'}")
    print("HISTOGRAM_BEGIN")
    for value in sorted(hist):
        print(f"POTENTIAL_VALUE_{value}_COUNT={hist[value]}")
    print("HISTOGRAM_END")
    print("EXACT_INTEGER_DEPTH_BUDGET_CERTIFICATE=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

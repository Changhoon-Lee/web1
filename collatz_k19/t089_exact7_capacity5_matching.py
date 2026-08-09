#!/usr/bin/env python3
"""Exact capacity-five matching for the 14-bit T089 critical layer.

Every seven-odd word demands two six-odd alternatives.  An edge is legal when
`v3(K(u)-K(v)) = 6`; this is exactly the same-target integrality condition and
makes the alternative source a 3-adic unit.  A deterministic integral max-flow
selects two edges per seven-odd word while using every six-odd word at most five
times.
"""
from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass
from hashlib import sha256
from math import comb
from pathlib import Path
import argparse

L = 14
P6 = 3**6
P7 = 3**7
LEFT_DEMAND = 2
RIGHT_CAPACITY = 5
TOTAL_LEFT = comb(14, 7)
TOTAL_DEMAND = LEFT_DEMAND * TOTAL_LEFT


def word_constant(word: int) -> int:
    k = 0
    for j in range(L):
        if (word >> j) & 1:
            k = 3 * k + (1 << j)
    return k


@dataclass
class Edge:
    to: int
    rev: int
    cap: int


class Dinic:
    def __init__(self, n: int) -> None:
        self.g: list[list[Edge]] = [[] for _ in range(n)]

    def add(self, u: int, v: int, cap: int) -> int:
        ui = len(self.g[u])
        vi = len(self.g[v])
        self.g[u].append(Edge(v, vi, cap))
        self.g[v].append(Edge(u, ui, 0))
        return ui

    def max_flow(self, source: int, sink: int) -> int:
        total = 0
        n = len(self.g)
        while True:
            level = [-1] * n
            level[source] = 0
            q = deque([source])
            while q:
                u = q.popleft()
                for e in self.g[u]:
                    if e.cap and level[e.to] < 0:
                        level[e.to] = level[u] + 1
                        q.append(e.to)
            if level[sink] < 0:
                return total
            it = [0] * n

            def dfs(u: int, pushed: int) -> int:
                if u == sink:
                    return pushed
                while it[u] < len(self.g[u]):
                    e = self.g[u][it[u]]
                    if e.cap and level[e.to] == level[u] + 1:
                        take = dfs(e.to, min(pushed, e.cap))
                        if take:
                            e.cap -= take
                            self.g[e.to][e.rev].cap += take
                            return take
                    it[u] += 1
                return 0

            while True:
                pushed = dfs(source, 10**9)
                if not pushed:
                    break
                total += pushed


def legal_graph() -> tuple[list[int], list[int], dict[int, list[tuple[int, int]]]]:
    six_by_mod: dict[int, list[tuple[int, int]]] = defaultdict(list)
    seven: list[int] = []
    constants: dict[int, int] = {}
    for w in range(1 << L):
        k = word_constant(w)
        constants[w] = k
        if w.bit_count() == 6:
            six_by_mod[k % P6].append((w, k))
        elif w.bit_count() == 7:
            seven.append(w)
    six = sorted(w for bucket in six_by_mod.values() for w, _ in bucket)
    legal: dict[int, list[tuple[int, int]]] = {}
    for u in seven:
        ku = constants[u]
        choices: list[tuple[int, int]] = []
        for v, kv in six_by_mod[ku % P6]:
            diff = ku - kv
            if diff % P7 != 0:
                assert diff % P6 == 0
                choices.append((v, diff // P6))
        choices.sort()
        legal[u] = choices
    return sorted(seven), six, legal


def build_matching(
    seven: list[int], six: list[int], legal: dict[int, list[tuple[int, int]]]
) -> list[tuple[int, int, int]]:
    right_index = {v: i for i, v in enumerate(six)}
    source = 0
    left0 = 1
    right0 = left0 + len(seven)
    sink = right0 + len(six)
    net = Dinic(sink + 1)
    edge_slots: dict[tuple[int, int], int] = {}
    for li, u in enumerate(seven):
        node = left0 + li
        net.add(source, node, LEFT_DEMAND)
        for v, _d in legal[u]:
            ri = right_index[v]
            slot = net.add(node, right0 + ri, 1)
            edge_slots[(u, v)] = slot
    for ri, _v in enumerate(six):
        net.add(right0 + ri, sink, RIGHT_CAPACITY)
    flow = net.max_flow(source, sink)
    assert flow == TOTAL_DEMAND, (flow, TOTAL_DEMAND)

    d_lookup = {(u, v): d for u in seven for v, d in legal[u]}
    selected: list[tuple[int, int, int]] = []
    for li, u in enumerate(seven):
        node = left0 + li
        chosen = []
        for v, _d in legal[u]:
            e = net.g[node][edge_slots[(u, v)]]
            # Original capacity one has been consumed exactly when cap is zero.
            if e.cap == 0:
                chosen.append(v)
        assert len(chosen) == LEFT_DEMAND, (u, chosen)
        for v in chosen:
            selected.append((u, v, d_lookup[(u, v)]))
    return selected


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()

    seven, six, legal = legal_graph()
    assert len(seven) == 3432
    assert len(six) == 3003
    min_legal = min(len(legal[u]) for u in seven)
    selected = build_matching(seven, six, legal)

    per_left: dict[int, int] = defaultdict(int)
    per_right: dict[int, int] = defaultdict(int)
    min_d = 10**9
    max_d = -10**9
    rows = ["u\tv\td"]
    for u, v, d in selected:
        ku = word_constant(u)
        kv = word_constant(v)
        assert u.bit_count() == 7 and v.bit_count() == 6
        assert ku - kv == P6 * d
        assert d % 3 != 0
        per_left[u] += 1
        per_right[v] += 1
        min_d = min(min_d, d)
        max_d = max(max_d, d)
        rows.append(f"{u}\t{v}\t{d}")
    assert set(per_left) == set(seven)
    assert all(per_left[u] == 2 for u in seven)
    max_load = max(per_right.values())
    assert max_load <= RIGHT_CAPACITY
    assert len(selected) == TOTAL_DEMAND
    assert max_d <= 331

    text = "\n".join(rows) + "\n"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(text, encoding="utf-8")
    digest = sha256(text.encode()).hexdigest()

    # At common inflation h = 7/2 and theta = 1449/16000,
    # h^(-theta) + (2/5)h^(-1) > 1 is equivalent to this integer inequality.
    margin_integer = (2**1449) * (35**16000) - (7**1449) * (31**16000)
    assert margin_integer > 0

    print(f"EXACT6_WORDS={len(six)}")
    print(f"EXACT7_WORDS={len(seven)}")
    print(f"MIN_LEGAL_UNIT_ALTERNATIVES={min_legal}")
    print(f"SELECTED_EDGES={len(selected)}")
    print(f"MAX_REVERSE_LOAD={max_load}")
    print(f"MIN_SELECTED_INTERCEPT={min_d}")
    print(f"MAX_SELECTED_INTERCEPT={max_d}")
    print(f"MATCHING_SHA256={digest}")
    print(f"CRITICAL_MARGIN_INTEGER_DIGITS={len(str(margin_integer))}")
    print("CRITICAL_MARGIN_H_EQ_7_OVER_2=PASS")
    print("T089_EXACT7_CAPACITY5_MATCHING=PASS")


if __name__ == "__main__":
    main()

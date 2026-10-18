"""Hai bài mẫu để thử core và làm khuôn cho pipes.py / kakurasu.py.

- EightPuzzle: dùng với dfs, bfs, astar (tìm kiếm từng bước).
- NQueens:     dùng với hill_climbing, simulated_annealing (tìm kiếm cục bộ).
"""

from __future__ import annotations

import random

from core.problem import Problem


class EightPuzzle(Problem):
    """Bảng 3x3, số 0 là ô trống. State là tuple 9 số."""

    name = "8puzzle"
    GOAL = (1, 2, 3, 4, 5, 6, 7, 8, 0)
    MOVES = {"U": -3, "D": 3, "L": -1, "R": 1}

    def __init__(self, start):
        self.start = tuple(start)

    def initial_state(self):
        return self.start

    def successors(self, state):
        z = state.index(0)
        r, c = divmod(z, 3)
        for a, d in self.MOVES.items():
            if (a == "U" and r == 0) or (a == "D" and r == 2) \
                    or (a == "L" and c == 0) or (a == "R" and c == 2):
                continue
            s = list(state)
            s[z], s[z + d] = s[z + d], s[z]
            yield a, tuple(s), 1

    def is_goal(self, state):
        return state == self.GOAL

    def heuristic(self, state):
        # tổng khoảng cách Manhattan, admissible
        total = 0
        for i, v in enumerate(state):
            if v:
                gr, gc = divmod(v - 1, 3)
                r, c = divmod(i, 3)
                total += abs(r - gr) + abs(c - gc)
        return total

    def to_view(self, state):
        return [list(state[i:i + 3]) for i in (0, 3, 6)]


class NQueens(Problem):
    """N quân hậu. State là tuple: state[c] = hàng của quân hậu ở cột c."""

    name = "nqueens"

    def __init__(self, n=8):
        self.n = n

    # --- tìm kiếm từng bước: đặt lần lượt từng cột, cắt tỉa khi bị ăn ---
    def initial_state(self):
        return ()

    def successors(self, state):
        c = len(state)
        for r in range(self.n):
            if all(r != r2 and abs(r - r2) != c - c2 for c2, r2 in enumerate(state)):
                yield (c, r), state + (r,), 1

    def is_goal(self, state):
        return len(state) == self.n

    # --- tìm kiếm cục bộ: mỗi cột luôn có đúng 1 quân hậu ---
    def local_initial_state(self, rng):
        return tuple(rng.randrange(self.n) for _ in range(self.n))

    def local_neighbors(self, state):
        for c in range(self.n):
            for r in range(self.n):
                if r != state[c]:
                    yield (c, r), state[:c] + (r,) + state[c + 1:]

    def local_random_neighbor(self, state, rng):
        c = rng.randrange(self.n)
        r = rng.choice([x for x in range(self.n) if x != state[c]])
        return (c, r), state[:c] + (r,) + state[c + 1:]

    def local_cost(self, state):
        # số cặp hậu ăn nhau
        n, k = len(state), 0
        for i in range(n):
            for j in range(i + 1, n):
                if state[i] == state[j] or abs(state[i] - state[j]) == j - i:
                    k += 1
        return k

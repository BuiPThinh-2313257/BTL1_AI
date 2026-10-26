"""Kiểm thử Kakurasu. Chạy từ thư mục gốc BTL:  python -m unittest discover tests"""

import glob
import itertools
import json
import math
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from core import Limits, Trace, astar, bfs, dfs
from core.search import SOLVED
from puzzles.kakurasu import Kakurasu, subset_tables, verify

FILES = sorted(glob.glob(os.path.join(ROOT, "data", "kakurasu_*.json")))
SMALL = os.path.join(ROOT, "data", "kakurasu_4x4_easy.json")
# Lời giải duy nhất của đề 9272227 (kiểm chứng bằng brute force 2^16 ở dưới)
SMALL_SOLUTION = [[0, 1, 0, 0],
                  [0, 0, 0, 1],
                  [1, 0, 1, 0],
                  [0, 1, 1, 0]]
SMALL_FLAT = tuple(v for row in SMALL_SOLUTION for v in row)


class TestModel(unittest.TestCase):
    def test_data_files(self):
        self.assertEqual(len(FILES), 12)

    def test_subset_tables(self):
        reach, mincnt = subset_tables(4)
        self.assertEqual(reach[3], {0, 3, 4, 7})
        self.assertEqual(reach[5], {0})
        self.assertEqual(mincnt[1][5], 2)
        self.assertEqual(reach[1], set(range(11)))

    def test_verify(self):
        self.assertTrue(verify(SMALL_SOLUTION, [2, 4, 4, 5], [3, 5, 7, 2]))
        bad = [row[:] for row in SMALL_SOLUTION]
        bad[0][0] = 1
        self.assertFalse(verify(bad, [2, 4, 4, 5], [3, 5, 7, 2]))

    def test_verify_requires_integer_binary_cells(self):
        for value in (2, -1, "bad", "1", 1.0, True, None):
            with self.subTest(value=value):
                # Matching clues must not hide an invalid cell value.
                self.assertFalse(verify([[value]], [1], [1]))
        self.assertFalse(verify([[None]], [0], [0]))
        self.assertTrue(verify([[0]], [0], [0]))
        self.assertTrue(verify([[1]], [1], [1]))

    def test_verify_rejects_wrong_dimensions(self):
        self.assertFalse(verify([[1, 0]], [1, 0], [1, 0]))
        self.assertFalse(verify([[1], [0, 0]], [1, 0], [1]))

    def test_heuristic_and_pruning_against_exhaustive_small_oracle(self):
        # Independent completion oracle for every binary prefix, including
        # prefixes that the solver would normally prune before reaching.
        for n, m in ((2, 2), (2, 3)):
            boards = list(itertools.product((0, 1), repeat=n * m))
            by_clues = {}
            for board in boards:
                rows = tuple(sum((c + 1) * board[r * m + c] for c in range(m))
                             for r in range(n))
                cols = tuple(sum((r + 1) * board[r * m + c] for r in range(n))
                             for c in range(m))
                by_clues.setdefault((rows, cols), []).append(board)
            for (rows, cols), solutions in by_clues.items():
                p = Kakurasu(rows, cols, prune="full")
                for k in range(n * m + 1):
                    for state in itertools.product((0, 1), repeat=k):
                        possible = [b for b in solutions if b[:k] == state]
                        h = p.heuristic(state)
                        if possible:
                            exact = min(sum(b[k:]) for b in possible)
                            self.assertLessEqual(h, exact, (rows, cols, state))
                            if k < n * m:
                                kept = {s for _, s, _ in p.successors(state)}
                                for b in possible:
                                    self.assertIn(b[:k + 1], kept)
                        if k < n * m:
                            for value in (0, 1):
                                self.assertLessEqual(h, value + p.heuristic(state + (value,)),
                                                     (rows, cols, state, value))

    def test_unique_solution_4x4(self):
        p = Kakurasu.from_file(SMALL, prune="none")
        sols = [b for b in itertools.product((0, 1), repeat=p.size) if p.is_goal(b)]
        self.assertEqual(sols, [SMALL_FLAT])

    def test_successors_format(self):
        p = Kakurasu.from_file(SMALL, prune="none")
        self.assertEqual(list(p.successors(())),
                         [(((0, 0), 1), (1,), 1), (((0, 0), 0), (0,), 0)])
        self.assertEqual(list(p.successors(SMALL_FLAT)), [])

    def test_full_prune_cuts_early(self):
        # tô ô (0,0): hàng 0 còn thiếu 1, nhưng các cột còn lại có giá trị >= 2
        self.assertEqual([a for a, _, _ in Kakurasu.from_file(SMALL, "full").successors(())],
                         [((0, 0), 0)])
        self.assertEqual(len(list(Kakurasu.from_file(SMALL, "basic").successors(()))), 2)

    def test_prune_keeps_solution_path(self):
        """Cắt tỉa không được bỏ nước đi nằm trên lời giải đúng."""
        for level in ("basic", "full"):
            p = Kakurasu.from_file(SMALL, prune=level)
            for k in range(p.size):
                nxt = [s2 for _, s2, _ in p.successors(SMALL_FLAT[:k])]
                self.assertIn(SMALL_FLAT[:k + 1], nxt, (level, k))

    def test_heuristic_admissible_on_solution_path(self):
        p = Kakurasu.from_file(SMALL)
        for k in range(p.size + 1):
            self.assertLessEqual(p.heuristic(SMALL_FLAT[:k]), sum(SMALL_FLAT[k:]))
        self.assertEqual(p.heuristic(()), 6)   # bằng đúng số ô đen của lời giải
        self.assertEqual(p.heuristic(SMALL_FLAT), 0)

    def test_heuristic_dead_state(self):
        p = Kakurasu.from_file(SMALL)
        self.assertEqual(p.heuristic((1, 1)), float("inf"))  # hàng 0: 1+2 > 2

    def test_to_view(self):
        p = Kakurasu.from_file(SMALL)
        v = p.to_view((1, 0))
        self.assertEqual(v["grid"][0], [1, 0, None, None])
        self.assertEqual(list(v["rows"]), [2, 4, 4, 5])


class TestSolvers(unittest.TestCase):
    def test_all_puzzles_full_prune(self):
        for path in FILES:
            for algo in (dfs, bfs, astar):
                p = Kakurasu.from_file(path, prune="full")
                r = algo(p, limits=Limits(time_limit=30))
                with self.subTest(file=os.path.basename(path), algo=algo.__name__):
                    self.assertEqual(r.status, SOLVED)
                    self.assertTrue(verify(p.to_grid(r.final_state), p.row_clues, p.col_clues))

    def test_astar_basic_prune_solves_all(self):
        for path in FILES:
            p = Kakurasu.from_file(path, prune="basic")
            r = astar(p, limits=Limits(time_limit=30))
            with self.subTest(file=os.path.basename(path)):
                self.assertEqual(r.status, SOLVED)
                self.assertEqual(r.cost, sum(r.final_state))  # cost = số ô đen

    def test_astar_can_expand_infinite_priority_on_unsatisfiable_input(self):
        p = Kakurasu([1], [0], prune="basic")
        trace = Trace(p, "astar")
        result = astar(p, trace=trace)
        self.assertEqual(result.status, "no_solution")
        self.assertTrue(any(step["event"] == "expand" and math.isinf(step["h"])
                            for step in trace.steps))

    def test_saved_traces_reproduce_solver_steps(self):
        for algorithm in (dfs, astar):
            path = os.path.join(ROOT, "traces", "example_kakurasu_4x4_" + algorithm.__name__ + ".json")
            with open(path, encoding="utf-8") as stream:
                saved = json.load(stream)
            # Both saved demos use basic pruning; DFS shows backtracking.
            p = Kakurasu.from_file(SMALL, prune="basic")
            trace = Trace(p, algorithm.__name__, input_name=saved["input"])
            result = algorithm(p, trace=trace)
            fresh = json.loads(json.dumps(trace.to_dict()))
            for field in ("initial", "steps", "solution", "truncated"):
                self.assertEqual(fresh[field], saved[field], (algorithm.__name__, field))
            self.assertEqual(result.nodes_expanded, saved["result"]["nodes_expanded"])
            self.assertTrue(verify(p.to_grid(result.final_state), p.row_clues, p.col_clues))

    def test_trace(self):
        p = Kakurasu.from_file(SMALL)
        t = Trace(p, "astar", input_name="kakurasu_4x4_easy")
        astar(p, trace=t)
        d = t.to_dict()
        self.assertEqual(d["puzzle"], "kakurasu")
        self.assertEqual(d["solution"][-1]["grid"], SMALL_SOLUTION)
        self.assertEqual(d["steps"][-1]["event"], "goal")


if __name__ == "__main__":
    unittest.main()

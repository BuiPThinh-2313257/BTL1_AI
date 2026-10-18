"""Kiểm thử core. Chạy từ thư mục gốc BTL:  python -m unittest discover tests"""

import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import (Limits, Trace, astar, bfs, dfs, greedy, hill_climbing,
                  load_trace, measure, simulated_annealing, write_csv)
from core.search import NODE_LIMIT, NO_SOLUTION, SOLVED
from puzzles.examples import EightPuzzle, NQueens

EASY = (1, 2, 3, 4, 5, 6, 0, 7, 8)          # cần 2 bước
MEDIUM = (8, 6, 7, 2, 5, 4, 3, 0, 1)        # một trong những bài khó nhất: 31 bước
UNSOLVABLE = (1, 2, 3, 4, 5, 6, 8, 7, 0)    # hoán vị lẻ, vô nghiệm


def valid_path(problem, res):
    """Mỗi bước trong path phải là successor hợp lệ của bước trước."""
    for s, a, s2 in zip(res.path, res.actions, res.path[1:]):
        if (a, s2) not in [(x, y) for x, y, _ in problem.successors(s)]:
            return False
    return res.path[0] == problem.initial_state() and problem.is_goal(res.path[-1])


class TestBlindAndInformed(unittest.TestCase):
    def test_bfs_optimal(self):
        p = EightPuzzle(EASY)
        r = bfs(p)
        self.assertEqual(r.status, SOLVED)
        self.assertEqual(len(r.actions), 2)
        self.assertTrue(valid_path(p, r))

    def test_astar_optimal_hard(self):
        p = EightPuzzle(MEDIUM)
        r = astar(p)
        self.assertEqual(r.status, SOLVED)
        self.assertEqual(r.cost, 31)
        self.assertTrue(valid_path(p, r))

    def test_astar_expands_less_than_bfs(self):
        p = EightPuzzle((4, 1, 3, 7, 2, 6, 0, 5, 8))
        self.assertLess(astar(p).nodes_expanded, bfs(p).nodes_expanded)

    def test_dfs_and_greedy_find_valid_solution(self):
        p = EightPuzzle((1, 2, 3, 4, 0, 6, 7, 5, 8))
        for algo in (dfs, greedy):
            r = algo(p)
            self.assertEqual(r.status, SOLVED, algo.__name__)
            self.assertTrue(valid_path(p, r), algo.__name__)

    def test_dfs_nqueens(self):
        p = NQueens(8)
        r = dfs(p)
        self.assertEqual(r.status, SOLVED)
        self.assertEqual(p.local_cost(r.final_state), 0)

    def test_no_solution(self):
        r = bfs(NQueens(3))
        self.assertEqual(r.status, NO_SOLUTION)

    def test_node_limit(self):
        r = bfs(EightPuzzle(UNSOLVABLE), limits=Limits(max_nodes=500))
        self.assertEqual(r.status, NODE_LIMIT)
        self.assertLessEqual(r.nodes_expanded, 500)

    def test_dfs_max_depth(self):
        r = dfs(EightPuzzle(MEDIUM), limits=Limits(max_depth=5))
        self.assertNotEqual(r.status, SOLVED)
        self.assertLessEqual(r.max_depth, 5)


class TestLocal(unittest.TestCase):
    def test_hill_climbing(self):
        p = NQueens(8)
        r = hill_climbing(p, seed=1, max_restarts=100)
        self.assertEqual(r.status, SOLVED)
        self.assertEqual(p.local_cost(r.final_state), 0)

    def test_simulated_annealing(self):
        p = NQueens(8)
        r = simulated_annealing(p, seed=3, max_restarts=20)
        self.assertEqual(r.status, SOLVED)
        self.assertEqual(p.local_cost(r.final_state), 0)

    def test_seed_reproducible(self):
        p = NQueens(10)
        a = hill_climbing(p, seed=7)
        b = hill_climbing(p, seed=7)
        self.assertEqual(a.final_state, b.final_state)
        self.assertEqual(a.nodes_expanded, b.nodes_expanded)


class TestTraceAndMetrics(unittest.TestCase):
    def test_trace_roundtrip(self):
        p = EightPuzzle(EASY)
        t = Trace(p, "astar")
        r = astar(p, trace=t)
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "t.json")
            t.save(path)
            data = load_trace(path)
        self.assertEqual(data["puzzle"], "8puzzle")
        self.assertEqual(data["initial"], [[1, 2, 3], [4, 5, 6], [0, 7, 8]])
        self.assertEqual(data["steps"][-1]["event"], "goal")
        self.assertEqual(len(data["solution"]), len(r.path))
        self.assertTrue(data["result"]["found"])

    def test_trace_truncation(self):
        p = EightPuzzle(MEDIUM)
        t = Trace(p, "bfs", max_steps=50)
        bfs(p, trace=t)
        self.assertTrue(t.truncated)
        self.assertEqual(len(t.steps), 50)

    def test_local_trace_events(self):
        p = NQueens(8)
        t = Trace(p, "hill_climbing")
        hill_climbing(p, trace=t, seed=1, max_restarts=100)
        events = {s["event"] for s in t.steps}
        self.assertIn("goal", events)
        json.dumps(t.to_dict())   # phải ghi ra JSON được

    def test_measure_and_csv(self):
        p = EightPuzzle(MEDIUM)
        m = measure(astar, p, input_name="medium")
        self.assertGreater(m.time_s, 0)
        self.assertGreater(m.peak_kb, 0)
        self.assertEqual(m.result.status, SOLVED)
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "out", "b.csv")
            write_csv([m], path)
            write_csv([m], path, append=True)
            with open(path, encoding="utf-8") as f:
                lines = f.read().strip().splitlines()
        self.assertEqual(len(lines), 3)   # header + 2 dòng
        self.assertTrue(lines[0].startswith("puzzle,input,algorithm"))


if __name__ == "__main__":
    unittest.main()

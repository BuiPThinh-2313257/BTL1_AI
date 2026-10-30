"""Chạy từ thư mục gốc BTL1_AI: python -m unittest tests/test_verify.py -v"""
import json
import unittest
from pathlib import Path

from core import Limits, dfs
from puzzles.kakurasu import Kakurasu
from verify import validate_input, verify_kakurasu, verify_pipes, verify_solution


class TestVerify(unittest.TestCase):
    def test_all_json_have_valid_structure(self):
        files = list(Path("data").glob("*.json"))
        self.assertTrue(files)
        for path in files:
            with self.subTest(path=path):
                data = json.loads(path.read_text(encoding="utf-8"))
                self.assertIn(validate_input(data), ("pipes", "kakurasu"))

    def test_kakurasu_real_solution_and_corruption(self):
        path = Path("data/kakurasu_4x4_easy.json")
        data = json.loads(path.read_text(encoding="utf-8"))
        p = Kakurasu.from_file(str(path), prune="full")
        result = dfs(p, limits=Limits(max_nodes=50000, time_limit=10))
        self.assertEqual(result.status, "solved")
        self.assertTrue(verify_solution(data, result.final_state))
        self.assertFalse(verify_kakurasu(data, result.final_state[:-1]))
        bad = list(result.final_state)
        bad[0] = 1 - bad[0]
        self.assertFalse(verify_kakurasu(data, bad))

    def test_pipes_valid_simple_chain(self):
        data = {
            "grid_size": {"rows": 1, "cols": 2},
            "grid": [[
                {"row": 0, "col": 0, "type": "end", "connections": ["right"], "rotatable": False},
                {"row": 0, "col": 1, "type": "end", "connections": ["left"], "rotatable": False},
            ]],
        }
        self.assertEqual(validate_input(data), "pipes")
        self.assertTrue(verify_pipes(data, (("right",), ("left",))))
        self.assertFalse(verify_pipes(data, (("left",), ("right",))))

    def test_pipes_reject_connected_cycle(self):
        data = {"grid_size": {"rows": 2, "cols": 2}, "grid": [
            [{"row": r, "col": c, "type": "L-shape", "connections": ["right", "down"],
              "rotatable": True} for c in range(2)] for r in range(2)]}
        cycle = (("right", "down"), ("left", "down"),
                 ("up", "right"), ("up", "left"))
        self.assertFalse(verify_pipes(data, cycle))


if __name__ == "__main__":
    unittest.main()

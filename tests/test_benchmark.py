"""TV5: kiem thu module benchmark, chay tai thu muc goc BTL1_AI."""
import unittest
from pathlib import Path

from benchmark import (
    algorithms_for, issue_from_row, load_case, run_one, summarize,
)


class TestBenchmarkTV5(unittest.TestCase):
    def test_algorithm_mapping(self):
        self.assertEqual(algorithms_for("kakurasu", None), ("dfs", "astar"))
        self.assertEqual(algorithms_for("pipes", None), ("dfs", "hill_climbing"))
        with self.assertRaises(ValueError):
            algorithms_for("kakurasu", ["hill_climbing"])

    def test_load_real_json(self):
        kind, data, problem = load_case(Path("data/kakurasu_4x4_easy.json"))
        self.assertEqual(kind, "kakurasu")
        self.assertEqual(problem.size, data["rows"] * data["cols"])

    def test_kakurasu_dfs_verified(self):
        result = run_one(Path("data/kakurasu_4x4_easy.json"), "dfs",
                         track_memory=False, max_nodes=50000, time_limit=5)
        self.assertEqual(result["status"], "solved")
        self.assertIs(result["verified"], True)
        self.assertIs(result["valid_solution"], True)
        self.assertIsNone(issue_from_row(result))

    def test_pipes_solver_bug_is_reported(self):
        # Test hien trang da biet: solved chua dam bao dung luat cam chu trinh.
        # Sau khi TV2 sua, co the thay test nay bang assert verified=True.
        record = {
            "puzzle": "pipes", "input": "sample.json", "algorithm": "dfs",
            "run": 1, "status": "solved", "found": True,
            "verified": False, "valid_solution": False, "error": "",
        }
        issue = issue_from_row(record)
        self.assertEqual(issue["issue"], "invalid_solution")

    def test_summary_distinguishes_failed_and_valid(self):
        base = {"puzzle": "kakurasu", "input": "x.json", "algorithm": "dfs",
                "time_s": 0.1, "peak_kb": 10, "nodes_expanded": 5}
        rows = [
            {**base, "status": "solved", "found": True, "verified": True,
             "valid_solution": True},
            {**base, "status": "node_limit", "found": False, "verified": None,
             "valid_solution": False},
        ]
        s = summarize(rows)[0]
        self.assertEqual(s["valid_runs"], 1)
        self.assertEqual(s["unsolved_runs"], 1)
        self.assertEqual(s["success_rate"], 0.5)


if __name__ == "__main__":
    unittest.main()


"""Unit test cho công cụ benchmark TV5.

Chạy từ thư mục gốc BTL1_AI:
    py -m unittest discover -s tests -p "test_*.py" -v
"""
import unittest
from pathlib import Path

from benchmark import (
    algorithms_for,
    issue_from_row,
    load_case,
    run_one,
    summarize,
)


class TestBenchmarkTV5(unittest.TestCase):
    def test_algorithm_mapping(self):
        self.assertEqual(
            algorithms_for("kakurasu", None),
            ("dfs", "astar")
        )
        self.assertEqual(
            algorithms_for("pipes", None),
            ("dfs", "hill_climbing")
        )
        with self.assertRaises(ValueError):
            algorithms_for("kakurasu", ["hill_climbing"])

    def test_load_real_json(self):
        kind, data, problem = load_case(
            Path("data/kakurasu_4x4_easy.json")
        )
        self.assertEqual(kind, "kakurasu")
        self.assertEqual(
            problem.size,
            data["rows"] * data["cols"]
        )

    def test_kakurasu_dfs_verified(self):
        result = run_one(
            Path("data/kakurasu_4x4_easy.json"),
            "dfs",
            track_memory=False,
            max_nodes=50000,
            time_limit=5,
        )
        self.assertEqual(result["status"], "solved")
        self.assertIs(result["verified"], True)
        self.assertIs(result["valid_solution"], True)
        self.assertIsNone(issue_from_row(result))

    def test_invalid_solution_is_reported(self):
        # Mo phong solver bao solved nhung loi giai sai.
        record = {
            "puzzle": "pipes",
            "input": "sample.json",
            "algorithm": "dfs",
            "run": 1,
            "status": "solved",
            "found": True,
            "verified": False,
            "valid_solution": False,
            "error": "",
        }

        issue = issue_from_row(record)

        self.assertIsNotNone(issue)
        self.assertEqual(
            issue["issue"],
            "invalid_solution"
        )

    def test_summary_distinguishes_failed_and_valid(self):
        base = {
            "puzzle": "kakurasu",
            "input": "x.json",
            "algorithm": "dfs",
            "time_s": 0.1,
            "peak_kb": 10,
            "nodes_expanded": 5,
        }

        rows = [
            {
                **base,
                "status": "solved",
                "found": True,
                "verified": True,
                "valid_solution": True,
            },
            {
                **base,
                "status": "node_limit",
                "found": False,
                "verified": None,
                "valid_solution": False,
            },
        ]

        summary = summarize(rows)[0]

        self.assertEqual(summary["valid_runs"], 1)
        self.assertEqual(summary["unsolved_runs"], 1)
        self.assertEqual(summary["success_rate"], 0.5)

    def test_summary_rejects_invalid_solved(self):
        row = {
            "puzzle": "pipes",
            "input": "bad.json",
            "algorithm": "dfs",
            "time_s": 0.01,
            "peak_kb": 20,
            "nodes_expanded": 10,
            "status": "solved",
            "found": True,
            "verified": False,
            "valid_solution": False,
        }

        summary = summarize([row])[0]

        self.assertEqual(summary["valid_runs"], 0)
        self.assertEqual(summary["invalid_runs"], 1)
        self.assertEqual(summary["success_rate"], 0)
        self.assertEqual(
            summary["median_time_valid_s"],
            ""
        )

    def test_pipes_dfs_real_input_verified(self):
        """Kiem tra Pipes 4x4 da sua bang DFS."""
        result = run_one(
            Path("data/input_pipes_4x4.json"),
            "dfs",
            track_memory=False,
            max_nodes=50000,
            time_limit=5,
        )

        self.assertEqual(result["status"], "solved")
        self.assertIs(result["verified"], True)
        self.assertIs(result["valid_solution"], True)
        self.assertIsNone(issue_from_row(result))

    def test_pipes_hill_climbing_real_input_verified(self):
        """Kiem tra Pipes 4x4 bang Hill Climbing, seed=0."""
        result = run_one(
            Path("data/input_pipes_4x4.json"),
            "hill_climbing",
            seed=0,
            track_memory=False,
            max_nodes=50000,
            time_limit=5,
        )

        self.assertEqual(result["status"], "solved")
        self.assertIs(result["verified"], True)
        self.assertIs(result["valid_solution"], True)
        self.assertIsNone(issue_from_row(result))


if __name__ == "__main__":
    unittest.main()

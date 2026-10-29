"""TV4 GĐ2: kiểm tra tích hợp solver -> JSON trace -> GUI (headless)."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from core.trace import load_trace
from gui.live_runner import DEFAULT_INPUTS, ROOT, run_live_trace
from gui.viewer import get_frames, validate_trace
from puzzles.kakurasu import Kakurasu
from puzzles.pipes import Pipes


class LiveIntegrationTests(unittest.TestCase):
    def test_four_solver_combinations_produce_valid_trace(self):
        cases = (("pipes", "dfs"), ("pipes", "hill_climbing"),
                 ("kakurasu", "dfs"), ("kakurasu", "astar"))
        for puzzle, algorithm in cases:
            with self.subTest(puzzle=puzzle, algorithm=algorithm):
                data = run_live_trace(puzzle, algorithm, seed=0,
                                      max_nodes=20000, time_limit=5,
                                      track_memory=False)
                validate_trace(data)
                self.assertEqual(data["puzzle"], puzzle)
                self.assertEqual(data["algorithm"], algorithm)
                self.assertEqual(data["result"]["status"], "solved")
                self.assertEqual(data["steps"][-1]["event"], "goal")
                if puzzle == "kakurasu" and algorithm == "dfs":
                    # Cùng cấu hình TV3, không kiểm tra thời gian vì thay đổi theo máy.
                    self.assertEqual(data["result"]["nodes_expanded"], 483)
                    self.assertEqual(len(data["steps"]), 485)
                self.assertGreater(len(get_frames(data, "search")), 1)
                self.assertGreater(len(data["solution"]), 1)
                problem = (Pipes.from_file(str(DEFAULT_INPUTS[puzzle])) if puzzle == "pipes"
                           else Kakurasu.from_file(str(DEFAULT_INPUTS[puzzle])))
                if puzzle == "pipes":
                    goal_view = data["solution"][-1]
                    final = tuple(tuple(cell) for row in goal_view for cell in row)
                else:
                    goal_view = data["solution"][-1]
                    final = tuple(v for row in goal_view["grid"] for v in row)
                self.assertTrue(problem.is_goal(final))

    def test_memory_is_measured_not_fabricated(self):
        data = run_live_trace("pipes", "dfs", track_memory=True)
        self.assertIsInstance(data["result"]["peak_kb"], float)
        self.assertGreater(data["result"]["peak_kb"], 0)
        self.assertEqual(data["result"]["memory_method"],
                         "tracemalloc_peak_second_run_without_trace")

    def test_gui_rejects_wrong_size(self):
        with self.assertRaisesRegex(ValueError, "4x4"):
            run_live_trace("kakurasu", "dfs", "data/kakurasu_5x5_easy.json")

    def test_rejects_unsupported_algorithm(self):
        with self.assertRaises(ValueError):
            run_live_trace("kakurasu", "hill_climbing")

    def test_subprocess_generates_loadable_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "trace.json"
            cp = subprocess.run(
                [sys.executable, "-m", "gui.live_runner", "--puzzle", "kakurasu",
                 "--algorithm", "astar", "--input", str(DEFAULT_INPUTS["kakurasu"]),
                 "--output", str(target), "--memory"],
                cwd=str(ROOT), text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                timeout=30)
            self.assertEqual(cp.returncode, 0, cp.stderr)
            trace = load_trace(str(target))
            validate_trace(trace)
            self.assertEqual(trace["result"]["status"], "solved")
            self.assertIsInstance(trace["result"]["peak_kb"], (int, float))


if __name__ == "__main__":
    unittest.main()

"""TV4: Kiểm thử dữ liệu trace dùng cho GUI (không cần mở cửa sổ)."""

import unittest
from pathlib import Path

from core.trace import load_trace
from gui.viewer import TRACES, ROOT, changed_cells, get_frames, validate_trace


class TraceViewerDataTests(unittest.TestCase):
    def test_four_real_traces_are_supported(self):
        for puzzle, mapping in TRACES.items():
            for _, name in mapping.items():
                with self.subTest(file=name):
                    data = load_trace(str(ROOT / "traces" / name))
                    self.assertEqual(data["puzzle"], puzzle)
                    validate_trace(data)

    def test_search_frames_include_initial(self):
        data = load_trace(str(ROOT / "traces" / "pipes_4x4_dfs.json"))
        search = get_frames(data, "search")
        self.assertEqual(len(search), len(data["steps"]) + 1)
        self.assertEqual(search[0]["event"], "initial")
        self.assertEqual(search[-1]["event"], "goal")

    def test_solution_frames(self):
        data = load_trace(str(ROOT / "traces" / "example_kakurasu_4x4_astar.json"))
        frames = get_frames(data, "solution")
        self.assertEqual(len(frames), len(data["solution"]))
        self.assertEqual(frames[-1]["state"], data["solution"][-1])

    def test_pipes_changed_cells(self):
        before = [[None] * 4 for _ in range(4)]
        after = [[None] * 4 for _ in range(4)]
        after[0][0] = ["right", "down"]
        self.assertEqual(changed_cells(before, after, "pipes"), [(0, 0)])

    def test_reject_invalid_kakurasu_grid(self):
        data = load_trace(str(ROOT / "traces" / "example_kakurasu_4x4_astar.json"))
        data["initial"]["grid"] = [[None] * 4]  # sai số hàng
        with self.assertRaises(ValueError):
            validate_trace(data)


if __name__ == "__main__":
    unittest.main()

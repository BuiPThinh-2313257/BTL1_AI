import unittest
import json
from puzzles.pipes import Pipes

# Giả lập dữ liệu 2x2 đơn giản để test logic cắt tỉa và heuristic.
# Lời giải là một cây (3 mối nối cho 4 ô), không có vòng kín.
MOCK_DATA = {
  "grid_size": {"rows": 2, "cols": 2},
  "grid": [
    [
      {"row": 0, "col": 0, "type": "L-shape", "connections": ["right", "down"], "rotatable": True},
      {"row": 0, "col": 1, "type": "Dead-end", "connections": ["left"], "rotatable": True}
    ],
    [
      {"row": 1, "col": 0, "type": "L-shape", "connections": ["up", "right"], "rotatable": True},
      {"row": 1, "col": 1, "type": "Dead-end", "connections": ["left"], "rotatable": True}
    ]
  ]
}

GOAL_STATE = (("right", "down"), ("left",), ("up", "right"), ("left",))
# 4 ống chữ L tạo thành vòng kín: khớp hết và liên thông nhưng vi phạm luật
LOOP_STATE = (("right", "down"), ("left", "down"), ("up", "right"), ("up", "left"))


class TestPipes(unittest.TestCase):
    def setUp(self):
        self.problem = Pipes(MOCK_DATA)

    def test_initial_state(self):
        self.assertEqual(self.problem.initial_state(), ())

    def test_goal_state(self):
        self.assertTrue(self.problem.is_goal(GOAL_STATE))

        # Chưa gán đủ ô thì chưa phải đích
        incomplete_state = (("right", "down"),)
        self.assertFalse(self.problem.is_goal(incomplete_state))

        # Có vòng kín thì không phải đích
        self.assertFalse(self.problem.is_goal(LOOP_STATE))

    def test_local_cost(self):
        # Mạng lưới hoàn hảo -> chi phí 0
        self.assertEqual(self.problem.local_cost(GOAL_STATE), 0)
        # Vòng kín -> chi phí dương
        self.assertGreater(self.problem.local_cost(LOOP_STATE), 0)

    def test_real_input_solvable(self):
        from core.search import dfs
        problem = Pipes.from_file("data/input_pipes_4x4.json")
        result = dfs(problem)
        self.assertEqual(result.status, "solved")
        self.assertEqual(problem.local_cost(result.final_state), 0)


if __name__ == "__main__":
    unittest.main()

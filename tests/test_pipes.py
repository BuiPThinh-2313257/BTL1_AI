import unittest
import json
from puzzles.pipes import Pipes

# Giả lập dữ liệu 2x2 đơn giản để test logic cắt tỉa và heuristic
MOCK_DATA = {
  "grid_size": {"rows": 2, "cols": 2},
  "grid": [
    [
      {"row": 0, "col": 0, "type": "L-shape", "connections": ["right", "down"], "rotatable": True},
      {"row": 0, "col": 1, "type": "I-shape", "connections": ["left", "right"], "rotatable": True}
    ],
    [
      {"row": 1, "col": 0, "type": "I-shape", "connections": ["up", "down"], "rotatable": True},
      {"row": 1, "col": 1, "type": "L-shape", "connections": ["up", "left"], "rotatable": True}
    ]
  ]
}

class TestPipes(unittest.TestCase):
    def setUp(self):
        self.problem = Pipes(MOCK_DATA)

    def test_initial_state(self):
        self.assertEqual(self.problem.initial_state(), ())

    def test_goal_state(self):
        # Trạng thái đích giả lập (gán đủ 4 ô khớp nhau)
        goal_state = (
            ("right", "down"), ("left", "down"),
            ("up", "right"), ("up", "left")
        )
        self.assertTrue(self.problem.is_goal(goal_state))
        
        # Chưa gán đủ ô thì chưa phải đích
        incomplete_state = (("right", "down"),)
        self.assertFalse(self.problem.is_goal(incomplete_state))

    def test_local_cost(self):
        # Mạng lưới hoàn hảo -> chi phí 0
        perfect_state = (
            ("right", "down"), ("left", "down"),
            ("up", "right"), ("up", "left")
        )
        self.assertEqual(self.problem.local_cost(perfect_state), 0)
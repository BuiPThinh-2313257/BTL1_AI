"""Ghi lại từng bước tìm kiếm để GUI phát lại (step-by-step demo).

Định dạng file trace (JSON), phiên bản 1:

{
  "version": 1,
  "puzzle": "pipes",                 # Problem.name
  "algorithm": "astar",
  "input": "data/pipes_5x5_01.json", # tuỳ chọn, ai gọi thì điền
  "initial": <view>,                 # Problem.to_view(trạng thái đầu)
  "steps": [
    {"i": 0, "event": "expand", "state": <view>, "depth": 0,
     "g": 0, "h": 3.0, "frontier": 1, "explored": 0},
    {"i": 1, "event": "move", "state": <view>, "cost": 7.0, ...},
    ...
  ],
  "truncated": false,                # true nếu bị cắt vì quá max_steps
  "solution": [<view>, ...],         # đường đi từ đầu tới đích ([] nếu không giải được)
  "result": {...}                    # SearchResult.summary()
}

Các event:
- "expand":  giải thuật đang mở rộng một node (DFS/BFS/A*).
- "goal":    tìm thấy đích.
- "move":    tìm kiếm cục bộ chuyển sang lời giải lân cận.
- "restart": tìm kiếm cục bộ bắt đầu lại từ trạng thái ngẫu nhiên.
- "stuck":   tìm kiếm cục bộ kẹt ở cực trị địa phương.
Các trường khác trong mỗi step là tuỳ chọn; GUI chỉ cần "event" và "state".

TV4 có thể tạo trace giả theo đúng định dạng này để làm GUI trước.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

TRACE_VERSION = 1


class Trace:
    def __init__(self, problem, algorithm: str, max_steps: int = 5000,
                 every: int = 1, input_name: Optional[str] = None):
        """
        max_steps: số bước tối đa được lưu (tránh file trace khổng lồ).
        every:     chỉ lưu 1 trong mỗi `every` bước (vd every=10 cho bài lớn).
        """
        self.problem = problem
        self.algorithm = algorithm
        self.max_steps = max_steps
        self.every = max(1, every)
        self.input_name = input_name
        self.steps: List[Dict[str, Any]] = []
        self.truncated = False
        self._count = 0
        self.initial = None
        self.solution: List[Any] = []
        self.result: Dict[str, Any] = {}

    def start(self, state) -> None:
        self.initial = self.problem.to_view(state)

    def record(self, event: str, state, **info: Any) -> None:
        i = self._count
        self._count += 1
        important = event in ("goal", "restart", "stuck")
        if not important and i % self.every:
            return
        if len(self.steps) >= self.max_steps:
            self.truncated = True
            return
        step = {"i": i, "event": event, "state": self.problem.to_view(state)}
        step.update(info)
        self.steps.append(step)

    def finish(self, result) -> None:
        self.solution = [self.problem.to_view(s) for s in result.path]
        self.result = result.summary()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "version": TRACE_VERSION,
            "puzzle": getattr(self.problem, "name", "problem"),
            "algorithm": self.algorithm,
            "input": self.input_name,
            "initial": self.initial,
            "steps": self.steps,
            "truncated": self.truncated,
            "solution": self.solution,
            "result": self.result,
        }

    def save(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, ensure_ascii=False)


def load_trace(path: str) -> Dict[str, Any]:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if data.get("version") != TRACE_VERSION:
        raise ValueError(f"Trace phiên bản {data.get('version')} không hỗ trợ")
    return data

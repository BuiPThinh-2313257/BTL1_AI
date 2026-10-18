"""Interface chung cho mọi bài toán (Pipes, Kakurasu, ...).

Mỗi bài toán viết một lớp con của `Problem`. Các giải thuật trong
`core/search.py` chỉ gọi những hàm khai báo ở đây, nên không cần biết
bài toán cụ thể là gì.

Quy ước quan trọng:
- Trạng thái (state) phải *hashable* và *bất biến*: dùng tuple, frozenset,
  hoặc dataclass(frozen=True). Không dùng list/dict làm state.
- `successors` trả về các bộ (action, next_state, cost).
- `to_view` đổi state sang dạng JSON (list/dict/số/chuỗi) để GUI vẽ lại
  và để ghi vào trace.
"""

from __future__ import annotations

import random
from abc import ABC, abstractmethod
from typing import Any, Hashable, Iterable, Tuple

State = Hashable
Action = Any
Successor = Tuple[Action, State, float]


class Problem(ABC):
    #: Tên bài toán, ghi vào trace và bảng benchmark (vd "pipes", "kakurasu").
    name: str = "problem"

    # ------------------------------------------------------------------
    # Bắt buộc: dùng cho DFS, BFS, A*
    # ------------------------------------------------------------------
    @abstractmethod
    def initial_state(self) -> State:
        """Trạng thái ban đầu."""

    @abstractmethod
    def successors(self, state: State) -> Iterable[Successor]:
        """Các trạng thái kế tiếp hợp lệ, dạng (action, next_state, cost).

        Nên cắt tỉa ngay tại đây: chỉ trả về những bước chưa vi phạm luật.
        """

    @abstractmethod
    def is_goal(self, state: State) -> bool:
        """True nếu state là lời giải hợp lệ."""

    # ------------------------------------------------------------------
    # Tuỳ chọn
    # ------------------------------------------------------------------
    def heuristic(self, state: State) -> float:
        """Ước lượng chi phí còn lại tới đích (dùng cho A*, Greedy).

        Muốn A* cho lời giải tối ưu thì h không được đánh giá quá cao
        (admissible). Mặc định 0, khi đó A* chạy giống UCS.
        """
        return 0.0

    def to_view(self, state: State) -> Any:
        """Dạng JSON của state để GUI vẽ. Mặc định trả về list lồng nhau."""
        return _jsonable(state)

    # ------------------------------------------------------------------
    # Tuỳ chọn: dùng cho tìm kiếm cục bộ (Hill Climbing, Simulated Annealing)
    # Ở đây state là một *lời giải đầy đủ* (có thể sai), không phải lời giải
    # đang dựng dở.
    # ------------------------------------------------------------------
    def local_initial_state(self, rng: random.Random) -> State:
        """Một lời giải đầy đủ (có thể sai) để bắt đầu. Gọi lại khi restart."""
        raise NotImplementedError(f"{self.name} chưa hỗ trợ tìm kiếm cục bộ")

    def local_neighbors(self, state: State) -> Iterable[Tuple[Action, State]]:
        """Các lời giải lân cận (vd xoay đúng 1 ô), dạng (action, state)."""
        raise NotImplementedError(f"{self.name} chưa hỗ trợ tìm kiếm cục bộ")

    def local_cost(self, state: State) -> float:
        """Độ sai của lời giải; bằng 0 nghĩa là đã giải xong."""
        raise NotImplementedError(f"{self.name} chưa hỗ trợ tìm kiếm cục bộ")

    def local_random_neighbor(self, state: State, rng: random.Random) -> Tuple[Action, State]:
        """Một lân cận ngẫu nhiên (dùng cho Simulated Annealing).

        Mặc định chọn ngẫu nhiên trong local_neighbors; nên viết lại cho nhanh
        nếu số lân cận lớn.
        """
        return rng.choice(list(self.local_neighbors(state)))


def _jsonable(x: Any) -> Any:
    if isinstance(x, (str, int, float, bool)) or x is None:
        return x
    if isinstance(x, dict):
        return {str(k): _jsonable(v) for k, v in x.items()}
    if isinstance(x, (tuple, list)):
        return [_jsonable(v) for v in x]
    if isinstance(x, (set, frozenset)):
        return sorted((_jsonable(v) for v in x), key=repr)
    if hasattr(x, "__dict__"):
        return _jsonable(vars(x))
    return repr(x)

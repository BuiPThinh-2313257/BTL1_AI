"""Bài toán Kakurasu (TV3).

Luật (https://www.puzzle-kakurasu.com/):
- Tô đen một số ô trên lưới n x m.
- Khi tính tổng HÀNG, ô đen ở cột j (đánh số từ 1) có giá trị j.
- Khi tính tổng CỘT, ô đen ở hàng i (đánh số từ 1) có giá trị i.
- Tổng mỗi hàng phải bằng số bên phải, tổng mỗi cột bằng số bên dưới.

Mô hình hoá (DFS, BFS, A*):
- State: tuple 0/1 của các ô ĐÃ quyết định, theo thứ tự từng hàng, trong
  hàng từ trái sang phải. len(state) = số ô đã quyết định.
  Ví dụ lưới 4x4, state (0, 1, 0): ô (0,0) trắng, (0,1) đen, (0,2) trắng.
- Action: ((hàng, cột), 1) tô đen hoặc ((hàng, cột), 0) để trắng ô tiếp theo.
- Cost: 1 nếu tô đen, 0 nếu để trắng, nên g = số ô đen đã tô.
- Goal: đủ n*m ô và mọi tổng hàng/cột đúng bằng gợi ý.
- Heuristic: cận dưới số ô đen còn phải tô (admissible), xem `heuristic`.

Mức cắt tỉa trong `successors` (để so sánh trong báo cáo):
- "none":  không kiểm tra, chỉ xét khi đủ ô (brute force 2^(n*m)).
- "basic": bỏ nước đi làm tổng hàng/cột VƯỢT gợi ý.
- "full":  bỏ nước đi khiến phần còn thiếu của hàng/cột KHÔNG THỂ bù được
           bằng các ô còn lại (tra bảng tổng tập con tính sẵn).

Ví dụ:
    from core import astar, Limits
    from puzzles.kakurasu import Kakurasu
    p = Kakurasu.from_file("data/kakurasu_4x4_easy.json", prune="basic")
    res = astar(p, limits=Limits(time_limit=60))
    print(p.render(res.final_state))
"""

from __future__ import annotations

import json
import math

from core.problem import Problem

PRUNE_LEVELS = ("none", "basic", "full")


def subset_tables(n):
    """Bảng tổng tập con cho các giá trị 1..n.

    Với mỗi điểm bắt đầu s (1..n+1), xét các giá trị s, s+1, ..., n:
      reach[s]  = tập các tổng tạo được (mỗi giá trị dùng tối đa 1 lần)
      mincnt[s] = dict tổng -> số giá trị ít nhất để tạo ra tổng đó
    reach[n+1] = {0}: không còn giá trị nào thì chỉ tạo được tổng 0.
    """
    mincnt = [None] * (n + 2)
    mincnt[n + 1] = {0: 0}
    for s in range(n, 0, -1):
        cur = dict(mincnt[s + 1])                 # không lấy s
        for total, cnt in mincnt[s + 1].items():  # lấy s
            if cnt + 1 < cur.get(total + s, math.inf):
                cur[total + s] = cnt + 1
        mincnt[s] = cur
    reach = [None] + [frozenset(mincnt[s]) for s in range(1, n + 2)]
    return reach, mincnt


class Kakurasu(Problem):
    name = "kakurasu"

    def __init__(self, row_clues, col_clues, prune="full"):
        if prune not in PRUNE_LEVELS:
            raise ValueError(f"prune phải là một trong {PRUNE_LEVELS}")
        self.row_clues = tuple(row_clues)
        self.col_clues = tuple(col_clues)
        self.n = len(self.row_clues)   # số hàng
        self.m = len(self.col_clues)   # số cột
        self.size = self.n * self.m
        self.prune = prune
        # tổng HÀNG dùng giá trị là chỉ số cột 1..m, tổng CỘT dùng chỉ số hàng 1..n
        self._row_reach, self._row_min = subset_tables(self.m)
        self._col_reach, self._col_min = subset_tables(self.n)

    @classmethod
    def from_file(cls, path, prune="full"):
        with open(path, encoding="utf-8") as f:
            d = json.load(f)
        return cls(d["row_clues"], d["col_clues"], prune=prune)

    # ------------------------------------------------------------------
    # Hàm phụ
    # ------------------------------------------------------------------
    def sums(self, state):
        """Tổng hiện tại của từng hàng và từng cột."""
        rs = [0] * self.n
        cs = [0] * self.m
        for k, v in enumerate(state):
            if v:
                r, c = divmod(k, self.m)
                rs[r] += c + 1
                cs[c] += r + 1
        return rs, cs

    def to_grid(self, state):
        """Lưới n x m: 1 = đen, 0 = trắng, None = chưa quyết định."""
        cells = list(state) + [None] * (self.size - len(state))
        return [cells[r * self.m:(r + 1) * self.m] for r in range(self.n)]

    def _ok(self, state):
        """Ô vừa đặt (ô cuối của state) có hợp lệ theo mức cắt tỉa không.

        Chỉ cần xét hàng r và cột c của ô đó vì chỉ hai tổng này thay đổi.
        """
        if self.prune == "none":
            return True
        r, c = divmod(len(state) - 1, self.m)
        rs, cs = self.sums(state)
        need_r = self.row_clues[r] - rs[r]
        need_c = self.col_clues[c] - cs[c]
        if self.prune == "basic":
            return need_r >= 0 and need_c >= 0
        # hàng r còn các cột c+1..m-1, tức giá trị c+2..m
        # cột c còn các hàng r+1..n-1, tức giá trị r+2..n
        return need_r in self._row_reach[c + 2] and need_c in self._col_reach[r + 2]

    # ------------------------------------------------------------------
    # Interface Problem
    # ------------------------------------------------------------------
    def initial_state(self):
        return ()

    def successors(self, state):
        k = len(state)
        if k >= self.size:
            return
        cell = divmod(k, self.m)
        for v in (1, 0):
            s2 = state + (v,)
            if self._ok(s2):
                yield (cell, v), s2, v

    def is_goal(self, state):
        if len(state) != self.size:
            return False
        rs, cs = self.sums(state)
        return tuple(rs) == self.row_clues and tuple(cs) == self.col_clues

    def heuristic(self, state):
        """Cận dưới số ô đen còn phải tô.

        Mỗi hàng cần ít nhất mincnt ô (trong các cột còn trống của hàng) để bù
        phần còn thiếu; cộng mọi hàng được h_row. Tương tự cho cột được h_col.
        Mỗi ô đen thuộc đúng 1 hàng và 1 cột, nên số ô đen thật còn cần
        >= h_row và >= h_col, tức h = max(h_row, h_col) là admissible.
        Trả về inf nếu có hàng/cột không thể bù được (trạng thái chết).
        """
        r0, c0 = divmod(len(state), self.m)   # ô tiếp theo cần quyết định
        rs, cs = self.sums(state)

        h_row = 0
        for r in range(self.n):
            if r < r0:
                start = self.m + 1    # hàng đã điền xong
            elif r == r0:
                start = c0 + 1        # còn cột c0..m-1
            else:
                start = 1             # còn cả hàng
            cnt = self._row_min[start].get(self.row_clues[r] - rs[r])
            if cnt is None:
                return math.inf
            h_row += cnt

        h_col = 0
        for c in range(self.m):
            # cột c còn các hàng r0..n-1 nếu ô (r0, c) chưa điền, ngược lại r0+1..n-1
            start = r0 + 1 if c >= c0 else r0 + 2
            cnt = self._col_min[start].get(self.col_clues[c] - cs[c])
            if cnt is None:
                return math.inf
            h_col += cnt

        return max(h_row, h_col)

    def to_view(self, state):
        return {"rows": self.row_clues, "cols": self.col_clues,
                "grid": self.to_grid(state)}

    def render(self, state):
        """Chuỗi ASCII của lưới kèm gợi ý, để in ra màn hình."""
        sym = {1: "#", 0: ".", None: "?"}
        lines = [" ".join(sym[v] for v in row) + f" | {self.row_clues[r]}"
                 for r, row in enumerate(self.to_grid(state))]
        lines.append("-" * (2 * self.m - 1))
        lines.append(" ".join(str(c) for c in self.col_clues))
        return "\n".join(lines)


def verify(grid, row_clues, col_clues):
    """Kiểm tra một lưới 0/1 hoàn chỉnh có đúng luật không."""
    if len(grid) != len(row_clues) or any(len(row) != len(col_clues) for row in grid):
        return False
    if any(type(v) is not int or v not in (0, 1) for row in grid for v in row):
        return False
    for r, row in enumerate(grid):
        if sum(c + 1 for c, v in enumerate(row) if v) != row_clues[r]:
            return False
    for c in range(len(col_clues)):
        if sum(r + 1 for r, row in enumerate(grid) if row[c]) != col_clues[c]:
            return False
    return True

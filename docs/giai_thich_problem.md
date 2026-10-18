# Giải thích chi tiết `core/problem.py`

## 1. File này để làm gì?

`problem.py` định nghĩa lớp `Problem`, tức là **bản mô tả luật chơi**. Mọi bài toán (Pipes, Kakurasu, 8-puzzle...) đều phải viết theo đúng mẫu này.

Lý do: các giải thuật trong `search.py` (DFS, BFS, A\*, Hill Climbing) chỉ cần biết 4 điều:

1. Bắt đầu từ đâu?
2. Từ một trạng thái đi tiếp được tới đâu?
3. Thế nào là đã giải xong?
4. (Nếu có heuristic) còn cách đích bao xa?

Nếu mỗi bài toán trả lời 4 câu này bằng _cùng tên hàm_, thì **một hàm `dfs` duy nhất giải được mọi bài**. Đây là ý tưởng "tách bài toán khỏi giải thuật" trong sách AI (Russell & Norvig gọi là _problem formulation_). Nên trình bày ý này trong báo cáo.

```
   Pipes ─┐                       ┌─ dfs
Kakurasu ─┼──>  Problem (mẫu)  <──┼─ bfs
8-puzzle ─┘                       ├─ astar
                                  └─ hill_climbing
```

---

## 2. Phần đầu file

```python
from __future__ import annotations
import random
from abc import ABC, abstractmethod
from typing import Any, Hashable, Iterable, Tuple
```

- `from __future__ import annotations`: cho phép ghi kiểu dữ liệu (type hint) thoải mái mà không lỗi trên Python cũ. Không ảnh hưởng gì đến cách chạy.
- `ABC`, `abstractmethod`: công cụ để tạo **lớp trừu tượng**, xem mục 3.
- `typing`: chỉ để ghi chú kiểu cho dễ đọc. Python **không kiểm tra** những kiểu này khi chạy.

```python
State = Hashable
Action = Any
Successor = Tuple[Action, State, float]
```

Đây là **đặt tên tắt cho kiểu** để đọc code dễ hơn:

- `State`: trạng thái, phải _hashable_ (giải thích ở mục 5).
- `Action`: hành động, kiểu gì cũng được (chuỗi `"U"`, tuple `(hàng, cột, góc)`...).
- `Successor`: bộ 3 `(action, trạng_thái_mới, chi_phí)`.

---

## 3. `class Problem(ABC)`: lớp trừu tượng

```python
class Problem(ABC):
    name: str = "problem"
```

- `ABC` (Abstract Base Class) nghĩa là đây là **lớp khung**: không tạo đối tượng trực tiếp từ nó được, mà phải viết lớp con kế thừa.
- `name`: tên bài, được ghi vào trace và bảng CSV. Lớp con nên đặt lại, ví dụ `name = "pipes"`.

Các hàm có `@abstractmethod` là **bắt buộc**. Nếu lớp con quên viết một trong số đó, Python báo lỗi ngay khi tạo đối tượng:

```
TypeError: Can't instantiate abstract class Pipes with abstract method is_goal
```

Lỗi này có lợi, vì nó báo ngay là quên hàm, thay vì để chương trình chạy sai một cách âm thầm.

---

## 4. Ba hàm bắt buộc (cho DFS, BFS, A\*)

### 4.1 `initial_state(self)`

Trả về trạng thái ban đầu của đề bài.

- 8-puzzle: `(8, 6, 7, 2, 5, 4, 3, 0, 1)`.
- Kakurasu (điền từng hàng): `()`, tức là chưa điền hàng nào.
- Pipes (gán góc xoay từng ô): `()`, tức là chưa xoay ô nào.

### 4.2 `successors(self, state)`

**Đây là hàm quan trọng nhất.** Nó trả về mọi bước đi hợp lệ từ `state`, mỗi bước là bộ 3:

```python
(action, next_state, cost)
```

Ví dụ 8-puzzle: ô trống đang ở giữa thì có 4 successor, ứng với 4 hướng đẩy:

```python
yield "U", (1,0,3, 4,2,6, 7,5,8), 1
yield "D", ...
```

Có hai điểm cần chú ý:

- **Dùng `yield` thay cho `return list`.** Cách này sinh từng successor một nên tiết kiệm bộ nhớ, và DFS có thể dừng sớm.
- **Cắt tỉa (pruning) đặt ngay ở đây.** Với Pipes, khi thử xoay ô (r, c), nếu ống chĩa ra ngoài biên hoặc lệch với ô bên trái hay bên trên đã xoay, thì **không `yield`** nhánh đó. Hàm cắt tỉa càng chặt thì DFS càng nhanh, có khi nhanh hơn hàng nghìn lần. Đây là chỗ TV2, TV3 cần đầu tư nhiều nhất.

`cost` thường là 1 (mỗi bước tốn như nhau). A\* dùng nó để tính `g` (chi phí đã đi).

### 4.3 `is_goal(self, state)`

Trả về `True` nếu `state` là lời giải hợp lệ.

- Kakurasu: đã điền đủ n hàng và tổng mỗi cột khớp gợi ý.
- Pipes: đã xoay đủ mọi ô, mọi mối nối khớp, tất cả liên thông và không có vòng.

Lưu ý: kiểm tra liên thông và không vòng của Pipes chỉ làm được khi đã xoay hết, nên đặt ở `is_goal`. Còn những kiểm tra làm được sớm thì đặt trong `successors`.

---

## 5. Vì sao state phải là tuple (hashable)?

Mọi giải thuật đều lưu những state đã thăm vào `set` hoặc `dict` để không duyệt lại:

```python
parent[state] = ...      # trong dfs/bfs
if s2 in closed: ...     # trong astar
```

Mà `set` và `dict` chỉ nhận khoá **hashable**, tức là không đổi được nội dung:

| Kiểu                               | Hashable? | Dùng làm state?                                    |
| ---------------------------------- | --------- | -------------------------------------------------- |
| `tuple`, `frozenset`, `int`, `str` | có        | được                                               |
| `list`, `dict`, `set`              | không     | không, sẽ báo `TypeError: unhashable type: 'list'` |

Bảng 2 chiều thì dùng **tuple lồng tuple**: `((1,0,1), (0,1,0))`.

Lý do thứ hai: nếu state là list và một chỗ nào đó vô tình sửa nó, thì mọi node khác đang dùng chung list đó cũng bị sửa theo, gây lỗi rất khó tìm. Tuple không sửa được nên tránh hẳn lỗi này. Muốn đổi một phần tử thì tạo tuple mới:

```python
new = state[:c] + (r,) + state[c+1:]
```

---

## 6. Các hàm tuỳ chọn

### 6.1 `heuristic(self, state)`

Ước lượng **chi phí còn lại** từ `state` tới đích. Dùng cho A\* (f = g + h) và Greedy (f = h).

- Mặc định trả về `0`. Khi đó A\* hoạt động y như UCS, nghĩa là không có thông tin gì thêm.
- **Admissible**: h không bao giờ lớn hơn chi phí thật. A* chỉ đảm bảo lời giải *tối ưu\* khi h admissible.
- Ví dụ 8-puzzle dùng tổng khoảng cách Manhattan: mỗi ô cần ít nhất chừng đó bước mới về đúng chỗ, nên h không đánh giá quá cao.

Báo cáo nên giải thích vì sao heuristic của nhóm admissible, hoặc vì sao không admissible mà vẫn chấp nhận.

### 6.2 `to_view(self, state)`

Đổi state sang dạng **JSON** (list, dict, số, chuỗi) để:

- ghi vào file trace,
- cho GUI của TV4 vẽ lại.

Mặc định, hàm đổi tuple thành list (qua `_jsonable`). Nhưng nên viết lại cho dễ vẽ, ví dụ 8-puzzle trả về bảng 3x3:

```python
return [list(state[i:i+3]) for i in (0, 3, 6)]   # [[1,2,3],[4,5,6],[7,8,0]]
```

**TV2, TV3 và TV4 cần thống nhất format `to_view` của mỗi bài.** Ví dụ Pipes trả về `{"rows": 5, "cols": 5, "tiles": [[{"type": "T", "rot": 90}, ...]]}`.

---

## 7. Nhóm hàm cho tìm kiếm cục bộ (`local_*`)

Hill Climbing và Simulated Annealing làm việc theo cách khác hẳn DFS và A\*:

|               | DFS / BFS / A\*           | Hill Climbing / SA                   |
| ------------- | ------------------------- | ------------------------------------ |
| State là      | lời giải **đang dựng dở** | lời giải **đầy đủ nhưng có thể sai** |
| Bước đi       | điền thêm 1 phần          | sửa 1 chỗ (vd xoay lại 1 ô)          |
| Dừng khi      | `is_goal`                 | `local_cost == 0`                    |
| Nhớ đường đi? | có (cây tìm kiếm)         | không, chỉ nhớ state hiện tại        |

Vì vậy cần một bộ hàm riêng:

- **`local_initial_state(rng)`**: tạo một lời giải đầy đủ _ngẫu nhiên_. Với Pipes là xoay mọi ô một góc ngẫu nhiên. `rng` là bộ sinh số ngẫu nhiên do giải thuật truyền vào, nên dùng `rng.randrange(...)` thay cho `random.randrange(...)` để cố định được `seed` và chạy lại ra đúng kết quả cũ (cần cho benchmark).
- **`local_neighbors(state)`**: mọi lời giải "hàng xóm", tức là chỉ khác state một chút. Pipes: xoay đúng 1 ô sang góc khác. Trả về các cặp `(action, state_mới)`.
- **`local_cost(state)`**: đo độ sai, **0 nghĩa là đã giải xong**. Hill Climbing luôn đi về phía cost nhỏ hơn. Pipes: số mối nối lệch + (số mạng rời − 1).
- **`local_random_neighbor(state, rng)`**: lấy 1 hàng xóm ngẫu nhiên, dùng cho Simulated Annealing. Mặc định hàm sinh hết hàng xóm rồi chọn 1, khá chậm nếu có nhiều hàng xóm. Nên viết lại: chọn ngẫu nhiên 1 ô rồi xoay ngẫu nhiên.

Các hàm này không có `@abstractmethod` mà mặc định `raise NotImplementedError`. Lý do: bài nào không dùng Hill Climbing thì không cần viết chúng. Chỉ khi gọi `hill_climbing` trên bài chưa viết thì mới báo lỗi.

---

## 8. Hàm phụ `_jsonable(x)`

Đổi một giá trị Python bất kỳ sang dạng ghi được ra JSON, bằng cách xét lần lượt:

- số, chuỗi, `None`: giữ nguyên,
- `dict`: đổi khoá thành chuỗi, xử lý đệ quy giá trị,
- `tuple`, `list`: chuyển thành list và xử lý đệ quy từng phần tử,
- `set`, `frozenset`: chuyển thành list đã sắp xếp (JSON không có kiểu set),
- object có thuộc tính: lấy `vars(x)` (dict các thuộc tính),
- còn lại: `repr(x)` (dạng chuỗi).

Dấu `_` ở đầu tên là quy ước của Python cho hàm nội bộ, các file khác không nên gọi trực tiếp.

---

## 9. Ví dụ hoàn chỉnh: Kakurasu (bản rút gọn)

Đây là phác thảo để TV3 tham khảo. Nó chưa tối ưu và chưa có A\*.

```python
from itertools import combinations
from core.problem import Problem

class Kakurasu(Problem):
    name = "kakurasu"

    def __init__(self, row_clues, col_clues):
        self.n = len(row_clues)
        self.rows, self.cols = row_clues, col_clues
        # tính trước: mọi cách tô 1 hàng có tổng chỉ số cột = gợi ý hàng
        self.options = [self._subsets(c) for c in row_clues]

    def _subsets(self, target):
        idx = range(1, self.n + 1)
        return [frozenset(s) for k in range(self.n + 1)
                for s in combinations(idx, k) if sum(s) == target]

    def initial_state(self):
        return ()                       # chưa điền hàng nào

    def successors(self, state):
        r = len(state)                  # đang điền hàng r (0-based)
        if r == self.n:
            return
        for cells in self.options[r]:
            new = state + (cells,)
            if self._ok(new):           # cắt tỉa: không cột nào vượt gợi ý
                yield (r, tuple(sorted(cells))), new, 1

    def _col_sum(self, state, c):
        return sum(i + 1 for i, cells in enumerate(state) if c in cells)

    def _ok(self, state):
        return all(self._col_sum(state, c) <= self.cols[c - 1]
                   for c in range(1, self.n + 1))

    def is_goal(self, state):
        return len(state) == self.n and all(
            self._col_sum(state, c) == self.cols[c - 1] for c in range(1, self.n + 1))

    def to_view(self, state):
        return [[1 if c in (state[r] if r < len(state) else ()) else 0
                 for c in range(1, self.n + 1)] for r in range(self.n)]
```

Dùng:

```python
from core import dfs
p = Kakurasu(row_clues=[...], col_clues=[...])
print(dfs(p).status)
```

---

## 10. Checklist cho TV2 / TV3

- [ ] Lớp kế thừa `Problem`, đặt `name`.
- [ ] State là tuple hoặc frozenset, không dùng list.
- [ ] Viết `initial_state`, `successors` (có cắt tỉa), `is_goal`.
- [ ] Viết `heuristic` nếu dùng A\*, kèm giải thích admissible.
- [ ] Viết các hàm `local_*` nếu dùng Hill Climbing hoặc SA.
- [ ] Viết `to_view` theo format đã thống nhất với TV4.
- [ ] Viết test: giải được đề mẫu, lời giải đúng luật.

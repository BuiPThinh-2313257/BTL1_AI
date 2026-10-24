# Giải thích `puzzles/kakurasu.py` (TV3)

## 1. Luật chơi

Tô đen một số ô trên lưới n × m sao cho:
- Tổng mỗi **hàng** bằng số bên phải. Ô đen ở **cột j** (đánh số từ 1) có giá trị **j**.
- Tổng mỗi **cột** bằng số bên dưới. Ô đen ở **hàng i** có giá trị **i**.

Ví dụ `data/kakurasu_4x4_easy.json` (puzzle-kakurasu.com, ID 9272227):

```
 cột:  1 2 3 4
hàng1  . # . .  | 2   = 2
hàng2  . . . #  | 4   = 4
hàng3  # . # .  | 4   = 1 + 3
hàng4  . # # .  | 5   = 2 + 3
       -------
       3 5 7 2        cột 3 = 3 + 4 = 7
```

## 2. Mô hình hoá

| Thành phần | Cách làm |
|---|---|
| State | tuple 0/1 của các ô **đã quyết định**, theo thứ tự từng hàng, trong hàng từ trái sang phải. `()` là chưa quyết định ô nào |
| Action | `((hàng, cột), 1)` tô đen hoặc `((hàng, cột), 0)` để trắng ô tiếp theo |
| Cost | tô đen = 1, để trắng = 0, nên g = số ô đen đã tô |
| Goal | đủ n·m ô và mọi tổng hàng/cột đúng |
| Không gian trạng thái | tối đa 2^(n·m), ví dụ 9×9 là 2^81 |

Mỗi state chỉ có **đúng một đường** đi tới nên cây tìm kiếm không có trạng thái trùng.

`to_view` trả về `{"rows": [...], "cols": [...], "grid": [[1, 0, null, ...], ...]}`, trong đó `null` là ô chưa quyết định. GUI vẽ được cả lưới đang điền dở.

## 3. Bảng tổng tập con (`subset_tables`)

Câu hỏi cần trả lời nhanh: *"hàng này còn thiếu x điểm, các cột còn trống có giá trị s, s+1, …, m. Có bù được không, và cần ít nhất mấy ô?"*

Với giá trị 1..4:

```
reach[4] = {0, 4}
reach[3] = {0, 3, 4, 7}            <- không tạo được 1, 2, 5, 6
reach[2] = {0, 2, 3, 4, 5, 6, 7, 9}
mincnt[1][5] = 2                   (5 = 1 + 4 = 2 + 3)
```

Tính bằng quy hoạch động, đi lùi từ s = n về 1: với mỗi tổng đã có thì hoặc **không lấy** s, hoặc **lấy** s (tổng + s, số ô + 1). Bảng chỉ tính một lần trong `__init__`, sau đó mỗi lần tra là O(1).

## 4. Cắt tỉa trong `successors`

Khi đặt ô (r, c), chỉ hàng r và cột c thay đổi nên chỉ cần kiểm tra hai tổng đó:

| Mức | Điều kiện giữ nước đi |
|---|---|
| `none` | luôn giữ (brute force) |
| `basic` | tổng hàng và tổng cột **chưa vượt** gợi ý |
| `full` | phần còn thiếu của hàng **thuộc** `reach` của các cột còn lại, và phần còn thiếu của cột **thuộc** `reach` của các hàng còn lại |

Ví dụ: tô đen ô (1,1) của đề trên làm hàng 1 còn thiếu 1, nhưng các cột còn lại có giá trị ≥ 2. Mức `full` loại ngay; mức `basic` vẫn cho đi tiếp và phải đi sâu thêm mới phát hiện ra sai.

## 5. Heuristic (A*)

**h = cận dưới số ô đen còn phải tô.**

```
h_row = tổng theo các hàng của mincnt[cột còn trống][phần hàng còn thiếu]
h_col = tổng theo các cột của mincnt[hàng còn trống][phần cột còn thiếu]
h     = max(h_row, h_col)          (inf nếu có hàng/cột không thể bù được)
```

**Admissible:** mỗi ô đen thuộc đúng 1 hàng, nên số ô đen thật còn cần ≥ h_row. Tương tự, nó ≥ h_col. Vậy nó ≥ max(h_row, h_col).

Ở trạng thái đầu của đề 4×4: h_row = 1+1+1+2 = 5, h_col = 1+2+2+1 = 6, nên h = 6, bằng đúng số ô đen của lời giải. Vì vậy A* đi thẳng tới đích, chỉ mở rộng 16 node.

Heuristic trả về `inf` ở trạng thái chết, nên các trạng thái đó có độ ưu tiên sau mọi trạng thái có f hữu hạn. `core.search.astar` vẫn đưa chúng vào heap: khi không còn trạng thái hữu hạn (ví dụ đề vô nghiệm), chúng vẫn có thể được lấy ra và mở rộng. Đây là ưu tiên duyệt, không phải thao tác loại bỏ node. Với một lời giải hữu hạn còn trong frontier, A* ưu tiên đường đi đó trước các trạng thái có f = inf.

## 6. Kết quả sơ bộ trước 24/10/2026 (`core.search`, time_limit = 10 s)

Bảng này là ghi nhận sơ bộ của phiên bản ban đầu, không phải bộ đo có kiểm soát mới. Bảng đầy đủ 12 input, thời gian/bộ nhớ, giới hạn và phân tích ở [báo cáo TV3](bao_cao_tv3_kakurasu.md). Không gộp các số liệu có ngân sách khác nhau.

| Đề | DFS `basic` | BFS `basic` | A* `basic` | DFS `full` |
|---|---|---|---|---|
| 4×4 easy | 483 node | 638 node | 16 node | 16 node |
| 5×5 hard | 37 182 node, 0.44 s | quá giờ | 36 node | 25 node |
| 6×6 → 9×9 | quá giờ (trừ 6×6 easy) | quá giờ | ≤ 1 305 node, ≤ 0.04 s | ≤ 1 120 node, ≤ 0.01 s |

Kết luận cho báo cáo:
- Với cắt tỉa `basic`, tìm kiếm mù bùng nổ từ 5×5, còn A* giải hết đến 9×9.
- Với cắt tỉa `full`, DFS cũng giải hết. Cắt tỉa tốt quan trọng ngang heuristic tốt.

## 7. Cách dùng

```python
from core import astar, dfs, Limits, Trace
from puzzles.kakurasu import Kakurasu, verify

p = Kakurasu.from_file("data/kakurasu_6x6_hard.json", prune="basic")
r = astar(p, limits=Limits(time_limit=60))
print(r.status, r.nodes_expanded)
print(p.render(r.final_state))
print(verify(p.to_grid(r.final_state), p.row_clues, p.col_clues))
```

Trace mẫu cho GUI: `traces/example_kakurasu_4x4_dfs.json` (có quay lui, 485 bước) và `traces/example_kakurasu_4x4_astar.json` (18 bước).

## 8. Dữ liệu

`data/kakurasu_<n>x<n>_<easy|hard>.json`, gồm 12 đề thật lấy từ puzzle-kakurasu.com (4×4 đến 9×9):

```json
{"puzzle": "kakurasu", "name": "4x4_easy", "puzzle_id": "9272227",
 "rows": 4, "cols": 4, "row_clues": [2, 4, 4, 5], "col_clues": [3, 5, 7, 2]}
```

## 9. Hợp đồng kiểm tra lời giải và bàn giao

`verify(grid, row_clues, col_clues)` nhận lưới hoàn chỉnh đúng kích thước;
mỗi ô phải có kiểu `int` và giá trị 0 hoặc 1. `bool`, `float`, chuỗi và `None`
đều không hợp lệ. Sau đó hàm kiểm tra tổng có trọng số của từng hàng/cột.
Ô chưa quyết định chỉ xuất hiện trong `to_view`, không phải lời giải để `verify` chấp nhận.

Hai trace mẫu dùng cắt tỉa `basic`, mỗi quyết định một ô; `solution` chứa cả trạng thái
đầu nên có n*m+1 trạng thái. DFS có 485 sự kiện/483 node mở rộng; A* có 18 sự kiện/16
node mở rộng trên 4x4 easy. Kiểm thử so sánh JSON chuẩn hóa với trace sinh lại;
không so thời gian thực thi vì thời gian thay đổi theo máy và lần chạy.

Mô hình tối ưu hóa số ô đen (`g`), không phải số lần quyết định ô: mọi lời giải đầy đủ
đều có n*m hành động. BFS ưu tiên độ sâu nên không được dùng như bằng chứng tối ưu
số ô đen. DFS/BFS vẫn là tìm kiếm mù theo thứ tự duyệt, dù `full` dùng ràng buộc miền
bài toán để cắt tỉa. A* có thêm thứ tự ưu tiên theo `g+h`.

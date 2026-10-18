# core: phần dùng chung cho cả nhóm

Cả nhóm (TV2 Pipes, TV3 Kakurasu, TV4 GUI, TV5 benchmark) dùng chung bộ khung này. Chỉ cần Python 3, không cần thư viện ngoài.

```
core/problem.py   interface Problem mà mỗi bài toán phải viết
core/search.py    dfs, bfs, astar, greedy, hill_climbing, simulated_annealing
core/trace.py     ghi từng bước ra JSON để GUI phát lại
core/metrics.py   đo thời gian, bộ nhớ, số node, ghi CSV
puzzles/examples.py  2 bài mẫu (8-puzzle, N-Queens) làm khuôn
tests/test_core.py   chạy: python -m unittest discover tests
traces/           trace mẫu cho TV4 làm GUI
```

## TV2, TV3: viết bài toán

Tạo lớp con của `Problem` trong `puzzles/pipes.py` hoặc `puzzles/kakurasu.py`. Xem `puzzles/examples.py` để làm theo.

| Hàm | Bắt buộc? | Dùng cho |
|---|---|---|
| `initial_state()` | có | DFS, BFS, A* |
| `successors(state)` trả về `(action, next_state, cost)` | có | DFS, BFS, A* |
| `is_goal(state)` | có | DFS, BFS, A* |
| `heuristic(state)` | nếu dùng A*/Greedy | A*, Greedy |
| `to_view(state)` | nên có | GUI và trace |
| `local_initial_state(rng)`, `local_neighbors(state)`, `local_cost(state)` | nếu dùng tìm kiếm cục bộ | Hill Climbing, SA |

Lưu ý:
- **State phải là tuple** (hoặc kiểu bất biến, hashable). Không dùng list hay dict, vì giải thuật lưu state vào set/dict.
- **Cắt tỉa trong `successors`**: chỉ trả về các bước chưa vi phạm luật. DFS chạy nhanh hay chậm phụ thuộc gần như hoàn toàn vào phần này.
- Tìm kiếm cục bộ dùng *lời giải đầy đủ* (vd Pipes: mọi ô đều đã có góc xoay), còn DFS/A* dùng *lời giải đang dựng dở*. Hai kiểu state này có thể khác nhau.

Gợi ý cho từng bài:
- **Pipes**: DFS gán góc xoay lần lượt từng ô, `successors` bỏ góc xoay làm ống chĩa ra biên hoặc lệch với ô đã gán. Heuristic dùng `hill_climbing` với `local_cost` = số mối nối lệch + (số mạng rời − 1).
- **Kakurasu**: DFS điền từng hàng bằng các tập ô có tổng đúng gợi ý hàng, cắt khi cột vượt gợi ý. A* dùng chung `successors`, `heuristic` là phần còn thiếu của các cột chia cho chỉ số hàng lớn nhất còn lại.

## Chạy giải thuật

```python
from core import astar, dfs, hill_climbing, Limits, Trace
from puzzles.pipes import Pipes

p = Pipes.from_file("data/pipes_5x5_01.json")
res = dfs(p, limits=Limits(time_limit=60, max_nodes=2_000_000))
print(res.status, res.nodes_expanded, res.elapsed)
# status: solved | no_solution | node_limit | time_limit | stuck
```

Nên luôn truyền `Limits`, vì BFS trên lưới lớn có thể tràn RAM.

## TV4: trace cho GUI

```python
t = Trace(p, "dfs", max_steps=5000, every=1, input_name="pipes_5x5_01")
dfs(p, trace=t)
t.save("traces/pipes_5x5_01_dfs.json")
```

Định dạng file được mô tả đầu file `core/trace.py`. Mỗi bước có `event` (expand, goal, move, restart, stuck) và `state` (kết quả `to_view`). Có thể xem 2 file mẫu trong `traces/`. GUI có thể làm trước bằng trace giả cùng định dạng.

Bài lớn sinh trace rất dài, nên đặt `every=10` để cứ 10 bước lưu 1, hoặc giảm `max_steps`.

## TV5: benchmark

```python
from core import measure, write_csv, format_table, astar, dfs, Limits

rows = []
for name, problem in inputs:
    for algo in (dfs, astar):
        rows.append(measure(algo, problem, input_name=name,
                            limits=Limits(time_limit=120)))
print(format_table(rows))
write_csv(rows, "results/benchmark.csv")
```

- `measure` chạy 2 lần: một lần đo thời gian (`perf_counter`) và một lần đo bộ nhớ (`tracemalloc`, đơn vị KB). Tách ra vì tracemalloc làm chương trình chậm đi vài lần.
- Với Hill Climbing hay SA, hãy truyền `seed=...` để hai lần chạy giống nhau. Nên chạy vài seed rồi lấy trung bình.
- Cột CSV gồm: puzzle, input, algorithm, status, found, time_s, peak_kb, nodes_expanded, nodes_generated, max_frontier, max_depth, solution_length, restarts.

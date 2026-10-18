# Giải thích chi tiết `core/search.py`

## 1. File này để làm gì?

`search.py` chứa **toàn bộ các giải thuật tìm kiếm** của nhóm. Mỗi giải thuật là một hàm, nhận vào một `Problem` (xem `giai_thich_problem.md`) và trả về một `SearchResult`.

| Nhóm | Hàm | Dùng khi |
|---|---|---|
| Tìm kiếm mù (blind) | `dfs`, `bfs` | Bắt buộc theo đề: chọn 1 trong 2 |
| Có thông tin (informed) | `astar`, `greedy` | Có hàm `heuristic` tốt |
| Cục bộ (local) | `hill_climbing`, `simulated_annealing` | Có các hàm `local_*` |

Đề yêu cầu mỗi bài có 1 blind search và 1 heuristic search. Dự kiến của nhóm:

- **Pipes**: `dfs` và `hill_climbing` (hoặc `simulated_annealing`).
- **Kakurasu**: `dfs` và `astar`.

Các hàm còn lại có sẵn để so sánh thêm trong báo cáo.

Mọi hàm đều có chung cách gọi:

```python
result = ten_giai_thuat(problem, limits=Limits(...), trace=Trace(...))
```

`limits` và `trace` là tuỳ chọn, có thể bỏ qua.

---

## 2. Các trạng thái kết thúc (`status`)

```python
SOLVED      = "solved"       # tìm được lời giải
NO_SOLUTION = "no_solution"  # đã duyệt HẾT không gian mà không có lời giải
NODE_LIMIT  = "node_limit"   # dừng vì duyệt quá số node cho phép
TIME_LIMIT  = "time_limit"   # dừng vì chạy quá thời gian cho phép
STUCK       = "stuck"        # tìm kiếm cục bộ: hết lượt restart mà vẫn chưa giải được
```

Cần phân biệt `NO_SOLUTION` với `NODE_LIMIT` / `TIME_LIMIT`:

- `NO_SOLUTION`: **chắc chắn** đề vô nghiệm.
- `NODE_LIMIT` / `TIME_LIMIT`: **chưa biết**, chỉ là chạy chưa xong.

Trong bảng benchmark, những dòng bị limit nên ghi là "không giải kịp trong X giây", không được ghi là "vô nghiệm".

---

## 3. `Limits`: giới hạn để không treo máy

```python
@dataclass
class Limits:
    max_nodes: Optional[int] = None      # số node mở rộng tối đa
    time_limit: Optional[float] = None   # số giây tối đa
    max_depth: Optional[int] = None      # độ sâu tối đa, chỉ DFS dùng
```

- `@dataclass` giúp Python tự sinh hàm khởi tạo, nên chỉ cần viết `Limits(time_limit=60)`.
- Giá trị `None` nghĩa là không giới hạn.
- Ví dụ: `Limits(time_limit=60, max_nodes=2_000_000)` dừng khi quá 60 giây hoặc quá 2 triệu node, tuỳ điều kiện nào đến trước.

Vì sao cần giới hạn: BFS trên Pipes 7×7 có thể phải lưu hàng triệu state và làm tràn RAM. Có giới hạn thì giải thuật dừng gọn gàng và vẫn trả về số liệu để đưa vào báo cáo.

`max_depth` biến DFS thành **Depth-Limited Search**. Nếu gọi lặp lại với `max_depth` = 1, 2, 3... thì được **Iterative Deepening (IDS)**, có thể nhắc đến trong báo cáo.

---

## 4. `SearchResult`: kết quả trả về

| Trường | Ý nghĩa |
|---|---|
| `algorithm` | tên giải thuật (`"dfs"`, `"astar"`...) |
| `status` | trạng thái kết thúc (mục 2) |
| `path` | danh sách state từ đầu tới đích |
| `actions` | danh sách hành động tương ứng (ít hơn `path` 1 phần tử) |
| `cost` | tổng chi phí đường đi |
| `nodes_expanded` | số node đã **mở rộng** (đã gọi `successors`) |
| `nodes_generated` | số node con đã **sinh ra** |
| `max_frontier` | kích thước lớn nhất của frontier (stack, queue hoặc heap), phản ánh bộ nhớ |
| `max_depth` | độ sâu lớn nhất đã chạm tới |
| `restarts` | số lần restart (chỉ tìm kiếm cục bộ) |
| `elapsed` | thời gian chạy (giây) |
| `final_state` | state cuối cùng (lời giải nếu `SOLVED`) |

Thêm hai tiện ích:

- `result.found`: trả về `True` nếu `status == "solved"`. Đây là `@property`, tức là gọi như một biến, không có dấu `()`.
- `result.summary()`: gom kết quả thành dict gọn, dùng khi ghi trace hoặc CSV.

**Expanded và generated khác nhau thế nào?** Khi lấy node A ra để xét các con của nó, A được tính là 1 node *expanded*. Nếu A có 3 con thì có thêm 3 node *generated*. Cả hai đều nên đưa vào bảng so sánh.

---

## 5. Các hàm phụ

### 5.1 `_Guard`: người gác giới hạn

```python
guard = _Guard(limits)          # bắt đầu bấm giờ
stop = guard.check(expanded)    # None nếu còn được chạy, ngược lại trả về NODE_LIMIT/TIME_LIMIT
```

Chi tiết nhỏ: `check` chỉ đo thời gian **mỗi 256 node** (`(expanded & 255) == 0` tương đương với `expanded % 256 == 0`). Lý do là gọi đồng hồ liên tục cũng tốn thời gian. Cái giá là có thể chạy lố giới hạn một chút, không đáng kể.

### 5.2 `_rebuild(parent, goal)`: dựng lại đường đi

Các giải thuật không lưu cả đường đi trong mỗi node vì tốn bộ nhớ. Thay vào đó, chúng lưu một bảng:

```
parent[state] = (state_cha, action)      # state đầu thì parent = None
```

Khi tìm thấy đích, `_rebuild` lần ngược từ đích về gốc theo bảng này, rồi đảo ngược danh sách:

```
goal → cha → ông → ... → start      (lần ngược)
start → ... → ông → cha → goal      (đảo lại = đường đi)
```

### 5.3 `_finish(res, guard, trace)`

Ghi lại thời gian chạy vào `res.elapsed` và báo cho trace là đã xong. Mọi giải thuật đều gọi hàm này trước khi `return`.

---

## 6. DFS: Depth-First Search

**Ý tưởng:** luôn đi sâu nhất có thể theo một nhánh. Khi bị kẹt (hết đường hoặc bị cắt tỉa) thì quay lui (backtrack) sang nhánh khác. Frontier là một **stack** (LIFO: vào sau, ra trước).

```python
stack = [(start, None, None, 0, 0.0)]   # (state, cha, action, độ_sâu, chi_phí)
parent = {}                             # state đã thăm -> (cha, action)

while stack:
    state, par, act, depth, g = stack.pop()     # lấy phần tử CUỐI
    if state in parent: continue                # đã thăm rồi, bỏ qua
    parent[state] = ...                         # đánh dấu đã thăm
    (kiểm tra giới hạn, ghi trace)
    if problem.is_goal(state): ... return       # tìm thấy
    nodes_expanded += 1
    if đã chạm max_depth: continue
    children = [con chưa thăm]
    for con in reversed(children): stack.append(con)
```

Những điểm đáng chú ý:

- **Graph search**: dùng `parent` làm tập "đã thăm", nên không duyệt lại một state hai lần. Điều này tránh lặp vô hạn khi đồ thị có chu trình, ví dụ 8-puzzle đẩy qua đẩy lại.
- **Đánh dấu khi lấy ra (pop), không phải khi đưa vào (push)**: một state có thể nằm trong stack nhiều lần, và lần được lấy ra đầu tiên mới được tính. Cách này đảm bảo đúng thứ tự duyệt của DFS.
- **`reversed(children)`**: stack lấy phần tử cuối trước, nên đảo ngược để successor đầu tiên được xét trước, giống với DFS đệ quy.
- **Kiểm tra đích khi lấy ra**.

**Tính chất (đưa vào báo cáo):**

| | DFS |
|---|---|
| Đầy đủ (complete)? | Có, với không gian hữu hạn và graph search |
| Tối ưu? | **Không**, lời giải đầu tiên tìm được chưa chắc ngắn nhất |
| Thời gian | O(b^m) |
| Bộ nhớ (frontier) | O(b·m), nhỏ. Nhưng bảng `parent` vẫn lớn dần theo số state đã thăm |

(b = số nhánh trung bình, m = độ sâu tối đa.)

**Vì sao DFS hợp với Pipes và Kakurasu:** lời giải luôn nằm ở đúng độ sâu = số ô (Pipes) hoặc số hàng (Kakurasu), và mọi lời giải đều "ngắn như nhau". Vì vậy tính tối ưu không quan trọng, còn DFS tiết kiệm bộ nhớ hơn BFS rất nhiều.

---

## 7. BFS: Breadth-First Search

**Ý tưởng:** duyệt theo từng tầng. Xét hết các node ở độ sâu 1, rồi mới tới độ sâu 2, và cứ thế. Frontier là một **queue** (FIFO: vào trước, ra trước), dùng `collections.deque` vì lấy phần tử đầu nhanh (O(1)). Nếu dùng `list.pop(0)` thì mỗi lần lấy tốn O(n).

```python
parent = {start: None}
queue = deque([start])
while queue:
    state = queue.popleft()              # lấy phần tử ĐẦU
    nodes_expanded += 1
    for a, s2, c in problem.successors(state):
        if s2 in parent: continue        # đã thấy rồi
        parent[s2] = (state, a)          # đánh dấu NGAY khi sinh ra
        if problem.is_goal(s2): ... return   # kiểm tra đích ngay khi sinh
        queue.append(s2)
```

Khác với DFS:

- **Đánh dấu ngay khi sinh ra**, nên mỗi state chỉ vào queue một lần, tiết kiệm bộ nhớ.
- **Kiểm tra đích ngay khi sinh ra (early goal test)**, không đợi tới lúc lấy ra. Cách này bớt được cả một tầng node, mà tầng cuối thường là tầng lớn nhất.
- `depth_of` và `cost_of` lưu độ sâu và chi phí của từng state. `depth_of.pop(state)` vừa đọc vừa xoá, để bớt tốn bộ nhớ.

**Tính chất:**

| | BFS |
|---|---|
| Đầy đủ? | Có |
| Tối ưu? | **Có**, khi mọi bước có chi phí bằng nhau |
| Thời gian | O(b^d) |
| Bộ nhớ | O(b^d), **rất lớn**: phải lưu cả tầng hiện tại |

(d = độ sâu của lời giải nông nhất.)

Đây là lý do nên dùng DFS cho blind search của cả hai bài. Báo cáo có thể chạy BFS trên đề nhỏ để minh hoạ việc nó tốn bộ nhớ gấp nhiều lần.

---

## 8. A* và Greedy: tìm kiếm có thông tin

Hai giải thuật này dùng chung một hàm `_best_first`, chỉ khác **công thức độ ưu tiên**:

```python
def astar(...):  return _best_first(..., lambda g, h: g + h, ...)   # f = g + h
def greedy(...): return _best_first(..., lambda g, h: h,     ...)   # f = h
```

- `g` = chi phí **đã đi** từ đầu tới node này.
- `h` = `problem.heuristic(node)`, ước lượng chi phí **còn lại** tới đích.
- `lambda g, h: g + h` là một hàm viết gọn trên một dòng.

**Ý tưởng chung:** luôn mở rộng node có `f` **nhỏ nhất** trước. Frontier là một **hàng đợi ưu tiên** (priority queue), cài bằng `heapq`. `heappop` luôn lấy ra phần tử nhỏ nhất, mất O(log n).

```python
heap = [(f, h, counter, state)]
g_of = {start: 0}         # g tốt nhất đã biết của mỗi state
closed = set()            # các state đã mở rộng xong

while heap:
    f, h, _, state = heappop(heap)
    if state in closed: continue          # bản cũ, đã có đường tốt hơn
    closed.add(state)
    if problem.is_goal(state): ... return
    for a, s2, c in successors(state):
        g2 = g_of[state] + c
        if g2 < g_of.get(s2, vô_cùng):    # tìm được đường rẻ hơn tới s2
            g_of[s2] = g2
            parent[s2] = (state, a)
            closed.discard(s2)            # mở lại nếu cần
            heappush(heap, (g2 + h(s2), h(s2), counter, s2))
```

Chi tiết kỹ thuật:

- **Bộ `(f, h, counter, state)`**: heap so sánh các bộ từ trái sang phải.
  - So `f` trước.
  - Nếu `f` bằng nhau thì so `h`, ưu tiên node gần đích hơn. Đây là mẹo phá hoà giúp A* nhanh hơn.
  - Nếu vẫn bằng thì so `counter`, một số tăng dần (node vào trước ra trước). Nhờ có `counter`, heap **không bao giờ phải so sánh hai state**. Điều này quan trọng vì nhiều state không so sánh được, ví dụ frozenset.
- **Lazy deletion**: khi tìm được đường rẻ hơn tới `s2`, hàm không xoá bản cũ khỏi heap (xoá giữa heap rất chậm) mà đẩy thêm bản mới. Bản cũ sau này bị lấy ra thì bỏ qua nhờ dòng `if state in closed: continue`.
- **Mở lại node (reopen)**: nếu heuristic không *consistent*, có thể một node đã đóng lại tìm được đường rẻ hơn. Khi đó hàm xoá nó khỏi `closed` để mở rộng lại. Nhờ vậy A* vẫn cho kết quả tối ưu khi h chỉ admissible.

**Tính chất:**

| | A* | Greedy |
|---|---|---|
| Đầy đủ? | Có | Có (graph search, không gian hữu hạn) |
| Tối ưu? | **Có**, nếu h admissible | Không |
| Tốc độ | phụ thuộc chất lượng h | thường nhanh hơn A*, nhưng lời giải có thể dài |
| Bộ nhớ | lớn: lưu mọi node đã sinh | lớn |

Với h = 0, A* trở thành **UCS** (Uniform Cost Search). Báo cáo có thể so sánh A* có h và A* với h = 0 để chứng minh heuristic có ích.

---

## 9. Hill Climbing: leo đồi

**Ý tưởng:** bắt đầu từ một lời giải đầy đủ ngẫu nhiên (có thể sai). Ở mỗi bước, xét tất cả hàng xóm và **chuyển sang hàng xóm tốt nhất**, tức là có `local_cost` nhỏ nhất. Dừng khi cost = 0 (đã giải xong) hoặc khi không còn hàng xóm nào tốt hơn (kẹt).

Bản cài đặt này là **Steepest-Ascent Hill Climbing** có thêm hai cải tiến:

```python
for attempt in range(max_restarts + 1):          # (2) random restart
    state = problem.local_initial_state(rng)     # điểm xuất phát ngẫu nhiên
    cost = problem.local_cost(state)
    while True:
        if cost == 0: return SOLVED
        (tìm tất cả hàng xóm có cost nhỏ nhất -> best, best_cost)
        if best_cost > cost: break               # cực tiểu địa phương, kẹt
        if best_cost == cost:                    # (1) đi ngang
            sideways += 1
            if sideways > max_sideways: break    # đi ngang quá lâu, coi như kẹt
        else:
            sideways = 0
        state = rng.choice(best)                 # chọn ngẫu nhiên trong các hàng xóm tốt nhất
```

1. **Cho phép đi ngang (sideways move)**: khi không có hàng xóm tốt hơn nhưng có hàng xóm *bằng* cost hiện tại, vẫn cho đi tiếp, tối đa `max_sideways` bước liên tiếp. Cách này giúp thoát khỏi vùng bằng phẳng (plateau).
2. **Random restart**: khi kẹt thì bắt đầu lại từ một điểm ngẫu nhiên mới, tối đa `max_restarts` lần. Hết lượt mà vẫn chưa giải được thì trả về `STUCK`.

Thêm vài chi tiết:

- `rng.choice(best)`: khi nhiều hàng xóm cùng tốt nhất, chọn ngẫu nhiên một cái để không luôn đi theo một hướng.
- `rng = random.Random(seed)`: bộ sinh ngẫu nhiên riêng. Cùng `seed` thì cho kết quả giống hệt, cần thiết để benchmark lặp lại được.
- Ở đây `nodes_expanded` là số bước đã xét, còn `nodes_generated` là tổng số hàng xóm đã đánh giá.

**Tính chất:**

| | Hill Climbing |
|---|---|
| Đầy đủ? | **Không**, có thể kẹt ở cực tiểu địa phương (restart giúp giảm rủi ro này) |
| Tối ưu? | Không có khái niệm tối ưu ở đây, vì chỉ cần cost = 0 |
| Bộ nhớ | **Rất nhỏ**: chỉ nhớ state hiện tại |
| Đặc điểm | Kết quả phụ thuộc may rủi, nên chạy nhiều seed rồi lấy trung bình |

---

## 10. Simulated Annealing: mô phỏng luyện kim

**Ý tưởng:** giống Hill Climbing nhưng **đôi khi chấp nhận bước xấu hơn** để thoát khỏi cực tiểu địa phương. Xác suất chấp nhận bước xấu giảm dần theo "nhiệt độ" T.

```python
t = t0                                     # nhiệt độ ban đầu, vd 2.0
while t > t_min:
    if cost == 0: return SOLVED
    s2 = một hàng xóm NGẪU NHIÊN
    delta = cost(s2) - cost                # > 0 nghĩa là s2 tệ hơn
    if delta <= 0 or random() < exp(-delta / t):
        state = s2                         # chấp nhận
    t *= cooling                           # hạ nhiệt, vd nhân 0.995
```

- **delta ≤ 0** (tốt hơn hoặc bằng): luôn chấp nhận.
- **delta > 0** (tệ hơn): chấp nhận với xác suất `e^(−delta/T)`.
  - T lớn (lúc đầu): xác suất cao, thuật toán đi lung tung để khám phá.
  - T nhỏ (về sau): xác suất gần 0, thuật toán hoạt động gần giống Hill Climbing.
- **Lịch hạ nhiệt** dạng hình học: `T ← T × cooling`. Với `t0=2`, `cooling=0.995`, `t_min=0.001` thì mỗi lần chạy khoảng 1.500 bước. Muốn chạy lâu hơn thì tăng `cooling` lên, ví dụ 0.999.
- `best_state`: luôn nhớ state tốt nhất từng gặp. Nếu không giải được thì trả về state này.
- Có restart giống Hill Climbing (`max_restarts`).

Nên thử SA cho Pipes nếu Hill Climbing hay bị kẹt. Báo cáo có thể so sánh tỉ lệ giải được của hai cách.

---

## 11. `_safe(a)` và `ALGORITHMS`

- `_safe(a)`: đổi action sang dạng ghi được ra JSON (tuple thành list, object thành chuỗi) trước khi ghi vào trace.
- `ALGORITHMS`: dict ánh xạ tên sang hàm, tiện cho script benchmark hoặc GUI chọn giải thuật theo tên:

```python
from core.search import ALGORITHMS
algo = ALGORITHMS["astar"]
result = algo(problem)
```

---

## 12. Bảng tổng hợp cho báo cáo

| Giải thuật | Frontier | Đầy đủ | Tối ưu | Thời gian | Bộ nhớ |
|---|---|---|---|---|---|
| DFS | Stack | Có* | Không | O(b^m) | O(b·m) |
| BFS | Queue | Có | Có** | O(b^d) | O(b^d) |
| A* | Priority queue (g+h) | Có | Có*** | Tuỳ h, xấu nhất O(b^d) | O(b^d) |
| Greedy | Priority queue (h) | Có* | Không | Tuỳ h | Tuỳ h |
| Hill Climbing | Không có | Không | — | Tuỳ bài | O(1) |
| Sim. Annealing | Không có | Không**** | — | Tuỳ lịch hạ nhiệt | O(1) |

\* không gian hữu hạn, có kiểm tra state đã thăm.
\** khi mọi bước có cùng chi phí.
\*** khi h admissible.
\**** về lý thuyết, nếu hạ nhiệt đủ chậm thì sẽ tìm được lời giải.

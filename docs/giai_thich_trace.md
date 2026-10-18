# Giải thích chi tiết `core/trace.py`

## 1. File này để làm gì?

Đề bài khuyến khích có **demo step-by-step trực quan** (in ra chữ thì không đạt điểm tối đa). `trace.py` là cầu nối giữa giải thuật và giao diện:

```
 search.py  ──(mỗi bước gọi trace.record)──>  Trace  ──save()──>  file .json  ──>  GUI (TV4)
```

- Trong lúc chạy, giải thuật **ghi lại** mỗi bước: đang xét state nào, độ sâu bao nhiêu, frontier lớn cỡ nào...
- Chạy xong thì lưu ra **file JSON**.
- GUI chỉ cần **đọc file đó rồi phát lại** từng bước như xem video, có thể tua tới tua lui.

Tách ra như vậy có ba lợi ích:

1. **GUI không phải chạy giải thuật.** GUI chỉ làm việc vẽ, nên code đơn giản và không bị đơ khi giải thuật chạy lâu.
2. **Làm song song được.** TV4 viết GUI bằng file trace giả ngay từ đầu, không cần đợi TV2, TV3 code xong.
3. **Demo an toàn.** Trên lớp chỉ cần mở file trace đã lưu sẵn, không sợ giải thuật chạy chậm hay lỗi lúc trình bày.

---

## 2. Định dạng file trace (phiên bản 1)

Đây là file mẫu thật trong `traces/example_8puzzle_astar.json`, đã rút gọn:

```json
{
  "version": 1,
  "puzzle": "8puzzle",
  "algorithm": "astar",
  "input": "8puzzle_demo",
  "initial": [[4,1,3],[7,2,6],[0,5,8]],
  "steps": [
    {"i": 0, "event": "expand", "state": [[4,1,3],[7,2,6],[0,5,8]],
     "depth": 0, "g": 0.0, "h": 6, "f": 6.0, "frontier": 0, "explored": 1},
    {"i": 1, "event": "expand", "state": [[4,1,3],[0,2,6],[7,5,8]],
     "depth": 1, "g": 1.0, "h": 5, "f": 6.0, "frontier": 1, "explored": 2},
    ...
    {"i": 7, "event": "goal", "state": [[1,2,3],[4,5,6],[7,8,0]], ...}
  ],
  "truncated": false,
  "solution": [ [[4,1,3],...], ..., [[1,2,3],[4,5,6],[7,8,0]] ],
  "result": {"status": "solved", "solution_length": 6, "nodes_expanded": 6, ...}
}
```

| Trường | Ý nghĩa |
|---|---|
| `version` | phiên bản định dạng. Nếu sau này đổi cấu trúc thì tăng số này lên, để code đọc file cũ báo lỗi rõ ràng |
| `puzzle` | `problem.name`, GUI dựa vào đây để chọn cách vẽ (Pipes hay Kakurasu) |
| `algorithm` | tên giải thuật, hiện lên màn hình |
| `input` | tên đề (tuỳ chọn) |
| `initial` | trạng thái ban đầu, đã qua `to_view` |
| `steps` | danh sách các bước (mục 3) |
| `truncated` | `true` nếu bị cắt bớt vì quá `max_steps` |
| `solution` | các state trên đường đi từ đầu tới đích. Danh sách rỗng nếu không giải được |
| `result` | tóm tắt kết quả (`SearchResult.summary()`) |

Tất cả `state` trong file đều đã qua `problem.to_view(state)`. Vì vậy GUI nhận được dạng dễ vẽ như list hay dict, không phải tuple nội bộ của giải thuật.

---

## 3. Các loại bước (`event`)

| event | Do giải thuật nào sinh ra | Ý nghĩa | GUI nên hiển thị |
|---|---|---|---|
| `expand` | DFS, BFS, A*, Greedy | đang mở rộng node này | vẽ state, hiện độ sâu, g, h, kích thước frontier |
| `goal` | tất cả | tìm thấy lời giải | tô màu xanh, thông báo "Đã giải" |
| `move` | Hill Climbing, SA | chuyển sang lời giải lân cận | vẽ state mới, hiện `cost`, đánh dấu ô vừa đổi (`action`) |
| `restart` | Hill Climbing, SA | kẹt, bắt đầu lại từ điểm ngẫu nhiên | thông báo "Restart lần k" |
| `stuck` | Hill Climbing, SA | kẹt ở cực tiểu địa phương | tô màu đỏ hoặc cam |

Mỗi bước **luôn có** `i` (số thứ tự), `event` và `state`. Các trường khác là tuỳ chọn và phụ thuộc giải thuật:

- DFS: `depth`, `g`, `frontier`, `explored`.
- A*: thêm `h`, `f`.
- Hill Climbing: `cost`, `action`, `restart`.
- SA: thêm `temp` (nhiệt độ).

GUI nên đọc bằng `step.get("h")` để không lỗi khi một trường không có.

---

## 4. Lớp `Trace`

### 4.1 Tạo trace

```python
t = Trace(problem, "dfs", max_steps=5000, every=1, input_name="pipes_5x5_01")
```

| Tham số | Ý nghĩa |
|---|---|
| `problem` | bài toán, dùng để gọi `to_view` và lấy `name` |
| `algorithm` | tên giải thuật, ghi vào file |
| `max_steps` | số bước **tối đa** được lưu (mặc định 5000). Quá số này thì ngừng lưu và đặt `truncated = True` |
| `every` | chỉ lưu **1 trong mỗi `every` bước**. `every=10` nghĩa là cứ 10 bước lưu 1 |
| `input_name` | tên đề, ghi vào trường `input` |

Vì sao cần `max_steps` và `every`: DFS trên Pipes 7×7 có thể duyệt hàng triệu node. Lưu hết thì file trace nặng hàng GB và GUI không mở nổi. Thường chỉ cần vài trăm đến vài nghìn bước là đủ để demo.

### 4.2 Các hàm (giải thuật tự gọi, nhóm không cần gọi tay)

**`start(state)`**: giải thuật gọi một lần lúc bắt đầu để lưu `initial`.

**`record(event, state, **info)`**: ghi một bước. `**info` nghĩa là nhận bao nhiêu tham số có tên cũng được (`depth=..., g=...`), tất cả được gom vào dict của bước đó.

```python
def record(self, event, state, **info):
    i = self._count;  self._count += 1            # đếm MỌI bước, kể cả bước không lưu
    important = event in ("goal", "restart", "stuck")
    if not important and i % self.every:          # bỏ qua nếu không tới lượt lưu
        return
    if len(self.steps) >= self.max_steps:         # đầy rồi thì không lưu nữa
        self.truncated = True
        return
    self.steps.append({"i": i, "event": event,
                       "state": self.problem.to_view(state), **info})
```

Chi tiết đáng chú ý:

- `i` là **số thứ tự thật** của bước, kể cả khi `every` > 1. Ví dụ với `every=10` thì các bước được lưu có `i` = 0, 10, 20... GUI có thể hiện "bước 20 / 15342".
- Các event **quan trọng** (`goal`, `restart`, `stuck`) luôn được lưu, kể cả khi không tới lượt theo `every`. Nhờ vậy GUI không bao giờ bỏ sót khoảnh khắc tìm thấy lời giải.
- Hàm chỉ gọi `to_view` khi thật sự lưu, nên các bước bị bỏ qua không tốn thời gian chuyển đổi.

Lưu ý: trường hợp hiếm là trace đã đầy `max_steps` trước khi tới `goal` thì bước `goal` cũng không được lưu. Khi đó GUI vẫn có `solution` và `result` để hiện kết quả cuối cùng. Muốn chắc có bước `goal` thì tăng `max_steps` hoặc tăng `every`.

**`finish(result)`**: giải thuật gọi khi xong, để lưu `solution` (đổi từng state qua `to_view`) và `result`.

**`to_dict()`**: gom mọi thứ thành một dict theo đúng định dạng ở mục 2.

**`save(path)`**: ghi ra file JSON. `ensure_ascii=False` để chữ tiếng Việt (nếu có) được giữ nguyên, không bị đổi thành dạng `ạ`.

### 4.3 Hàm `load_trace(path)`

GUI dùng hàm này để đọc file. Hàm kiểm tra `version`, nếu không khớp thì báo lỗi rõ ràng thay vì để GUI vẽ sai.

```python
from core.trace import load_trace
data = load_trace("traces/pipes_5x5_01_dfs.json")
for step in data["steps"]:
    ve(step["state"])   # hàm vẽ của GUI
```

---

## 5. Cách dùng đầy đủ

### Ghi trace (TV2, TV3, TV5)

```python
from core import dfs, hill_climbing, Trace, Limits
from puzzles.pipes import Pipes

p = Pipes.from_file("data/pipes_5x5_01.json")

t = Trace(p, "dfs", max_steps=3000, input_name="pipes_5x5_01")
dfs(p, limits=Limits(time_limit=60), trace=t)
t.save("traces/pipes_5x5_01_dfs.json")

t = Trace(p, "hill_climbing", input_name="pipes_5x5_01")
hill_climbing(p, trace=t, seed=42)
t.save("traces/pipes_5x5_01_hc.json")
```

### Tạo trace giả để làm GUI trước (TV4)

Không cần giải thuật, chỉ cần viết dict đúng định dạng:

```python
import json
fake = {
  "version": 1, "puzzle": "kakurasu", "algorithm": "dfs", "input": "demo",
  "initial": [[0,0,0],[0,0,0],[0,0,0]],
  "steps": [
    {"i": 0, "event": "expand", "state": [[0,0,0],[0,0,0],[0,0,0]], "depth": 0},
    {"i": 1, "event": "expand", "state": [[1,0,1],[0,0,0],[0,0,0]], "depth": 1},
    {"i": 2, "event": "goal",   "state": [[1,0,1],[0,1,0],[1,1,0]], "depth": 3},
  ],
  "truncated": False, "solution": [], "result": {"status": "solved"}
}
json.dump(fake, open("traces/fake_kakurasu.json", "w"))
```

---

## 6. Lưu ý quan trọng

- **Ghi trace làm giải thuật chậm đi**, vì mỗi bước phải gọi `to_view` và tạo dict. Do đó khi **đo thời gian cho bảng benchmark thì không truyền `trace`**. Trace chỉ dùng cho demo.
- **Format `to_view` của mỗi bài phải được TV2, TV3 và TV4 thống nhất sớm**, vì GUI vẽ dựa trên nó. Ví dụ:
  - Kakurasu: `[[0,1,0,...], ...]` (ma trận 0/1) kèm gợi ý hàng và cột.
  - Pipes: `[[{"type": "L", "rot": 90}, ...], ...]` hoặc `null` cho ô chưa xoay (khi chạy DFS).
- Để demo trên lớp, chọn đề **nhỏ** (vd 4×4, 5×5) để trace ngắn và người xem theo kịp.

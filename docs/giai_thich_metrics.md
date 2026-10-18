# Giải thích chi tiết `core/metrics.py`

## 1. File này để làm gì?

Đề bài bắt buộc:

> "Trong báo cáo, sinh viên phải trình bày **bảng số liệu về thời gian và sự tiêu tốn bộ nhớ** của từng giải thuật đối với các input, và giải thích."

`metrics.py` lo việc **đo** các số liệu đó và **xuất ra bảng**:

- **Thời gian chạy** (giây).
- **Bộ nhớ đỉnh** (KB): lúc tốn bộ nhớ nhất trong quá trình chạy.
- **Số node**: số node mở rộng, số node sinh ra, frontier lớn nhất (lấy từ `SearchResult`).
- Xuất ra **CSV** (mở bằng Excel hoặc Google Sheets để vẽ biểu đồ) và **bảng text** in ra màn hình.

Người dùng chính là TV5 (benchmark). TV1 dùng số liệu này để viết phần phân tích trong báo cáo.

---

## 2. Ví dụ kết quả thật

Chạy 3 giải thuật trên một đề 8-puzzle khó (cần 31 bước):

```
puzzle    input           algo                status         time(s)    mem(KB)   expanded      len
---------------------------------------------------------------------------------------------------
8puzzle   8p_hard         bfs                 solved          1.2786    61018.1     181347       31
8puzzle   8p_hard         astar               solved          0.0377     3761.4       6744       31
8puzzle   8p_hard         dfs                 solved          0.7378    49025.8     148344   107823
```

Từ bảng này có thể rút ra những nhận xét đúng kiểu báo cáo cần có:

- **A\*** chỉ mở rộng 6.744 node, ít hơn BFS **27 lần**, nhanh hơn khoảng 34 lần và tốn bộ nhớ ít hơn khoảng 16 lần. Đó là nhờ heuristic Manhattan dẫn đường.
- **BFS** tìm được lời giải tối ưu (31 bước) nhưng tốn bộ nhớ nhất, vì phải lưu cả tầng.
- **DFS** cũng giải được nhưng lời giải dài **107.823 bước**. Điều này minh hoạ đúng tính chất "DFS không tối ưu".

---

## 3. Cách đo, và vì sao đo như vậy

### 3.1 Thời gian: `time.perf_counter()`

```python
t0 = time.perf_counter()
result = algorithm(problem, ...)
time_s = time.perf_counter() - t0
```

- `perf_counter` là đồng hồ chính xác nhất trong Python (độ phân giải tới micro giây), chuyên dùng để đo hiệu năng.
- Không dùng `time.time()` vì nó kém chính xác hơn và có thể bị nhảy khi máy tự chỉnh giờ.

### 3.2 Bộ nhớ: `tracemalloc`

`tracemalloc` là module có sẵn của Python, **theo dõi mọi lần Python cấp phát bộ nhớ**.

```python
tracemalloc.start()
tracemalloc.reset_peak()                  # xoá mốc đỉnh cũ
base, _ = tracemalloc.get_traced_memory() # bộ nhớ đang dùng TRƯỚC khi chạy
algorithm(problem, ...)
_, peak = tracemalloc.get_traced_memory() # đỉnh bộ nhớ TRONG lúc chạy
tracemalloc.stop()
peak_kb = (peak - base) / 1024
```

- Đo **đỉnh (peak)**, không đo lượng còn lại sau khi chạy. Lúc tốn nhất chính là giới hạn thực tế, ví dụ khi BFS giữ cả tầng lớn nhất trong queue.
- Trừ `base` để chỉ tính phần **giải thuật dùng thêm**, không tính những gì đã có sẵn từ trước (đề bài, các module đã import).
- Kết quả tính bằng **KB** (chia 1024).

Lưu ý khi viết báo cáo: `tracemalloc` chỉ đo bộ nhớ do **Python cấp phát** (các object, dict, set, tuple...). Nó không đo toàn bộ RAM của tiến trình như Task Manager. Đây vẫn là thước đo phù hợp để **so sánh giữa các giải thuật**, vì mọi giải thuật đều được đo cùng một cách.

### 3.3 Vì sao chạy 2 lần?

Bật `tracemalloc` làm chương trình **chậm đi 2–5 lần**, vì Python phải ghi chép mọi lần cấp phát. Nếu đo thời gian trong lúc bật `tracemalloc`, số thời gian sẽ sai.

Vì vậy `measure()` làm như sau:

1. **Lần 1**: tắt `tracemalloc` và đo **thời gian**.
2. **Lần 2**: bật `tracemalloc` và đo **bộ nhớ**. Thời gian của lần này bị bỏ.

Cả hai lần chạy cùng một đề với cùng giải thuật nên đi qua đúng các bước như nhau. Riêng giải thuật ngẫu nhiên thì phải truyền `seed`, xem mục 6.

### 3.4 `gc.collect()`

Trước mỗi lần đo, hàm gọi bộ dọn rác của Python để dọn hết rác từ lần chạy trước. Nhờ vậy lần đo sau không bị ảnh hưởng bởi lần đo trước.

---

## 4. Các hàm trong file

### 4.1 `measure(...)`: hàm chính

```python
m = measure(algorithm, problem, limits=None, input_name="", track_memory=True, trace=None, **kwargs)
```

| Tham số | Ý nghĩa |
|---|---|
| `algorithm` | hàm giải thuật, vd `astar` (truyền tên hàm, **không** có `()`) |
| `problem` | bài toán |
| `limits` | `Limits(...)` để không chạy mãi |
| `input_name` | tên đề, ghi vào cột `input` của bảng |
| `track_memory` | `False` để bỏ lần đo bộ nhớ (nhanh gấp đôi, cột `peak_kb` để trống) |
| `trace` | gắn trace vào lần chạy đo thời gian (nhưng khi benchmark thì **không nên**, vì làm sai số thời gian) |
| `**kwargs` | tham số riêng của giải thuật, được chuyển thẳng xuống, vd `seed=1, max_restarts=100` cho Hill Climbing |

Hàm trả về đối tượng `Metrics`.

### 4.2 `Metrics`: kết quả một lần đo

```python
@dataclass
class Metrics:
    puzzle: str          # tên bài
    input: str           # tên đề
    algorithm: str       # tên giải thuật
    time_s: float        # thời gian (giây)
    peak_kb: float|None  # bộ nhớ đỉnh (KB), None nếu không đo
    result: SearchResult # kết quả đầy đủ của giải thuật
```

`m.row()` trả về một dict phẳng, ứng với một dòng của bảng CSV.

### 4.3 `peak_memory_kb(...)`

Hàm này chỉ đo bộ nhớ, `measure` gọi nó ở lần chạy thứ 2. Có thể gọi riêng nếu chỉ cần số bộ nhớ.

Chi tiết nhỏ: nếu `tracemalloc` đã được bật từ trước (`was_tracing`), hàm không tắt nó đi sau khi đo, để không phá phần code khác đang dùng. Khối `try/finally` đảm bảo `tracemalloc` luôn được tắt, kể cả khi giải thuật báo lỗi giữa chừng.

### 4.4 `write_csv(metrics, path, append=False)`

Ghi danh sách `Metrics` ra file CSV.

- Tự tạo thư mục nếu chưa có (`os.makedirs(..., exist_ok=True)`).
- `append=False`: ghi đè file mới, có dòng tiêu đề.
- `append=True`: ghi **nối tiếp** vào file cũ, chỉ ghi tiêu đề nếu file chưa tồn tại. Tiện khi chạy benchmark nhiều đợt.
- `newline=""` là yêu cầu của module `csv` để không bị dòng trống xen kẽ khi mở trên Windows.
- `encoding="utf-8"` để không lỗi tiếng Việt.

Các cột của file CSV:

| Cột | Ý nghĩa |
|---|---|
| `puzzle`, `input`, `algorithm` | bài, đề, giải thuật |
| `status`, `found` | trạng thái kết thúc, có giải được không |
| `time_s` | thời gian (giây) |
| `peak_kb` | bộ nhớ đỉnh (KB) |
| `nodes_expanded`, `nodes_generated` | số node mở rộng và số node sinh ra |
| `max_frontier` | frontier lớn nhất |
| `max_depth` | độ sâu lớn nhất |
| `solution_length` | độ dài lời giải (số bước) |
| `restarts` | số lần restart (Hill Climbing, SA) |

### 4.5 `format_table(metrics)`

Trả về một chuỗi bảng gọn như ví dụ ở mục 2, để `print()` ra màn hình xem nhanh. Các cột được canh lề bằng f-string (`:<10` canh trái rộng 10 ký tự, `:>11` canh phải rộng 11 ký tự).

---

## 5. Ví dụ script benchmark (gợi ý cho TV5)

```python
from core import measure, write_csv, format_table, dfs, astar, hill_climbing, Limits
from puzzles.kakurasu import Kakurasu
from puzzles.pipes import Pipes

LIM = Limits(time_limit=120, max_nodes=5_000_000)
rows = []

for name in ["kakurasu_4x4_01", "kakurasu_5x5_01", "kakurasu_6x6_01"]:
    p = Kakurasu.from_file(f"data/{name}.json")
    for algo in (dfs, astar):
        rows.append(measure(algo, p, limits=LIM, input_name=name))

for name in ["pipes_4x4_01", "pipes_5x5_01", "pipes_7x7_01"]:
    p = Pipes.from_file(f"data/{name}.json")
    rows.append(measure(dfs, p, limits=LIM, input_name=name))
    for seed in range(5):            # thuật toán ngẫu nhiên: chạy nhiều seed
        rows.append(measure(hill_climbing, p, limits=LIM,
                            input_name=f"{name}#seed{seed}", seed=seed))

print(format_table(rows))
write_csv(rows, "results/benchmark.csv")
```

---

## 6. Lưu ý khi benchmark

1. **Luôn đặt `Limits`.** Không có giới hạn thì BFS hoặc DFS trên đề lớn có thể chạy cả ngày hoặc làm tràn RAM.
2. **Không truyền `trace` khi đo**, vì ghi trace tốn thời gian và làm sai số liệu.
3. **Giải thuật ngẫu nhiên phải có `seed`**, vì 2 lần chạy trong `measure` cần đi giống hệt nhau. Ngoài ra nên chạy **nhiều seed** (vd 5–10) rồi báo cáo trung bình, cùng tỉ lệ giải được.
4. **Chạy mỗi đề vài lần rồi lấy trung bình hoặc trung vị.** Thời gian dao động theo máy và theo các chương trình khác đang chạy. Nên tắt bớt ứng dụng nặng khi benchmark.
5. **Ghi rõ cấu hình máy** (CPU, RAM, phiên bản Python) trong báo cáo, vì số liệu thời gian chỉ có ý nghĩa khi kèm cấu hình.
6. **Dòng bị limit** (`status` = `time_limit` hoặc `node_limit`) nên ghi là "> 120 s" trong bảng, không được ghi là vô nghiệm.
7. Thời gian nhỏ quá (< 0,001 giây) thì kém tin cậy. Khi đó dùng **số node** để so sánh, vì số node không phụ thuộc máy.

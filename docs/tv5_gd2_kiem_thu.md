
# TV5 — TỔNG KẾT KIỂM THỬ TÍCH HỢP
## Giai đoạn 2 — Bài tập lớn Nhập môn AI

**Bài toán:** Pipes và Kakurasu  
**Thành viên:** TV5 — Dữ liệu và Benchmark

---

## 1. Mục tiêu

Giai đoạn 2 tập trung kiểm thử tích hợp các thành phần tìm kiếm, mô hình bài toán và bộ dữ liệu.

TV5 thực hiện:

- Kiểm tra cấu trúc các input JSON.
- Kiểm tra lời giải độc lập bằng `verify.py`.
- Chạy thử các thuật toán đã được nhóm triển khai.
- Đo thử thời gian, bộ nhớ và số node.
- Phát hiện, ghi nhận và báo lỗi tích hợp.
- Chuẩn bị công cụ benchmark cho Giai đoạn 3.

TV5 không tự ý sửa thuật toán hoặc heuristic của TV1, TV2 và TV3.

## 2. Phạm vi kiểm thử

| Puzzle | Thuật toán |
|---|---|
| Kakurasu | DFS, A* |
| Pipes | DFS, Hill Climbing |

Các file TV5 sử dụng:

- `verify.py`
- `benchmark.py`
- `tests/test_verify.py`
- `tests/test_benchmark.py`
- `core/metrics.py`
- `core/search.py`

## 3. Phương pháp kiểm thử

Các chương trình được chạy bằng Python 3 tại thư mục gốc của repository.

Lệnh kiểm tra JSON:

```powershell
py verify.py
```

Lệnh unit test:

```powershell
py -m unittest discover -s tests -p "test_*.py" -v
```

Lệnh kiểm thử Kakurasu:

```powershell
py benchmark.py --puzzle kakurasu --inputs kakurasu_4x4_easy.json --repeats 1 --max-nodes 50000 --time-limit 5 --strict --output results/tv5-gd2-kakurasu-recheck
```

Lệnh kiểm thử Pipes:

```powershell
py benchmark.py --puzzle pipes --inputs input_pipes_4x4.json --repeats 1 --max-nodes 50000 --time-limit 5 --strict --output results/tv5-gd2-pipes-recheck
```

Nếu thư mục kết quả đã tồn tại, cần thay tên `--output`.

Lời giải chỉ được công nhận khi:

`status=solved` và `verified=True`.

Các trường hợp chạm giới hạn node hoặc thời gian không được xem là lời giải thành công, nhưng cũng không chứng minh bài toán vô nghiệm.

## 4. Kết quả kiểm thử

### 4.1. Kiểm tra dữ liệu

Có 13/13 file JSON hợp lệ về cấu trúc:

- 12 file Kakurasu.
- 1 file Pipes 4×4.

Kết quả này chưa có nghĩa tất cả input đều được chứng minh có lời giải.

### 4.2. Unit test

Bộ source sau cập nhật có:

**59/59 unit test đạt.**

Các bài test bao gồm thuật toán, mô hình puzzle, GUI, xác thực lời giải và benchmark.

### 4.3. Kiểm thử solver

Cấu hình: `max_nodes=50000`, `time_limit=5`, Kakurasu dùng `prune=basic`, Hill Climbing dùng seed 0.

| Input | Thuật toán | Status | Verified | Expanded nodes |
|---|---|---|---|---:|
| Kakurasu 4×4 Easy | DFS | solved | True | 483 |
| Kakurasu 4×4 Easy | A* | solved | True | 16 |
| Pipes 4×4 | DFS | solved | True | 16 |
| Pipes 4×4 | Hill Climbing | solved | True | 21 |

Bảng trên chỉ là kiểm thử tích hợp trên các input đại diện.

Số liệu benchmark đầy đủ được trình bày riêng tại báo cáo Giai đoạn 3.

## 5. Lịch sử và xử lý lỗi Pipes

### 5.1. Lỗi trước khi TV2 sửa

Trong phiên bản cũ:

- `Pipes.is_goal()` chưa loại trừ đúng các vòng kín.
- `local_cost()` chưa đánh giá đầy đủ điều kiện cấm chu trình.
- Input Pipes cũ không phù hợp với mạng liên thông không chu trình.
- DFS và Hill Climbing có thể báo `solved`, nhưng TV5 xác thực `False`.

TV5 đã phát hiện lỗi qua `verify.py` và ghi nhận vào `integration_issues.csv`.

### 5.2. Sau khi sửa

TV2 đã cập nhật:

- `puzzles/pipes.py`
- `data/input_pipes_4x4.json`
- Các bài test liên quan.

Input mới gồm:

- 2 ô Dead-end.
- 8 ô I-shape.
- 6 ô L-shape.

Tổng số đầu nối bằng 30, phù hợp điều kiện cần của mạng cây gồm 16 đỉnh.

Sau khi cập nhật:

- DFS giải đúng input 4×4.
- Hill Climbing seed 0 giải đúng input 4×4.
- `verify_pipes()` xác nhận `True`.

Benchmark ba lượt cho mỗi thuật toán cũng ghi nhận 6/6 lượt hợp lệ.

Ngoài ra, năm seed Hill Climbing từ 0 đến 4 đều trả lời giải hợp lệ trên input này.

### 5.3. Lưu ý kỹ thuật còn lại

Trong `Pipes.is_goal()` hiện có:

```python
if total_ends // 2 != len(self.grid) - 1:
    return False
```

Điều kiện này nên được thay bằng:

```python
if total_ends != 2 * (len(self.grid) - 1):
    return False
```

Lý do là phép chia nguyên có thể bỏ sót trường hợp tổng đầu nối lẻ.

Ngoài ra, nếu hàm Goal được gọi trực tiếp trên một trạng thái bất kỳ, cần xác minh các đầu nối không vượt biên, khớp nhau và toàn mạng liên thông.

`verify_pipes()` của TV5 đã kiểm tra những điều kiện đó.

Phần sửa solver thuộc trách nhiệm TV2. Các kết quả Pipes 4×4 hiện tại đã vượt qua bước xác thực độc lập.

## 6. Công cụ benchmark của TV5

`benchmark.py` có các chức năng:

- Đọc file input JSON.
- Chọn puzzle và thuật toán tương ứng.
- Chạy thuật toán theo giới hạn.
- Đo execution time.
- Đo peak memory bằng `tracemalloc`.
- Đo expanded nodes.
- Xác thực lời giải.
- Ghi nhận lỗi.
- Xuất CSV và metadata.

Các file kết quả:

- `benchmark_raw.csv`
- `benchmark_summary.csv`
- `integration_issues.csv`
- `metadata.json`

Thời gian và bộ nhớ được đo qua hai lượt chạy riêng. Bộ nhớ được báo cáo là mức cấp phát Python theo `tracemalloc`, không phải RSS.

## 7. Đánh giá Giai đoạn 2

Các công việc đã hoàn thành:

- Kiểm tra dữ liệu JSON.
- Xây dựng verifier.
- Viết unit test.
- Kiểm thử thuật toán trên input đại diện.
- Phát hiện và ghi nhận lỗi Pipes.
- Kiểm tra lại sau khi TV2 sửa.
- Hoàn thiện công cụ benchmark.
- Chuẩn bị dữ liệu cho Giai đoạn 3.

Hạn chế:

- Chưa thể khẳng định solver đúng với mọi input và mọi seed.
- Pipes hiện chỉ có một input.
- Cần đánh giá benchmark đầy đủ hơn trong Giai đoạn 3.

## 8. Công việc chuyển tiếp Giai đoạn 3

- Chạy benchmark trên toàn bộ input Kakurasu.
- Chạy Pipes với nhiều lượt và nhiều seed.
- Tổng hợp CSV.
- Tạo bảng và biểu đồ.
- Phân tích chênh lệch thời gian, bộ nhớ và số node.
- Bàn giao kết quả cho TV1 và TV4.
- Hỗ trợ đóng gói ZIP cuối.

**Kết luận:** Các thành phần tích hợp đã hoạt động trên những trường hợp được kiểm tra. TV5 đã phát hiện được lỗi Pipes của phiên bản trước và xác nhận bản sửa trên input 4×4. Phần đánh giá thực nghiệm tổng thể được tiếp tục ở Giai đoạn 3.

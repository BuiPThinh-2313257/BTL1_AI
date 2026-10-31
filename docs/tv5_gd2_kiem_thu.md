
# TV5 – Báo cáo kiểm thử tích hợp (Giai đoạn 2)

## 1. Phạm vi

- Bài toán: **Pipes** và **Kakurasu**.
- Giải thuật kiểm thử:
  - Pipes: DFS và Hill Climbing.
  - Kakurasu: DFS và A*.
- TV5 kiểm tra độc lập bằng `verify.py` và đo thử bằng `benchmark.py`.
- Không sửa thuật toán của TV1, TV2 và TV3.
- Tài liệu cập nhật theo bản source có phần sửa Pipes của TV2, ngày 31/10/2026.

## 2. Lệnh và phương pháp kiểm thử

Chạy tại thư mục gốc `BTL1_AI`:

```powershell
py verify.py

py -m unittest discover -s tests -p "test_*.py" -v

py benchmark.py --puzzle kakurasu --inputs kakurasu_4x4_easy.json --repeats 1 --max-nodes 50000 --time-limit 5 --strict --output results/tv5-gd2-kakurasu

py benchmark.py --puzzle pipes --inputs input_pipes_4x4.json --repeats 1 --max-nodes 50000 --time-limit 5 --strict --output results/tv5-gd2-pipes
```

Nếu thư mục kết quả đã tồn tại, đổi tên `--output` trước khi chạy lại.

### Phương pháp đo

- Thời gian: `core.metrics.measure()` sử dụng `time.perf_counter()`.
- Bộ nhớ: `tracemalloc` đo bộ nhớ Python được cấp phát ở một lượt chạy riêng.
- Không bật trace GUI khi benchmark.
- Chỉ công nhận giải thành công khi `status=solved` và `verified=True`.
- Các trạng thái `node_limit`, `time_limit` và `stuck` không được coi là vô nghiệm.

## 3. Kết quả kiểm thử

Kết quả trên source ngày 31/10/2026:

- 13/13 file JSON hợp lệ về cấu trúc.
- 59/59 unit test đạt sau khi bổ sung 3 bài kiểm thử hồi quy.
- Các bài toán được chạy với `max_nodes=50000` và `time_limit=5`.
- Kakurasu sử dụng `prune=basic`.
- Hill Climbing sử dụng `seed=0`.

| Input | Giải thuật | Status | Verified | Expanded nodes |
|---|---|---|---|---:|
| kakurasu_4x4_easy.json | DFS | solved | True | 483 |
| kakurasu_4x4_easy.json | A* | solved | True | 16 |
| input_pipes_4x4.json | DFS | solved | True | 16 |
| input_pipes_4x4.json | Hill Climbing | solved | True | 21 |

Bảng trên là kết quả kiểm thử tích hợp, chưa phải kết quả benchmark cuối cùng. Thời gian và bộ nhớ phải lấy từ CSV thực nghiệm trên máy được sử dụng để lập báo cáo.

## 4. Tình trạng lỗi Pipes

### Trước khi TV2 sửa

- Solver có thể trả về `solved` nhưng `verify.py` trả về `False`.
- Điều kiện Goal chưa loại trừ đúng mạng có vòng kín.
- Bộ dữ liệu Pipes cũ không phù hợp với yêu cầu mạng không chu trình.

### Sau khi TV2 sửa

- Đã cập nhật `puzzles/pipes.py`.
- Đã cập nhật `data/input_pipes_4x4.json`.
- DFS giải thành công và `verified=True`.
- Hill Climbing với seed 0 giải thành công và `verified=True`.
- Không còn tái hiện lỗi cũ trên input Pipes 4x4 đã kiểm tra.

### Lưu ý kỹ thuật còn lại

`is_goal()` hiện dùng điều kiện:

`total_ends // 2 == V - 1`

Với input có tổng đầu nối lẻ, phép chia lấy phần nguyên có thể cho kết quả đúng dù vẫn còn đầu ống thừa.

Nên thay bằng:

`total_ends == 2 * (V - 1)`

Đồng thời, khi hỗ trợ dữ liệu khác, cần kiểm tra các đầu nối khớp nhau và không hướng ra biên.

`verify_pipes()` của TV5 đã từ chối các lời giải có đầu nối không hợp lệ.

Chưa kết luận solver đúng với mọi input và mọi seed.

## 5. Công việc cần thực hiện ở Giai đoạn 3

1. Thống nhất cấu hình benchmark chính thức với TV1.
2. Chạy benchmark toàn bộ bộ dữ liệu Kakurasu.
3. Chạy benchmark các input Pipes hợp lệ.
4. Đánh giá Hill Climbing với nhiều seed khác nhau.
5. Xuất CSV thô, CSV tổng hợp và metadata.
6. Tạo bảng và biểu đồ so sánh thời gian, bộ nhớ và số node.
7. Phân biệt kết quả giải thành công với các trường hợp chạm giới hạn.
8. Bàn giao kết quả cho TV1 và TV4.

Lưu ý: `median_time_valid_s` chỉ tính lượt giải đúng, trong khi `median_peak_kb_all` tính trên mọi lượt. Không coi hai chỉ số này được tính trên cùng một tập lượt chạy.

## 6. Các file TV5 bàn giao

### Giai đoạn 1

- `verify.py`
- `tests/test_verify.py`

### Giai đoạn 2

- `benchmark.py`
- `tests/test_benchmark.py`
- `docs/tv5_gd2_kiem_thu.md`

### Kết quả thực nghiệm

Các file CSV và metadata được tạo trong `results/`.

Thư mục `results/` hiện bị `.gitignore` bỏ qua. Nếu muốn lưu kết quả chính thức lên GitHub, có thể sao chép chúng vào `docs/experiments/tv5/` sau khi thống nhất với nhóm.
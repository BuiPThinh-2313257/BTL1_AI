# TV5 - Báo cáo kiểm thử tích hợp (Giai đoạn 2)

## 1. Phạm vi
- Puzzle: Pipes và Kakurasu.
- Giải thuật: Pipes (DFS / Hill Climbing); Kakurasu (DFS / A*).
- Kiểm tra độc lập bằng `verify.py`; không can thiệp code solver TV1/TV2/TV3.

## 2. Phương pháp
- Kiểm tra dữ liệu: `py verify.py`.
- Unit test: `py -m unittest discover -s tests -p "test_*.py" -v`.
- Benchmark thử: `py benchmark.py --puzzle kakurasu --inputs kakurasu_4x4_easy.json --repeats 2 --output results/tv5-smoke-01`.
- Thời gian: `core.metrics.measure()` dùng `perf_counter()`.
- Bộ nhớ: `tracemalloc` peak trong lần chạy riêng, đơn vị KiB; không phải RSS.
- Tính đúng: chỉ `status=solved` VÀ `verified=True` mới là lời giải hợp lệ.

## 3. Kết quả kiểm tra (điền sau khi chạy trên máy của bạn)
| Input | Thuật toán | Status | Verified | Nodes | Ghi chú |
|---|---|---|---|---:|---|
| kakurasu_4x4_easy.json | DFS | ... | ... | ... | ... |
| kakurasu_4x4_easy.json | A* | ... | ... | ... | ... |
| input_pipes_4x4.json | DFS | ... | ... | ... | ... |
| input_pipes_4x4.json | Hill Climbing | ... | ... | ... | ... |

## 4. Lỗi cần phối hợp
- **PIPES-01 (chờ TV2):** `puzzles/pipes.py` hiện kiểm tra liên thông nhưng chưa chặn chu trình ở `is_goal()`; `local_cost()` cũng có thể kết thúc với state có vòng kín. `verify.py` từ chối lời giải đó. Mô hình/input cần kiểm tra lại theo luật puzzle mà nhóm chốt.
- Sau khi TV2 sửa, chạy lại Pipes; thay trạng thái trong bảng bằng dữ liệu thực tế.

## 5. Giới hạn và ghi chú
- `node_limit` / `time_limit` / `stuck` không đồng nghĩa vô nghiệm.
- Không dùng kết quả `verified=False` để tuyên bố solver giải được.
- Giai đoạn 2 chỉ là kiểm thử và benchmark thử. Cần chốt cấu hình với TV1 trước đo chính thức Giai đoạn 3.
- Lần chạy đo bộ nhớ là lần riêng; `benchmark.py` xác thực lời giải của lần đo thời gian. Seed cố định cho Hill Climbing để tái lập.

## 6. Bàn giao
- `benchmark.py`; `tests/test_benchmark_tv5.py`; tài liệu này.
- Kết quả CSV thử nghiệm ở `results/` (thường bị `.gitignore` bỏ qua). Khi cần đưa lên GitHub, thống nhất nơi lưu với nhóm.

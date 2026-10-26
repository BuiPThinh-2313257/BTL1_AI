# BTL1 – Nhập môn Trí tuệ nhân tạo: Pipes & Kakurasu

Giải 2 bài logic puzzle (Pipes, Kakurasu) bằng 1 giải thuật tìm kiếm mù và 1 giải thuật heuristic, có demo trực quan step-by-step và bảng đo thời gian/bộ nhớ.

## Cấu trúc

| Thư mục | Nội dung |
|---|---|
| `core/` | khung chung: `Problem`, các giải thuật (`search.py`), ghi trace cho GUI (`trace.py`), đo lường (`metrics.py`). Hướng dẫn: `core/README.md` |
| `puzzles/` | các bài toán. `examples.py` là bài mẫu (8-puzzle, N-queens) để thử giải thuật |
| `tests/` | unit test |
| `traces/` | file trace JSON mẫu cho GUI |
| `docs/` | giải thích chi tiết từng file trong `core/` |

## Chạy test

```
python -m unittest discover tests
```

Yêu cầu: Python 3.8+, không cần thư viện ngoài.

## Phần TV3 - Kakurasu

- Mô hình, luật, heuristic và API: [giải thích Kakurasu](docs/giai_thich_kakurasu.md).
- Phần báo cáo và phân tích từng input: [báo cáo TV3](docs/bao_cao_tv3_kakurasu.md).
- Số liệu thô và cấu hình: [thực nghiệm 24/10/2026](docs/experiments/tv3-2026-10-24/).
- Chạy lại (thư mục kết quả phải chưa tồn tại):

```sh
python -B tools/tv3_kakurasu_experiment.py --output results/tv3-new --repeats 3 --max-nodes 50000 --time-limit 5 --memory-time-limit 30
```

Công cụ này chỉ tạo số liệu cho phần Kakurasu của TV3. Benchmark tổng hợp hai bài,
biểu đồ chung và ZIP nộp bài là phần bàn giao cho TV5. Không cần thư viện ngoài.

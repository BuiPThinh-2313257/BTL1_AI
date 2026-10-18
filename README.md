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

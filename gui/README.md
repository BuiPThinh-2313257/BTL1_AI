# TV4 – Giai đoạn 1: GUI xem trace

Ứng dụng đọc **trace JSON thật đã có**, không chạy solver và không cần package ngoài thư viện chuẩn Python.

## Khởi động (Windows / VS Code)

1. Mở **thư mục gốc** `BTL1_AI-main` trong VS Code (thư mục chứa `core/`, `puzzles/`, `traces/`).
2. Trong VS Code chọn **Terminal > New Terminal**.
3. Chạy:

   ```powershell
   python gui/viewer.py
   ```

   Nếu Windows dùng Python Launcher, có thể thay bằng `py gui/viewer.py`.

4. Chọn `Pipes` hoặc `Kakurasu` và chọn đúng thuật toán có sẵn:
   - Pipes: **DFS** / **Hill Climbing**
   - Kakurasu: **DFS** / **A\***
5. Sử dụng các nút **Phát / Tạm dừng / Trước / Sau / Về đầu** và thanh tua.
6. Chuyển giữa **QUÁ TRÌNH TÌM KIẾM** (có sự kiện expand/move/goal) và **ĐƯỜNG ĐI LỜI GIẢI** (chỉ các trạng thái của lời giải).
7. Có thể dùng **MỞ TRACE JSON** để chọn một file khác cùng chuẩn.

## Có thể chạy file JSON cụ thể

```powershell
python gui/viewer.py traces/example_kakurasu_4x4_astar.json
```

## Lưu ý

- Chỉ hỗ trợ ma trận 4×4 và trace JSON `version: 1` ở Giai đoạn 1.
- Màu sáng ở viền ô chỉ vị trí **thay đổi so với frame trước**, không phải thông báo lỗi.
- Số liệu **thời gian / node** hiển thị là kết quả lưu trong `result`, không phải đo tại GUI. Trace hiện tại **không có dữ liệu bộ nhớ**, vì vậy giao diện hiển thị `Không có dữ liệu`, không tự suy đoán.
- Đối với Pipes/DFS, các ô `null` là **chưa được gán** theo thuật toán, không nhất thiết tương ứng với bảng trò chơi lúc bắt đầu.
- Giai đoạn 2 sẽ ghép việc chạy solver thật, nếu nhóm thống nhất API; giai đoạn 1 chỉ phát lại trace sẵn có.

## Tệp mới do TV4 tạo

- `gui/__init__.py`
- `gui/viewer.py`
- `gui/README.md`

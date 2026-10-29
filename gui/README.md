# TV4 – Giai đoạn 2: giao diện chạy solver thật

**Mục tiêu:** Từ cùng giao diện Tkinter của GĐ1, chọn input 4×4 và thuật toán,
chạy trực tiếp solver TV1 + mô hình Pipes (TV2) / Kakurasu (TV3), nhận trace
JSON mới rồi phát lại từng bước. **Không sửa** `core/`, `puzzles/`, `data/`.

## 1. Khởi động Windows + VS Code

Mở **thư mục gốc** repository (cùng cấp với `core/`, `puzzles/`, `gui/`).

```powershell
conda activate btl1-gui
python gui/viewer.py
```

Nếu Python cài mặc định có Tkinter, không nhất thiết phải dùng Conda. Để kiểm
tra môi trường: `python -m tkinter`.

## 2. Các nút trong giao diện

1. **BÀI TOÁN:** Pipes 4×4 hoặc Kakurasu 4×4.
2. **GIẢI THUẬT:** Pipes `DFS` / `Hill Climbing`; Kakurasu `DFS` / `A*`.
3. **INPUT 4×4 → CHỌN INPUT:** chọn một file JSON đầu vào khác; để mặc định
   sẽ dùng `data/input_pipes_4x4.json` hoặc `data/kakurasu_4x4_easy.json`.
   Các input Kakurasu 4×4 hard cũng dùng được. Không hỗ trợ bảng kích thước khác.
4. **▶ CHẠY SOLVER:** chạy thật trong tiến trình con, không làm treo GUI.
   Khi hoàn tất, giao diện sẽ đọc trace mới và phát lại bằng nút **PHÁT / TẠM DỪNG**,
   **TRƯỚC / SAU**, **VỀ ĐẦU** hoặc thanh kéo. Một lần bấm **CHẠY SOLVER**
   là **chạy lại thuật toán**; bấm **PHÁT** chỉ **phát lại dữ liệu đã ghi**.
5. **QUÁ TRÌNH TÌM KIẾM / ĐƯỜNG ĐI LỜI GIẢI:** xem hai loại chuỗi trạng thái.
6. **LƯU TRACE:** chọn nơi ghi JSON; có thể chia sẻ lại với nhóm hoặc nạp lại
   bằng **MỞ TRACE JSON**. Tính năng mở trace mẫu GĐ1 vẫn giữ nguyên.

## 3. Cấu hình mặc định dùng để demo

| Bài | Thuật toán | Input | Tham số |
|---|---|---|---|
| Pipes | DFS | `data/input_pipes_4x4.json` | 50.000 node / 5 giây |
| Pipes | Hill Climbing | như trên | seed 0, 50.000 node / 5 giây |
| Kakurasu | DFS | `data/kakurasu_4x4_easy.json` | prune=`basic`, 50.000 node / 5 giây |
| Kakurasu | A* | như trên | prune=`basic`, 50.000 node / 5 giây |

Mặc định `prune=basic` để nhất quán với **trace mẫu TV3**. Khi chạy trực tiếp,
Kakurasu DFS trên `4x4_easy` tạo 483 node mở rộng / 485 sự kiện. Kết quả thời gian
sẽ thay đổi theo máy. Hill Climbing đặt seed=0 để tái lập; **trace HC có thể khác
trace mẫu nhóm tạo với seed khác**.

## 4. Đo số liệu – đừng nhầm với benchmark TV5

- **Node, độ dài, trạng thái** lấy từ `SearchResult` của solver.
- **Thời gian thuật toán** đọc từ `SearchResult.elapsed` của lần chạy **có ghi trace**.
- **Bộ nhớ** là `tracemalloc` peak KB/KiB của **một lần chạy thứ hai không ghi
  trace**, dùng `core.metrics.measure()`. Giao diện sẽ hiển thị KB khi đo được.
- Vì số đo thời gian bật trace, và bộ nhớ là một lần đo riêng, **không sử dụng
  số liệu GUI làm bảng benchmark chính thức**; nhiệm vụ so sánh và bảng CSV
  theo quy trình chung của TV5.
- Trace mẫu GĐ1 không có `peak_kb`, nên hiện "Không có dữ liệu"; GUI không tự
  đoán bộ nhớ của những lần chạy trước.

Khi giải không tìm được nghiệm, vượt giới hạn, hoặc trace bị cắt do quá nhiều
frame, giao diện thể hiện trạng thái đó; không được hiểu `node_limit/time_limit`
là `solved`.

## 5. Chạy solver từ Terminal (không cần mở GUI)

```powershell
python -m gui.live_runner --puzzle pipes --algorithm dfs --input data/input_pipes_4x4.json --output traces/my_pipes_dfs.json --memory
python -m gui.live_runner --puzzle pipes --algorithm hill_climbing --input data/input_pipes_4x4.json --output traces/my_pipes_hc.json --seed 0 --memory
python -m gui.live_runner --puzzle kakurasu --algorithm dfs --input data/kakurasu_4x4_easy.json --output traces/my_kakurasu_dfs.json --prune basic --memory
python -m gui.live_runner --puzzle kakurasu --algorithm astar --input data/kakurasu_4x4_easy.json --output traces/my_kakurasu_astar.json --prune basic --memory
```

Các lệnh chỉ chạy khi người dùng gọi; **không tự ghi trace vào repository**
khi bấm nút trong GUI. Với UI, trace tạm được xóa sau khi tải vào bộ nhớ;
ấn **LƯU TRACE** nếu muốn giữ lại.

## 6. Kiểm thử

```powershell
python -m unittest discover tests
```

Bộ kiểm thử GĐ2 kiểm tra đủ 4 tổ hợp bài/thuật toán, trạng thái goal thực sự
đúng luật, các cấu trúc JSON, đo bộ nhớ, subprocess và xử lý input sai kích thước.

## 7. File của TV4

- `gui/viewer.py` – giao diện GĐ1 được nâng cấp thêm nút chọn input/chạy/lưu.
- `gui/live_runner.py` – adapter duy nhất để gọi solver trong core + mô hình puzzles.
- `gui/README.md` – hướng dẫn người chạy, nhập input và kiểm thử.
- `tests/test_gui_live.py` – kiểm thử tích hợp GĐ2.

`gui/__init__.py` và `tests/test_gui.py` từ GĐ1 **được giữ nguyên**.

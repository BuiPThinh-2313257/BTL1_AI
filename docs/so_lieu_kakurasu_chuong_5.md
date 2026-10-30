# Số liệu thực nghiệm Kakurasu cho chương 5

Bộ số liệu ngày 24/10/2026 dùng để ghép vào chương thực nghiệm chung với Pipes.
Phần luật chơi, mô hình và thuật toán nằm trong [báo cáo Kakurasu](bao_cao_tv3_kakurasu.md).

## 1. Cách đo

- Tập đo cố định: 12 JSON từ 4x4 đến 9x9, mỗi kích thước hai nhãn easy/hard, có source
  và puzzle_id trong file. Đây là tập nhỏ có sẵn, không phải mẫu ngẫu nhiên đại diện.
- Thiết kế 12 input x 3 thuật toán (DFS, BFS, A*) x 2 mức cắt tỉa = 72 cấu hình.
- Mỗi cấu hình chạy 3 lần đo giờ không bật trace/tracemalloc; báo trung vị và min-max.
  Chạy thêm một lần riêng bật tracemalloc đo peak cấp phát Python, đơn vị KiB=1024 byte.
  Tổng 288 lượt; không có warm-up riêng, chạy tuần tự theo thứ tự cố định.
- Mỗi lượt tạo mô hình mới: thời gian và peak đều gồm đọc JSON, tạo mô hình/tính bảng và
  tìm kiếm; không gồm import thư viện, kiểm tra lời giải hay ghi CSV. Thời gian của lượt
  tracemalloc không dùng để so tốc độ.
- Giới hạn chung 50.000 node mở rộng/lượt. Hàng rào thời gian: 5 giây cho lượt đo giờ,
  30 giây cho lượt đo bộ nhớ. Solver kiểm tra thời gian mỗi 256 node nên không phải
  timeout cứng. Lượt bộ nhớ được đối chiếu trạng thái, số node, frontier, cost và lời giải
  với lượt đo giờ trước khi ghép hai số liệu.
- `node_limit` nghĩa là chưa giải được trong ngân sách; không có nghĩa vô nghiệm và thời
  gian dừng đó không phải thời gian giải. Peak ở lượt bị giới hạn là peak đến lúc dừng.
- Peak Python không phải RSS hay toàn bộ RAM của tiến trình. Không bật đo bộ nhớ khi đo
  giờ; không coi một lượt peak là ước lượng phương sai bộ nhớ. Ba lượt giờ chỉ cho mô tả
  độ dao động cục bộ, không đủ để khẳng định ý nghĩa thống kê.
- Giữ nguyên mức cắt tỉa để so thuật toán; giữ nguyên thuật toán để so cắt tỉa. Việc so
  DFS basic với A* full sẽ trộn hai tác động. Mọi thuật toán cùng chịu chi phí tính bảng.

Máy đo: Intel Core i7-13650HX, 14 lõi/20 luồng; RAM vật lý 16.873.545.728 byte
(khoảng 15,71 GiB). Hệ điều hành `Windows-11-10.0.26200-SP0`; Python `3.12.14 (main, Aug 25 2026, 14:01:42) [MSC v.1944 64 bit (AMD64)]`.
Thời điểm đo: 24/10/2026 12:02:14 đến 12:04:08, UTC+7.
Không cố định CPU affinity hay kiểm soát tải nền. Các con số là kết quả trên máy này.

Mã nền Git: `3de2bfddc74ac2479143a468b5d380cb38c52b41` trên nhánh `tv3-kakurasu`, cộng các thay đổi TV3
chưa commit tại lúc đo. SHA256 từng file thực sự dùng, hash 12 input, câu lệnh, môi trường
và trạng thái working tree nằm trong [metadata](experiments/tv3-2026-10-24/metadata.json).
Không gán kết quả mới cho riêng commit nền. Dữ liệu thô ở
[raw.csv](experiments/tv3-2026-10-24/raw.csv), tổng hợp ở
[summary.csv](experiments/tv3-2026-10-24/summary.csv).

Chạy lại từ thư mục gốc repo (thư mục kết quả phải chưa tồn tại):

```sh
python -B tools/tv3_kakurasu_experiment.py --output results/tv3-new --repeats 3 --max-nodes 50000 --time-limit 5 --memory-time-limit 30
python -B -m unittest discover -s tests -v
```

Chương trình không dùng thư viện ngoài. Số node tái lập theo thuật toán/thứ tự successor;
thời gian và peak có thể thay đổi theo phiên bản Python, môi trường và tải máy.

## 2. Kết quả

Cả 72 cấu hình có ba lượt đo giờ trùng trạng thái và thống kê tìm kiếm; lượt đo bộ nhớ
cũng trùng đường tìm kiếm. Có 55/72 cấu hình giải được (220/288 lượt), 17/72 cấu hình
đạt giới hạn node; không lượt nào dừng vì giới hạn thời gian. Mọi lời giải trả về đều
qua kiểm tra đúng kích thước, ô nguyên 0/1, tổng hàng/cột, chi phí và số hành động.

| Mức cắt tỉa | DFS giải được | BFS giải được | A* giải được |
|---|---:|---:|---:|
| basic | 4/12 | 3/12 | 12/12 |
| full | 12/12 | 12/12 | 12/12 |

### 2.1. Số node mở rộng theo input

`L` = dừng ở giới hạn 50.000 node. Dấu L là quan sát bị giới hạn, không phải số node
cần để giải. Các bộ đếm dùng nguyên định nghĩa của core: DFS/A* không tính node đích
vào nodes_expanded, BFS kiểm tra đích khi sinh node con. Trace có thể có sự kiện expand
cho đích nhưng bộ đếm không tăng; không đồng nhất số sự kiện trace với số node mở rộng.

| Input | DFS basic | BFS basic | A* basic | DFS full | BFS full | A* full |
|---|---:|---:|---:|---:|---:|---:|
| 4x4_easy | 483 | 638 | 16 | 16 | 16 | 16 |
| 4x4_hard | 243 | 796 | 16 | 16 | 16 | 16 |
| 5x5_easy | L | L | 25 | 25 | 25 | 25 |
| 5x5_hard | 37182 | L | 36 | 25 | 36 | 36 |
| 6x6_easy | 276 | 5679 | 37 | 36 | 37 | 37 |
| 6x6_hard | L | L | 91 | 43 | 125 | 91 |
| 7x7_easy | L | L | 64 | 50 | 64 | 64 |
| 7x7_hard | L | L | 88 | 49 | 91 | 88 |
| 8x8_easy | L | L | 221 | 199 | 243 | 221 |
| 8x8_hard | L | L | 1305 | 1120 | 2127 | 1305 |
| 9x9_easy | L | L | 1082 | 480 | 1327 | 1082 |
| 9x9_hard | L | L | 368 | 308 | 487 | 368 |

### 2.2. Thời gian và bộ nhớ từng cấu hình

Trung vị và min-max tính trên ba lượt giờ, đơn vị ms, làm tròn 3 chữ số thập phân chỉ
để trình bày. File CSV giữ số chưa làm tròn. Peak Python tính KiB từ lượt riêng.
`max_frontier` là bộ đếm do core trả về, không phải toàn bộ cấu trúc lưu trữ: DFS cũng
lưu parent của node đã thăm; BFS/A* còn có các bảng phụ nên frontier nhỏ không chứng minh
bộ nhớ toàn chương trình nhỏ. Hàng `node_limit` chỉ mô tả tài nguyên dùng tới lúc dừng.

#### DFS / basic

| Input | Trạng thái | Trung vị ms | Min-max ms | Peak Python KiB | max_frontier |
|---|---|---:|---:|---:|---:|
| 4x4_easy | solved | 1.628 | 1.592-1.761 | 173.1 | 7 |
| 4x4_hard | solved | 0.914 | 0.907-0.952 | 93.6 | 8 |
| 5x5_easy | node_limit | 255.796 | 253.317-268.073 | 21000.3 | 17 |
| 5x5_hard | solved | 502.082 | 479.962-503.106 | 14908.5 | 16 |
| 6x6_easy | solved | 4.321 | 3.301-4.451 | 149.2 | 9 |
| 6x6_hard | node_limit | 797.948 | 788.421-807.967 | 25007.7 | 25 |
| 7x7_easy | node_limit | 1074.488 | 1044.061-1106.083 | 30085.8 | 35 |
| 7x7_hard | node_limit | 927.669 | 912.836-933.974 | 30051.5 | 28 |
| 8x8_easy | node_limit | 1371.745 | 1334.968-1397.139 | 35928.7 | 47 |
| 8x8_hard | node_limit | 1289.482 | 1265.152-1363.879 | 35856.4 | 41 |
| 9x9_easy | node_limit | 1706.012 | 1698.663-1830.544 | 42509.1 | 60 |
| 9x9_hard | node_limit | 1545.949 | 1470.393-1717.517 | 42652.5 | 42 |

#### BFS / basic

| Input | Trạng thái | Trung vị ms | Min-max ms | Peak Python KiB | max_frontier |
|---|---|---:|---:|---:|---:|
| 4x4_easy | solved | 2.429 | 2.404-2.448 | 378.5 | 236 |
| 4x4_hard | solved | 2.955 | 2.939-3.064 | 454.1 | 323 |
| 5x5_easy | node_limit | 336.292 | 295.310-669.772 | 44218.8 | 48169 |
| 5x5_hard | node_limit | 725.289 | 723.107-731.802 | 33941.0 | 30351 |
| 6x6_easy | solved | 67.664 | 67.651-71.422 | 3680.3 | 917 |
| 6x6_hard | node_limit | 742.923 | 719.695-745.217 | 43408.8 | 43222 |
| 7x7_easy | node_limit | 766.443 | 736.750-913.509 | 43738.4 | 45769 |
| 7x7_hard | node_limit | 726.312 | 716.623-777.829 | 34192.5 | 29767 |
| 8x8_easy | node_limit | 777.612 | 763.047-778.212 | 44458.9 | 49243 |
| 8x8_hard | node_limit | 767.283 | 745.064-785.157 | 44687.5 | 40687 |
| 9x9_easy | node_limit | 839.235 | 816.485-848.452 | 45360.1 | 49825 |
| 9x9_hard | node_limit | 799.548 | 779.517-808.592 | 38728.9 | 34308 |

#### A* / basic

| Input | Trạng thái | Trung vị ms | Min-max ms | Peak Python KiB | max_frontier |
|---|---|---:|---:|---:|---:|
| 4x4_easy | solved | 0.233 | 0.226-0.278 | 23.7 | 12 |
| 4x4_hard | solved | 0.237 | 0.235-0.266 | 23.2 | 11 |
| 5x5_easy | solved | 0.744 | 0.742-1.310 | 39.0 | 22 |
| 5x5_hard | solved | 1.479 | 1.296-1.487 | 45.3 | 33 |
| 6x6_easy | solved | 1.424 | 1.200-1.725 | 47.7 | 13 |
| 6x6_hard | solved | 4.887 | 4.887-5.261 | 117.2 | 86 |
| 7x7_easy | solved | 4.008 | 3.288-4.281 | 92.9 | 62 |
| 7x7_hard | solved | 3.508 | 1.967-4.197 | 108.9 | 68 |
| 8x8_easy | solved | 11.735 | 8.364-11.925 | 284.2 | 211 |
| 8x8_hard | solved | 50.640 | 50.133-57.316 | 1473.7 | 1231 |
| 9x9_easy | solved | 55.808 | 43.726-59.474 | 1265.7 | 1064 |
| 9x9_hard | solved | 18.900 | 17.999-19.842 | 563.5 | 320 |

#### DFS / full

| Input | Trạng thái | Trung vị ms | Min-max ms | Peak Python KiB | max_frontier |
|---|---|---:|---:|---:|---:|
| 4x4_easy | solved | 0.170 | 0.167-0.206 | 17.0 | 1 |
| 4x4_hard | solved | 0.179 | 0.172-0.221 | 16.9 | 1 |
| 5x5_easy | solved | 0.704 | 0.697-0.863 | 25.3 | 1 |
| 5x5_hard | solved | 0.800 | 0.735-1.130 | 25.8 | 3 |
| 6x6_easy | solved | 0.783 | 0.780-0.820 | 35.2 | 2 |
| 6x6_hard | solved | 1.544 | 1.473-1.918 | 38.9 | 5 |
| 7x7_easy | solved | 1.535 | 1.384-2.260 | 50.3 | 6 |
| 7x7_hard | solved | 0.767 | 0.728-1.631 | 49.7 | 3 |
| 8x8_easy | solved | 5.788 | 5.309-5.890 | 122.7 | 8 |
| 8x8_hard | solved | 20.084 | 18.640-20.728 | 498.1 | 11 |
| 9x9_easy | solved | 11.143 | 8.699-12.406 | 262.6 | 7 |
| 9x9_hard | solved | 6.319 | 6.078-6.706 | 200.8 | 7 |

#### BFS / full

| Input | Trạng thái | Trung vị ms | Min-max ms | Peak Python KiB | max_frontier |
|---|---|---:|---:|---:|---:|
| 4x4_easy | solved | 0.170 | 0.169-0.190 | 19.8 | 1 |
| 4x4_hard | solved | 0.186 | 0.177-0.331 | 19.7 | 1 |
| 5x5_easy | solved | 0.467 | 0.405-0.810 | 28.9 | 1 |
| 5x5_hard | solved | 0.783 | 0.762-0.810 | 31.8 | 3 |
| 6x6_easy | solved | 0.813 | 0.599-0.990 | 39.1 | 2 |
| 6x6_hard | solved | 2.151 | 2.067-2.277 | 72.9 | 10 |
| 7x7_easy | solved | 2.104 | 1.952-2.503 | 58.3 | 4 |
| 7x7_hard | solved | 2.436 | 2.157-2.796 | 72.9 | 4 |
| 8x8_easy | solved | 5.325 | 5.108-6.231 | 154.8 | 18 |
| 8x8_hard | solved | 35.169 | 33.355-47.849 | 1033.7 | 201 |
| 9x9_easy | solved | 15.914 | 14.891-16.387 | 676.2 | 99 |
| 9x9_hard | solved | 9.986 | 9.854-11.971 | 322.3 | 40 |

#### A* / full

| Input | Trạng thái | Trung vị ms | Min-max ms | Peak Python KiB | max_frontier |
|---|---|---:|---:|---:|---:|
| 4x4_easy | solved | 0.209 | 0.203-0.237 | 19.1 | 1 |
| 4x4_hard | solved | 0.223 | 0.217-0.247 | 19.1 | 1 |
| 5x5_easy | solved | 0.943 | 0.931-1.038 | 30.2 | 1 |
| 5x5_hard | solved | 1.121 | 1.107-1.315 | 32.9 | 3 |
| 6x6_easy | solved | 1.091 | 0.709-1.097 | 40.4 | 2 |
| 6x6_hard | solved | 2.797 | 1.505-2.898 | 74.7 | 8 |
| 7x7_easy | solved | 3.463 | 2.766-3.685 | 60.7 | 3 |
| 7x7_hard | solved | 3.063 | 2.813-3.109 | 82.9 | 4 |
| 8x8_easy | solved | 8.150 | 7.381-9.349 | 162.2 | 9 |
| 8x8_hard | solved | 43.728 | 36.854-49.040 | 803.1 | 92 |
| 9x9_easy | solved | 40.069 | 36.792-40.429 | 651.8 | 62 |
| 9x9_hard | solved | 12.439 | 12.212-13.166 | 322.0 | 21 |

## 3. Phân tích kết quả

| Input | Nhận xét dựa trên số node, dưới cùng ngân sách |
|---|---|
| 4x4 easy | basic: A* 16 node so với DFS 483 và BFS 638. full: cả ba còn 16; ưu thế số node của A* biến mất khi ràng buộc đã ép đường đi. |
| 4x4 hard | basic: DFS 243, BFS 796, A* 16. DFS duyệt ít hơn trên đề easy dù tên là hard; nhãn trang nguồn không đo trực tiếp độ khó của thuật toán này. |
| 5x5 easy | DFS/BFS basic cùng dừng ở 50.000 node; A* basic 25. full đưa cả ba về 25, cho thấy kiểm tra phần thiếu khả đạt loại được nhiều nhánh hơn kiểm tra vượt tổng. |
| 5x5 hard | DFS basic giải ở 37.182 node, BFS basic bị giới hạn, A* basic 36. full: DFS 25, BFS/A* 36. Không thể khẳng định A* luôn mở ít node nhất. |
| 6x6 easy | basic: DFS 276, BFS 5.679, A* 37; full: 36/37/37. Thứ tự duyệt DFS có lợi trên input này; full khiến phần lớn chi phí node không còn khác biệt. |
| 6x6 hard | DFS/BFS basic bị giới hạn, A* 91. full: DFS 43, BFS 125, A* 91. Cắt tỉa giúp các thuật toán mù giải trong ngân sách. |
| 7x7 easy | DFS/BFS basic bị giới hạn, A* 64. full: 50/64/64, DFS đi ít nhánh sai hơn trong lần tìm lời giải đầu tiên này. |
| 7x7 hard | DFS/BFS basic bị giới hạn, A* 88. full: 49/91/88; A* giảm một phần node so BFS nhưng không so DFS. |
| 8x8 easy | DFS/BFS basic bị giới hạn, A* 221. full: 199/243/221; khác biệt nhỏ hơn nhiều so basic, cần xem chi phí xử lý mỗi node trong bảng thời gian. |
| 8x8 hard | DFS/BFS basic bị giới hạn, A* 1.305. full: 1.120/2.127/1.305. Đây là input mở nhiều node nhất trong các lượt full của từng thuật toán ở bộ đo này. |
| 9x9 easy | DFS/BFS basic bị giới hạn, A* 1.082. full: 480/1.327/1.082. Dù nhiều ô hơn 8x8 hard, cả ba full đều mở ít node hơn: kích thước không đủ để dự báo độ khó. |
| 9x9 hard | DFS/BFS basic bị giới hạn, A* 368. full: 308/487/368, đều ít hơn 9x9 easy; một đề mỗi nhãn/kích thước không đủ phân tích tác động độc lập của nhãn độ khó. |

Trong tập đo này, A* basic tìm được lời giải trong ngân sách node ở cả 12 đề, trong khi DFS/BFS basic
chỉ đạt 4 và 3 đề. Cơ chế phù hợp với kết quả là ưu tiên đường có cận tổng chi phí thấp;
đây không phải bằng chứng rằng mọi Kakurasu lớn đều giải nhanh. Ngân sách node chỉ cho
cận dưới về công việc còn thiếu của các lượt bị giới hạn, không cho tỷ lệ tăng tốc chính
xác trên các lượt đó.

Khi chuyển basic sang full, DFS giảm mạnh số node trên nhiều input và giải được toàn bộ
12 đề. A* mở cùng số node giữa hai mức trên bộ dữ liệu này, nhưng full có thể loại bớt
nhánh h=inf trước khi đưa vào heap, ảnh hưởng số node sinh/frontier/peak. Không được suy
ra cắt tỉa vô ích đối với A* chỉ từ nodes_expanded bằng nhau. Thời gian còn phụ thuộc chi
phí kiểm tra, tính heuristic, thao tác heap và cấu trúc lưu trữ; ít node hơn không đồng
nghĩa nhanh hơn theo đúng cùng một tỷ lệ.

DFS giữ frontier theo chiều sâu nhưng hiện thực còn lưu parent của mọi trạng thái đã
thăm; do đó không áp dụng máy móc cận bộ nhớ O(depth) của DFS dạng đệ quy chỉ lưu đường.
BFS giữ nhiều trạng thái cùng lớp; A* giữ heap và các bảng g/depth/parent/closed. Peak
tracemalloc ở bảng là số đo cho hiện thực này, không chỉ là phân tích độ phức tạp lý thuyết.

Các kết quả basic/full dùng cùng input và cấu hình để so cơ chế cụ thể. Chưa có thử nghiệm
đối chứng thứ tự successor hay heuristic bằng 0; không tách hoàn toàn hiệu quả của cận
heuristic khỏi quy tắc phá hòa của A* (`f`, rồi `h`, rồi thứ tự sinh). Không suy diễn nhân
quả riêng cho một thành phần chưa được tách thử nghiệm.

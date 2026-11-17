# Bài tập về nhà 2 — Load test endpoint chính và đề xuất SLO

Theo trang 35, Buổi 8: load test một endpoint chính bằng Locust và viết một
trang phân tích giải thích SLO đề xuất.

Bài này dùng service có sẵn ở `week7`, endpoint
`GET /api/v1/products?page=<1..50>&size=20`. Đây là endpoint duyệt danh mục
sản phẩm, có truy vấn lấy dữ liệu, đếm tổng số và serialize JSON.

## Cài đặt và chạy từ thư mục gốc project

Yêu cầu Python 3.12 trở lên, macOS hoặc Linux (runner dùng Gunicorn).

```sh
python3 -m venv week8/.venv
week8/.venv/bin/python -m pip install -r week8/requirements-lock.txt
week8/.venv/bin/python week8/bai_tap_ve_nha_2/run_load_test.py
```

Runner tự chạy migration của tuần 7, tạo 1.000 sản phẩm giả trong một database
SQLite mới, khởi động Gunicorn 2 sync worker trên cổng loopback còn trống,
warmup 10 giây, chạy A/B/C rồi dừng server. Mỗi lần chạy tạo một thư mục kết
quả mới và giữ nguyên dữ liệu của những lần trước. Thời gian toàn bộ khoảng
2–3 phút sau khi cài dependency.

`requirements-lock.txt` ghi đầy đủ các phiên bản đã chạy kiểm chứng;
`requirements.txt` ghi dependency trực tiếp và dùng lại dependency tuần 7.

| Kịch bản | User tối đa | Thêm user/giây | Thời gian |
| --- | ---: | ---: | ---: |
| A — baseline | 10 | 2 | 30 giây |
| B — tải dự kiến | 50 | 5 | 60 giây |
| C — tăng tải nhanh | 200 | 50 | 30 giây |

User nghỉ ngẫu nhiên 1–3 giây sau mỗi lần đọc; timeout HTTP 5 giây. Locust
kiểm tra HTTP 200, JSON, phân trang, 20 sản phẩm mỗi trang và kiểu dữ liệu
cơ bản. Request HTTP 200 nhưng sai dữ liệu cũng được ghi là lỗi. Các trang
được gộp chung một tên trong thống kê. Bài này đo hành vi đọc hợp lệ.

Chỉ chạy baseline để dùng trong CI:

```sh
week8/.venv/bin/python week8/bai_tap_ve_nha_2/run_load_test.py --scenario A
```

Runner trả exit code 0 khi mọi kịch bản được chọn đều có ít nhất 100 request,
**p95 < 300 ms** và **tỉ lệ request lỗi < 1%**. Không có request, thiếu dữ liệu,
lỗi khởi động và lỗi chạy Locust đều làm lệnh thất bại.

## Bài nộp

- `locustfile.py`: kịch bản Locust.
- `run_load_test.py`: tự chuẩn bị API và chạy phép đo.
- [analysis.md](analysis.md): báo cáo phân tích SLO dựa trên số đo thực tế.
- `reports/<thời điểm>/A.html`, `B.html`, `C.html`: báo cáo HTML.
- `reports/<thời điểm>/*_stats.csv`, `*_stats_history.csv`, `*_failures.csv`,
  `*_exceptions.csv`: số liệu gốc.
- `summary.csv`, `summary.json`: kết quả và quyết định SLO từng kịch bản.
- `*_final.json`, `*_final_stats.csv`: số liệu cuối phiên trích từ HTML bằng
  `../locust_report.py`. Bảng phân tích dùng số liệu này; CSV mặc định của
  Locust là snapshot định kỳ, có thể chưa chứa các request ở giây cuối.
- `environment.json`, `*_command.json`, `*.log`: cấu hình, lệnh, thời gian và log.

Database `benchmark.db` và thư mục `instance/` chỉ dùng để chạy local, không
cần đưa vào bài nộp. Không coi kết quả benchmark local là cam kết production.

## Kết quả đã chạy ngày 18/11/2026

Số liệu gốc nằm trong `reports/20261118-043628-983800/`.

| Kịch bản | Request | RPS | p95 | p99 | Lỗi |
| --- | ---: | ---: | ---: | ---: | ---: |
| A — 10 user | 143 | 4,85 | 12 ms | 30 ms | 0 |
| B — 50 user | 1.382 | 23,29 | 14 ms | 32 ms | 0 |
| C — 200 user | 2.903 | 98,30 | 69 ms | 120 ms | 0 |

Cả ba đạt ngưỡng kiểm tra local. Toàn bộ **49 kiểm thử của service tuần 7**
cũng pass với môi trường dependency dùng cho bài này. Server được dừng sau
khi đo xong; có thể chạy lại bằng runner ở trên.

## Tài liệu tham khảo

- [Locust: viết kịch bản](https://docs.locust.io/en/stable/writing-a-locustfile.html)
- [Locust: chạy headless](https://docs.locust.io/en/stable/running-without-web-ui.html)
- [Locust: cấu hình CSV/HTML](https://docs.locust.io/en/stable/configuration.html)

Thời gian `--run-time` tính cả giai đoạn tăng user. A/B/C là các lần đo riêng,
không phải phép đo soak test hoặc phép chứng minh giới hạn công suất tối đa.

# Bài tập về nhà 2 - Phân tích load test và đề xuất SLO

**Endpoint:** `GET /api/v1/products?page=<1..50>&size=20`

## Mục tiêu và môi trường

Đo GET /api/v1/products của service tuần 7: thao tác duyệt danh mục có truy vấn lấy trang, đếm tổng sản phẩm và serialize JSON. Database SQLite riêng có 1.000 sản phẩm, 20 sản phẩm/trang; Gunicorn 25.3.0 với 2 sync worker, Flask 3.1.3, Locust 2.47.0, Python 3.12.14. Máy macOS-26.5.2-x86_64-i386-64bit, 12 CPU logic. Đo ngày 18/11/2026, giờ Việt Nam.

## Kịch bản và cách đo

Warmup 10 giây được tách khỏi kết quả. A: 10 user, tăng 2 user/giây, chạy 30 giây; B: 50 user, tăng 5 user/giây, chạy 60 giây; C: 200 user, tăng 50 user/giây, chạy 30 giây. User chọn ngẫu nhiên trang 1-50, nghỉ 1-3 giây; timeout 5 giây. HTTP khác 200, JSON sai, sai phân trang hoặc sai kiểu dữ liệu đều tính là lỗi. Latency đo từ client Locust, bao gồm thời gian nhận body; không đo thời gian render giao diện.

| Kịch bản | Request | RPS | p50 (ms) | p95 (ms) | p99 (ms) | Lỗi | SLO |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| A | 143 | 4.85 | 6 | 12 | 30 | 0% | Đạt |
| B | 1382 | 23.29 | 6 | 14 | 32 | 0% | Đạt |
| C | 2903 | 98.30 | 7 | 69 | 120 | 0% | Đạt |

## Nhận xét từ số đo

Kịch bản C có p95 cao nhất: 69 ms. Tổng 4.428 request, 0 lỗi; các kịch bản đạt ngưỡng quan sát: A, B, C. Khi tăng user, nhiều request có thể phải chờ hai worker; cần CPU, pool và query trace để xác nhận nút thắt, không kết luận nguyên nhân chỉ từ latency. RPS chịu ảnh hưởng của thời gian nghỉ 1-3 giây; 200 user không đồng nghĩa 200 RPS hoặc 200 request cùng lúc.

## SLO đề xuất và áp dụng CI

Đề xuất tạm cho luồng duyệt danh mục: p95 < 300 ms, tỉ lệ request lỗi < 1%. Ngưỡng 300 ms theo mốc thực hành buổi 8, dành ngân sách phản hồi cho API trong luồng xem sản phẩm; cần xác nhận lại bằng kỳ vọng người dùng và telemetry production. Dùng A làm smoke gate CI: ít nhất 100 request, cùng dữ liệu và cấu hình, đạt cả hai ngưỡng; exit code khác 0 khi không đạt. Chạy B để kiểm tra mức tải dự kiến trước release; số 50 user là giả định thực hành.

## Giới hạn và bằng chứng

Mỗi kịch bản mới chạy một lần, tính cả ramp-up; percentile Locust được làm tròn theo histogram. API và máy tạo tải cùng máy, DB SQLite, không có TLS hoặc độ trễ Internet. Kết quả chỉ xác nhận các lần đo local, chưa chứng minh SLO production, công suất tối đa hoặc rò rỉ tài nguyên. Cần lặp lại, đo trên staging giống production và theo dõi SLI dài hạn. Bảng dùng số liệu cuối phiên từ HTML, được trích sang `*_final.json` và `*_final_stats.csv`; CSV mặc định là snapshot định kỳ và có thể thiếu request ở giây cuối. Số liệu gốc: reports/20261118-043628-983800/ (HTML, CSV, log, environment.json).

Tham khảo cách chạy và đo của Locust: [headless](https://docs.locust.io/en/stable/running-without-web-ui.html), [kịch bản](https://docs.locust.io/en/stable/writing-a-locustfile.html).

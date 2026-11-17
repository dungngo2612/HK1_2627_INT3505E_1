# Lab 4 — Load test Books API với Locust

## Cách thực hiện

- Dùng Books API từ starter `TrinhLK/lab08-starter`, commit
  `b97f793ebf47b6c8a723324bb888f510c64f71ed`. `app.py` và `models.py` giữ
  nguyên; phần mở rộng thực hành nằm trong `benchmark_app.py`.
- Mỗi kịch bản có database SQLite mới, 1.000 sách, 25 năm xuất bản từ
  2000 đến 2024. Gunicorn dùng 2 sync worker, mỗi worker có pool 5,
  `max_overflow=0`. Dữ liệu và server được tạo lại trước từng lần đo.
- Locust có trọng số list/read/create/search là **3:2:1:1**. User nghỉ
  1–3 giây giữa các task; timeout HTTP 5 giây. ID đọc nằm trong 1–50 đã seed,
  vì vậy 404 ở đây sẽ được tính là lỗi. Response 200/201 còn được kiểm tra
  JSON, schema Book và điều kiện lọc năm.
- `search_by_year(year)` gọi `GET /books?year=...`. Server có xác suất
  **1% trên mỗi request tìm theo năm** trả HTTP 500 với code
  `INJECTED_FAILURE`; các request lỗi vẫn được Locust ghi nhận là failure.
  Đây là HTTP 500 thật từ server. Vì search chỉ chiếm khoảng 1/7 task,
  tỉ lệ lỗi tổng kỳ vọng xấp xỉ **0,143%**, không phải 1% toàn bộ request.
  Mẫu ngắn có thể lệch hoặc chưa xuất hiện lỗi.
- A: `-u 10 -r 2 -t 30s`; B: `-u 50 -r 5 -t 60s`;
  C: `-u 200 -r 50 -t 30s`. Mỗi server được warmup bằng 10 request đọc
  trước khi Locust chạy; các request này không vào số liệu. Thời gian đo
  tính cả ramp-up. Một lần chạy cho mỗi kịch bản, API và Locust cùng máy.

## Kết quả đo A/B/C

| Kịch bản | User | Request | Lỗi | Fail rate | RPS | p50 | p95 | p99 | p95 < 300 ms |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| A | 10 | 145 | 0 | 0.000% | 4.93 | 5 ms | 17 ms | 50 ms | Đạt |
| B | 50 | 1394 | 3 | 0.215% | 23.48 | 5 ms | 18 ms | 53 ms | Đạt |
| C | 200 | 2866 | 6 | 0.209% | 96.80 | 6 ms | 70 ms | 110 ms | Đạt |

Tổng A/B/C: **4405 request, 9 lỗi**.

### Theo từng endpoint

| Kịch bản | Endpoint | Request | Fail rate | p95 |
| --- | --- | ---: | ---: | ---: |
| A | `GET /books` | 58 | 0.000% | 26 ms |
| A | `GET /books/{id}` | 48 | 0.000% | 18 ms |
| A | `GET /books?year={year}` | 15 | 0.000% | 15 ms |
| A | `POST /books` | 24 | 0.000% | 15 ms |
| B | `GET /books` | 577 | 0.000% | 17 ms |
| B | `GET /books/{id}` | 409 | 0.000% | 18 ms |
| B | `GET /books?year={year}` | 203 | 1.478% | 28 ms |
| B | `POST /books` | 205 | 0.000% | 17 ms |
| C | `GET /books` | 1241 | 0.000% | 66 ms |
| C | `GET /books/{id}` | 814 | 0.000% | 70 ms |
| C | `GET /books?year={year}` | 403 | 1.489% | 78 ms |
| C | `POST /books` | 408 | 0.000% | 74 ms |

## 1. Kịch bản nào có p95 cao nhất? Vì sao?

**C có p95 cao nhất: 70 ms.**
Khi tăng tải, request có thể phải chờ hai worker xử lý và chờ SQLite
ghi tuần tự đối với POST. Đây là các cơ chế có thể giải thích biến động,
chưa phải kết luận nút thắt: cần CPU, thời gian truy vấn và thời gian chờ
worker/lock để xác nhận. So sánh p95 với p99 trong bảng để thấy phần đuôi.
200 user có thời gian nghỉ không đồng nghĩa với 200 request đồng thời.

## 2. Endpoint nào có fail rate tăng theo số user?

- `GET /books`: A/B/C = 0.000% / 0.000% / 0.000%; không tăng liên tiếp theo số user.
- `GET /books/{id}`: A/B/C = 0.000% / 0.000% / 0.000%; không tăng liên tiếp theo số user.
- `GET /books?year={year}`: A/B/C = 0.000% / 1.478% / 1.489%; tăng liên tiếp trong mẫu này.
- `POST /books`: A/B/C = 0.000% / 0.000% / 0.000%; không tăng liên tiếp theo số user.

Các lỗi 500 có code
`INJECTED_FAILURE` được tạo độc lập với số user; thay đổi tỉ lệ quan sát
ở endpoint search có thể do biến động của mẫu ngẫu nhiên. Số lỗi tuyệt đối
có thể tăng vì số request tăng. Không suy ra lỗi do tải chỉ từ xu hướng này.
Nếu POST có lỗi ngoài dự kiến, cần kiểm tra SQLite write lock/timeout trong
server log; nếu có lỗi kết nối hoặc HTTP 503, cần phân biệt với 500 giả lập.

Các thông báo failure ghi nhận được:

- A: không ghi nhận failure.
- B: `CatchResponseError('HTTP 500: INJECTED_FAILURE')`, số lần: 3.
- C: `CatchResponseError('HTTP 500: INJECTED_FAILURE')`, số lần: 6.


## 3. Kịch bản nào đạt SLO p95 < 300 ms? Baseline CI là gì?

Theo số đo lần này, **A, B, C** đạt mốc p95
nhỏ hơn 300 ms. SLO latency và tỉ lệ lỗi cần được đánh giá riêng; p95 tổng
cũng có thể bị ảnh hưởng bởi response lỗi trả nhanh. Vì vậy cần xem cả
endpoint và failure report, không dùng p95 để kết luận tất cả request đúng.

Đề xuất CI smoke gate dùng **A: 10 user, tăng 2 user/giây, 30 giây** với
ít nhất 100 request, p95 < 300 ms và fail rate < 1%. Lệnh `--ci` tắt
injection 500 để gate phản ánh lỗi thật. Dùng B trước release khi cần kiểm
tra mức tải giả định 50 user. Đo riêng fault injection để kiểm tra quan sát
lỗi, không trộn việc kỳ vọng 500 với tiêu chí không có lỗi bất ngờ.

```sh
week8/.venv/bin/python week8/lab4/run_load_test.py --scenario A --ci
```

## Bonus — Pool 5 khi 200 user truy cập

Phép đo riêng dùng **1 gthread worker, 50 thread**, 200 user, tăng
50 user/giây, 20 giây, chỉ tìm theo năm. Injection 500 được tắt. Mỗi request
giữ một kết nối DB thật trong **100 ms** để mô phỏng DB chậm; `max_overflow=0`,
`pool_timeout=1 giây`. Hai lần đo chỉ đổi pool từ 5 thành 20.
Đây là điều kiện mô phỏng riêng, không phải cấu hình A/B/C.

| Pool | Request | Fail rate | p95 | Kết nối hoạt động tối đa | Số pool timeout | Chờ pool trung bình |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 5 | 1130 | 12.65% | 2000 ms | 5 | 142 | 779.95 ms |
| 20 | 1804 | 0.11% | 300 ms | 20 | 0 | 12.29 ms |

Phân loại failure trong từng lần đo bonus:

- pool5: `CatchResponseError('HTTP 503: POOL_TIMEOUT')`, số lần: 142.
- pool5: `CatchResponseError('HTTP 0: invalid_json')`, số lần: 1.
- pool20: `CatchResponseError('HTTP 0: invalid_json')`, số lần: 2.

`HTTP 0` trong lần đo này nghĩa là không nhận được HTTP response;
chuỗi `invalid_json` do phiên bản hàm phân loại ban đầu ghi lại. Đây là
lỗi transport, chưa có chi tiết để xác định nguyên nhân. Không tính chúng
thành pool timeout. Mã hiện tại giữ nguyên thông báo transport gốc cho các
lần chạy tiếp theo.

p95 pool20 là **300 ms**, chưa đạt điều kiện nghiêm ngặt **p95 < 300 ms**; pool timeout ghi nhận **0 lần**.

Pool 5 chỉ cho tối đa 5 request giữ kết nối trong một tiến trình. Các
request tiếp theo phải chờ; hết một giây sẽ nhận HTTP **503 `POOL_TIMEOUT`**.
Với thời gian giữ 100 ms, giới hạn lý tưởng riêng phần này khoảng
5 / 0,1 = 50 lượt thành công/giây, chưa tính query và các chi phí khác.

Xác nhận bằng cả p95/failure của Locust và bộ đếm checkout/checkin, pool
timeout, thời gian chờ trong `pool5_pool_metrics.json` và
`pool20_pool_metrics.json`. Số checkout đồng thời chứng minh giới hạn pool;
200 user là số user ảo, không phải 200 connection DB. Pool là theo từng
process: A/B/C có 2 worker nên không được hiểu pool 5 là 5 cho cả server.
Bộ đếm server còn bao gồm warmup và request đã tới server dù client không
nhận được response; không dùng tổng checkout làm tổng request Locust.

## Dữ liệu gốc và giới hạn

Kết quả: [`reports/20261118-045118-366158/`](reports/20261118-045118-366158/).
HTML A/B/C, `*_stats.csv`, `*_stats_history.csv`, `*_failures.csv`,
`*_exceptions.csv`, server log, cấu hình và `summary.json` đều được giữ lại.
**Bảng phân tích dùng số liệu cuối phiên trong HTML**, được trích thêm ra
`*_final.json` và `*_final_stats.csv`. CSV mặc định là snapshot định kỳ nên
có thể thiếu request ở giây cuối; không dùng nó làm tổng cuối phiên.
Locust có thể trả exit code 1 khi ghi nhận HTTP 500/503; runner vẫn thu
thập báo cáo của phép thử lỗi có chủ đích. `--ci` trả thất bại khi gate
không đạt. Server được dừng khi phép đo kết thúc.

Percentile Locust dùng histogram làm tròn; mỗi kịch bản ở đây chỉ chạy
một lần, ngắn và trên máy local với SQLite. Cần lặp lại trên staging có
DB/server/network giống production trước khi cam kết SLO hay công suất.

Tham khảo: [starter giảng viên](https://github.com/TrinhLK/lab08-starter),
[Locust headless](https://docs.locust.io/en/stable/running-without-web-ui.html),
[SQLAlchemy QueuePool](https://docs.sqlalchemy.org/en/20/core/pooling.html).

# Lab 4 — Load test Books API với Locust

Bài làm theo trang 30 của slide buổi 8. Mã nguồn, báo cáo Markdown và kết
quả đo đều nằm trong `week8/lab4/`.

## Chạy từ thư mục gốc project

Môi trường dùng chung với bài tập về nhà 2: Python 3.12 trở lên,
macOS/Linux vì runner dùng Gunicorn.

```sh
python3 -m venv week8/.venv
week8/.venv/bin/python -m pip install -r week8/requirements-lock.txt
week8/.venv/bin/python week8/lab4/run_load_test.py --bonus
```

Runner tạo database riêng cho từng kịch bản, seed 1.000 sách, mở API trên
một cổng loopback còn trống, chạy Locust, lưu báo cáo rồi dừng server.
Không cần tự chạy Flask ở terminal khác. Thời gian khoảng 3–4 phút.
Mỗi lần chạy có một thư mục kết quả mới trong `reports/`.

## Kết quả đã chạy ngày 18/11/2026

Báo cáo đầy đủ: [analysis.md](analysis.md). Số liệu cuối phiên:

| Kịch bản | Request | Lỗi | p95 |
| --- | ---: | ---: | ---: |
| A — 10 user | 145 | 0 | 17 ms |
| B — 50 user | 1.394 | 3 | 18 ms |
| C — 200 user | 2.866 | 6 | 70 ms |

Chín lỗi A/B/C đều là `INJECTED_FAILURE` đúng thiết kế. Kết quả nằm trong
`reports/20261118-045118-366158/`, gồm cả bonus pool 5/20.

Bốn kiểm thử tự động pass. Một lần chạy CI riêng đã pass với 139 request,
0 lỗi, p95 12 ms; lưu tại `reports/20261118-045809-593212/`.

Khi dùng ZIP bài nộp, giải nén rồi chạy từ thư mục gốc đã giải nén theo
các lệnh cài đặt ở trên.

Chỉ chạy ba kịch bản bắt buộc:

```sh
week8/.venv/bin/python week8/lab4/run_load_test.py
```

| Kịch bản | User | Thêm user/giây | Thời gian | Báo cáo |
| --- | ---: | ---: | ---: | --- |
| A — baseline | 10 | 2 | 30 giây | `reports/<lần chạy>/A.html` |
| B — load test | 50 | 5 | 60 giây | `reports/<lần chạy>/B.html` |
| C — tăng tải nhanh | 200 | 50 | 30 giây | `reports/<lần chạy>/C.html` |

## Hoàn thành task tìm theo năm và giả lập lỗi

`locustfile.py` có bốn task list/read/create/search với trọng số 3:2:1:1,
nghỉ ngẫu nhiên 1–3 giây giữa task. `search_by_year(year)` gọi
`GET /books?year=...`, kiểm tra schema và năm của từng sách trả về.

`benchmark_app.py` bổ sung vào starter xác suất 1% trả HTTP 500 cho
request tìm theo năm, có code `INJECTED_FAILURE` và header
`X-Lab-Injected: true`. Lỗi được phát ở server và được Locust tính vào
failure. Với trọng số search là 1/7, tỉ lệ lỗi tổng kỳ vọng khoảng 0,143%;
mẫu ngắn có thể khác giá trị kỳ vọng.

Mỗi kịch bản dùng 2 sync worker, pool 5/worker, không overflow. Bonus dùng
1 gthread worker/50 thread để quan sát pool 5 cho toàn bộ tiến trình.

## Bonus connection pool

`--bonus` thêm hai lần đo `pool5` và `pool20`: cùng 200 user, tăng 50
user/giây, 20 giây, chỉ chạy search, tắt injection 500. Request giữ một
kết nối DB thật trong 100 ms để mô phỏng truy vấn chậm. `max_overflow=0`,
`pool_timeout=1 giây`; hết thời gian chờ trả HTTP 503 `POOL_TIMEOUT`.

Theo dõi đồng thời:

- HTML/CSV của Locust: p95, failure rate, RPS.
- `pool5_pool_metrics.json`, `pool20_pool_metrics.json`: số kết nối checkout
  đồng thời tối đa, số timeout và thời gian chờ pool.
- `*_failures.csv`: phân biệt `POOL_TIMEOUT` với `INJECTED_FAILURE`.

Điều kiện giữ kết nối 100 ms chỉ áp dụng cho bonus và được ghi rõ trong
`analysis.md`, không áp dụng cho A/B/C.

## Báo cáo và bài nộp

- [analysis.md](analysis.md): số đo thực tế, trả lời cả ba câu hỏi và bonus.
- `locustfile.py`: kịch bản bắt buộc và kịch bản bonus.
- `reports/<lần chạy>/A.html`, `B.html`, `C.html`: ba báo cáo bắt buộc.
- CSV, log, `summary.json`, `summary.csv`, `environment.json` và cấu hình
  từng lần đo: bằng chứng để kiểm tra lại.
- `*_final.json`, `*_final_stats.csv`: số liệu cuối phiên trích từ HTML.
  `summary.json` và `analysis.md` dùng số liệu này; CSV mặc định của Locust
  được ghi định kỳ nên có thể thiếu các request cuối phiên.
- `app.py`, `models.py`: bản gốc từ starter của giảng viên.
- `benchmark_app.py`, `run_load_test.py`, `analyze.py`: phần bổ sung để
  chạy phép đo và tự sinh báo cáo Markdown.
- `../locust_report.py`: đọc số liệu cuối phiên, dùng chung với bài tập về nhà 2.
- `starter_source.json`: URL, commit và SHA-256 hai file gốc.

Database `*.db`, `.venv`, cache Python và cache pytest không đưa vào ZIP.

## Kiểm tra và CI

```sh
week8/.venv/bin/python -m pytest week8/lab4/test_lab4.py -q
week8/.venv/bin/python week8/lab4/run_load_test.py --scenario A --ci
```

`--ci` tắt injection 500 và trả exit code khác 0 nếu dưới 100 request,
p95 >= 300 ms hoặc failure rate >= 1%. Trong phép thử injection/bonus,
Locust có thể trả exit code 1 vì có HTTP 500/503; runner vẫn thu thập
đầy đủ báo cáo. Exception trong task, lỗi khởi động hoặc thiếu request
vẫn làm runner thất bại. Chạy CI hoặc một kịch bản riêng không ghi đè
bản phân tích A/B/C đầy đủ.

## Nguồn starter

[TrinhLK/lab08-starter](https://github.com/TrinhLK/lab08-starter), commit
`b97f793ebf47b6c8a723324bb888f510c64f71ed`. Hai file `app.py`, `models.py`
được giữ nguyên để dễ đối chiếu; phần thêm của Lab 4 ở các file riêng.

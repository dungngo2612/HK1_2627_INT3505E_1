# lab08-starter — API Testing & Quality Assurance

**Flask 3.x / SQLAlchemy / pytest / OpenAPI / Postman / Locust**

## 1. Chuẩn bị và chạy API

Yêu cầu Python **3.11+** và Node.js **22** nếu chạy Newman/Spectral. Chạy từ thư mục gốc project.

```bash
python -m venv .venv
# Linux/macOS:
source .venv/bin/activate
# Windows PowerShell:
# .venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m app --port 5000
```

API: `http://127.0.0.1:5000` (chỉ chạy trên máy local). Thử:

```bash
curl http://127.0.0.1:5000/health
curl http://127.0.0.1:5000/books
curl -X POST http://127.0.0.1:5000/books \
  -H 'Content-Type: application/json' \
  -d '{"title":"API Design Patterns","author":"J.J. Geewax","year":2021}'
```

SQLite lưu tại `instance/books.db` (không commit lên Git). API không có authentication bắt buộc cho CRUD để dễ thực hành functional test. `POST /auth/login` chỉ là **mô phỏng cục bộ**, tài khoản `lab/lab`; token không cấp quyền và **không được dùng trong production**.

### REST endpoints

| Method | Path | Trả về |
|---|---|---|
| GET | `/health` | 200 |
| GET | `/books?author=&year=&page=` | 200, JSON array, page 1-based, 20 items/page |
| GET | `/books/{id}` | 200 / 400 (ID sai định dạng) / 404 |
| POST | `/books` | 201 / 400 / 409 (ISBN trùng) |
| PUT | `/books/{id}` | 200 / 400 / 404 / 409 |
| DELETE | `/books/{id}` | 204 (không body) / 400 / 404 |
| POST | `/auth/login` | 200 / 401, chỉ để minh họa |

Schema JSON của Book trả `id`, `title`, `author`, `year`, `isbn`. Trong request, `title` và `author` là required. `year`/`isbn` tùy chọn; ISBN nếu có là 13 chữ số và unique. **POST lặp lại chỉ 409 nếu xảy ra xung đột ISBN**, không phải vì lặp payload nói chung. DELETE lần đầu 204, lần sau 404; điều này không mâu thuẫn với idempotency vì trạng thái tài nguyên sau hai lần là như nhau.

## 2. Lab 1 — pytest

```bash
python -m pytest -v
```

Hai smoke test có sẵn nhằm xác nhận starter hoạt động. Lab 1 gồm **4 test bắt buộc + 1 bonus** trong `tests/test_lab01.py`. Các fixture `app`, `client`, `sample_book` nằm trong `tests/conftest.py`. Mỗi test dùng một cơ sở dữ liệu riêng.

## 3. Lab 2 — OpenAPI/Spectral

`GET /books` có `operationId: listBooks`, response 204 của `DELETE /books/{id}` đã bỏ `content`, và `Book.year` dùng `type: integer` với `nullable: true`.

```bash
npm install -g @stoplight/spectral-cli@6.17.1
spectral lint openapi.yaml --ruleset .spectral.yml
python -m pytest -v tests/test_lab02.py
```

Rule `response-200-has-schema-fields` báo lỗi khi response 200 thiếu schema hoặc schema không mô tả trường nào. Với mảng, rule kiểm tra schema của `items`, kể cả khi `items` dùng `$ref`. GitHub Actions chạy Spectral khi push hoặc mở, cập nhật pull request. Kết quả lint trước và sau khi sửa nằm trong `reports/lab02-spectral.log`.

`test_get_book_response_matches_openapi` gọi Flask thật rồi đối chiếu JSON trả về với schema `Book`. Test bắt các trường bắt buộc bị thiếu, trường thừa và giá trị sai kiểu, ví dụ `year` bị serialize thành chuỗi.

## 4. Lab 3 — Postman/Newman

File `books-api.postman_collection.json` chứa 5 happy-path requests chạy theo thứ tự: list → create → get → update → delete. Request tạo lưu `book_id` trong collection variables. Hãy:

- Tạo folder `error-cases/` với **POST /books** thiếu `title` và **GET /books/9999**.
- Thêm **ít nhất 2 `pm.test` cho mỗi error request**: HTTP status và JSON `code`/`message`.
- Chạy bằng Newman, lưu JUnit report.

```bash
npm install -g newman
newman run books-api.postman_collection.json \
  -e postman/local.postman_environment.json \
  -r cli,junit --reporter-junit-export reports/junit.xml
```

Lưu ý: cần chạy server trước. `data.csv` là dữ liệu ví dụ để thực hành data-driven iteration; khi sử dụng `-d data.csv`, collection sẽ lặp theo số hàng. Đừng hard-code credentials/tokens trong file đẩy lên Git.

## 5. Lab 4 — Locust

`performance/locustfile.py` là baseline có weighted tasks; `performance/locustfile_realistic.py` minh hoạ flow có state và demo login. Chạy API trong terminal 1; terminal 2:

```bash
mkdir -p reports
locust -f performance/locustfile.py --headless -H http://127.0.0.1:5000 \
  -u 10 -r 2 -t 30s --html reports/A.html
locust -f performance/locustfile.py --headless -H http://127.0.0.1:5000 \
  -u 50 -r 5 -t 60s --html reports/B.html
locust -f performance/locustfile.py --headless -H http://127.0.0.1:5000 \
  -u 200 -r 50 -t 30s --html reports/C.html
```

Hoàn thiện TODO `search_by_year` và nếu tạo 1% failure giả lập, **ghi rõ** đó là HTTP 500 do server phát hay client-side `response.failure()` của Locust. Điền `performance/analysis.md` bằng kết quả **đo thực tế**; báo cáo p95, failure rate, RPS, nhận xét giới hạn phép đo. Load test chạy Flask development server + SQLite chỉ có ý nghĩa thực hành, không thể khẳng định SLO production.

## 6. Cấu trúc thư mục

```text
lab08-starter/
├── app.py, models.py, tools.py
├── openapi.yaml, .spectral.yml
├── books-api.postman_collection.json
├── data.csv, requirements.txt, pytest.ini
├── tests/
│   ├── conftest.py
│   ├── test_smoke.py             # supplied baseline
│   ├── test_lab01.py             # Lab 1 exercises
│   └── test_lab02.py             # Flask response contract
├── postman/
│   ├── books-api.postman_collection.json
│   └── local.postman_environment.json
├── performance/
│   ├── locustfile.py
│   ├── locustfile_realistic.py
│   └── analysis.md
├── reports/
└── .github/workflows/spectral.yml
```

## Lưu ý:

- `pytest` và Newman đều chạy được độc lập sau khi đã cài dependency, không cần Postman GUI.

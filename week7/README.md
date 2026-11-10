# Tuần 7 - Backend Service

Bài làm được chia thành **5 thư mục tương ứng 5 yêu cầu cuối slide**. Mỗi thư mục có code và README hướng dẫn kiểm tra riêng. Các phần ghép thành cùng một backend service; bài 2 dùng lại Product của bài 1, bài 3 đóng gói service, bài 4 bổ sung health check và bài 5 kiểm thử service.

| Bài | Thư mục | Nội dung và cách kiểm tra |
| --- | --- | --- |
| 1 | [bai1_product_api](bai1_product_api/README.md) | Product model/schema, 6 endpoint CRUD và reserve; xem `models.py`, `schemas.py`, `services.py`, `routes.py` |
| 2 | [bai2_orders](bai2_orders/README.md) | Order/OrderItem, đơn nhiều sản phẩm, transaction và eager loading |
| 3 | [bai3_docker](bai3_docker/README.md) | Dockerfile, Compose, Gunicorn, entrypoint và WSGI |
| 4 | [bai4_healthcheck](bai4_healthcheck/README.md) | `/healthz` và `/ready`, phân biệt process sống với DB sẵn sàng |
| 5 | [bai5_pytest](bai5_pytest/README.md) | Pytest cho Product, Order, health, OpenAPI và migration; kiểm tra N+1 |

## Cài đặt và chạy local

Cần Python 3.12 trở lên. Chạy từ thư mục `week7`:

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements-dev.txt
python -m pip install --no-deps -e .
flask --app product_api:create_app db upgrade
flask --app product_api:create_app run --port 8000
```

Mặc định dùng SQLite tại `instance/products.db`. Đổi database qua biến môi trường `DB_URL`, ví dụ `postgresql+psycopg://user:password@host/dbname`; chạy migration trên database mới trước khi phục vụ request. Có thể sao chép `.env.example` thành `.env` khi chạy Flask CLI; không commit `.env` thật.

- Swagger UI: <http://localhost:8000/docs>
- OpenAPI JSON: <http://localhost:8000/openapi.json>
- Product API: <http://localhost:8000/api/v1/products>
- Order API: <http://localhost:8000/api/v1/orders>
- Health: <http://localhost:8000/healthz> và <http://localhost:8000/ready>

Swagger UI tải tài nguyên từ CDN, cần Internet khi mở trang. API và endpoint OpenAPI JSON không phụ thuộc CDN.

## Kiểm tra từng bài

Các lệnh pytest dưới đây chạy từ `week7` sau khi cài đặt môi trường:

```sh
# Bài 1: Product API, CRUD, phân trang, reserve và đặt trước đồng thời
python -m pytest bai5_pytest/test_products.py -q

# Bài 2: Order/OrderItem, rollback, giá tại lúc đặt và eager loading
python -m pytest bai5_pytest/test_orders.py -q

# Bài 4: health check, OpenAPI và định dạng lỗi/log
python -m pytest bai5_pytest/test_health_and_contract.py -q

# Bài 5: toàn bộ kiểm thử, gồm migration upgrade/downgrade
python -m pytest -q
```

Bài 3 chạy riêng từ thư mục Docker:

```sh
cd bai3_docker
docker compose config --quiet
docker compose up --build -d --wait
docker compose logs -f api
docker compose down
```

Compose dùng PostgreSQL 16, chạy migration trước khi khởi động Gunicorn và ánh xạ cổng host 8000 vào cổng container 5000. Không cần sửa source hoặc tạo `.env` để chạy cấu hình local mặc định. `docker compose down` giữ dữ liệu; chỉ thêm `-v` khi muốn xóa database của bài thực hành.

## Phần dùng chung

```text
week7/
  bai1_product_api/     # Bài 1: Product
  bai2_orders/          # Bài 2: Order và OrderItem
  bai3_docker/          # Bài 3: đóng gói và triển khai
  bai4_healthcheck/     # Bài 4: health endpoint
  bai5_pytest/          # Bài 5: kiểm thử
  product_api/          # Factory, db/migrate, lỗi, log, schema dùng chung
  migrations/           # Lược đồ Product, Order, OrderItem dùng chung
  pyproject.toml
  requirements.txt
  requirements-dev.txt
  .env.example
```

`product_api/factory.py` ghép các Blueprint, cấu hình DB từ môi trường và đăng ký extension. `product_api/extensions.py` chứa `db`/`migrate`; `errors.py` trả lỗi JSON; `logging_config.py` ghi log request có request ID và thời gian xử lý. Các schema input/phân trang/lỗi dùng chung nằm trong `product_api/schemas.py`.

Lỗi JSON có dạng `{"error":"out_of_stock","detail":"Insufficient stock for this product."}`. Dùng `400` cho JSON sai cú pháp, `404` cho tài nguyên không tồn tại/archived, `409` cho xung đột và `422` cho input không hợp lệ. Lỗi validate có thêm `fields`; input chứa trường ngoài schema bị từ chối.

Migration ban đầu gồm PK, FK, unique index, check constraint và default boolean tương thích SQLite/PostgreSQL. Sau khi sửa Model:

```sh
flask --app product_api:create_app db migrate -m 'Describe the model change'
# Đọc và rà soát revision trước khi áp dụng.
flask --app product_api:create_app db upgrade
flask --app product_api:create_app db check
```

Service dùng migration; `db.create_all()` chỉ dùng trong fixture test. Đây là bài thực hành, chưa bổ sung authentication hoặc payment.

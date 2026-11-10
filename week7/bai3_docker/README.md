# Bài 3 - Đóng gói service bằng Docker

Yêu cầu: đóng gói backend bằng Dockerfile và Docker Compose để chạy trên máy khác mà không sửa source.

## File cần kiểm tra

| File | Vai trò |
| --- | --- |
| `Dockerfile` | Build nhiều stage với Python 3.12; runtime chạy bằng user `app` |
| `docker-compose.yml` | API và PostgreSQL 16, volume dữ liệu, health check, cổng 8000 |
| `entrypoint.sh` | Chạy migration trước khi khởi động Gunicorn |
| `gunicorn.conf.py` | Cấu hình WSGI server |
| `wsgi.py` | Entry point gọi Application Factory dùng chung |

Build context là thư mục cha `week7`, vì image cần source ở bài 1, bài 2, bài 4, package dùng chung và migration. Dockerfile vẫn nằm trong bài 3; `.dockerignore` dùng ở thư mục `week7`.

## Chạy và kiểm tra

Mở terminal tại thư mục `bai3_docker`:

```sh
docker compose config --quiet
docker compose up --build -d --wait
docker compose ps
```

Cấu hình mặc định đủ chạy local, không cần tạo `.env`. Các URL:

- Product API: <http://localhost:8000/api/v1/products>
- Order API: <http://localhost:8000/api/v1/orders>
- Swagger UI: <http://localhost:8000/docs>
- OpenAPI: <http://localhost:8000/openapi.json>
- Health: <http://localhost:8000/healthz> và <http://localhost:8000/ready>

```sh
curl -i http://localhost:8000/healthz
curl -i http://localhost:8000/ready
docker compose logs --tail=50 api
docker compose down
```

`down` giữ volume database. Chỉ thêm `-v` khi muốn xóa dữ liệu của bài thực hành.

## Cấu hình tùy chọn

File mẫu nằm tại `../.env.example`. Muốn dùng file `.env` ở thư mục `week7`, tạo file từ mẫu rồi chỉ định rõ:

```sh
cp ../.env.example ../.env
docker compose --env-file ../.env up --build -d --wait
```

Compose mặc định đọc `.env` cạnh file Compose, nên lệnh `--env-file ../.env` cần có nếu lưu cấu hình ở thư mục cha. Mật khẩu mặc định chỉ dành cho môi trường local.

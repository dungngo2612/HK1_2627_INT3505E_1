# Bài 4 - Liveness và readiness

## Code cần xem

`health.py` khai báo hai endpoint độc lập. Application Factory trong `product_api/factory.py` đăng ký blueprint này cùng các bài 1 và 2.

| Endpoint | Ý nghĩa | Database hoạt động | Database lỗi |
| --- | --- | --- | --- |
| `GET /healthz` | Process còn sống; không truy vấn DB | 200 | 200 |
| `GET /ready` | Service kết nối được DB | 200 | 503 |

## Chạy và kiểm tra từ thư mục week7

```sh
flask --app product_api:create_app db upgrade
flask --app product_api:create_app run --port 8000
```

Trong terminal khác:

```sh
curl -i http://localhost:8000/healthz
curl -i http://localhost:8000/ready
```

Kiểm tra tự động khi DB bị lỗi:

```sh
python -m pytest bai5_pytest/test_health_and_contract.py -k liveness -q
```

Test mô phỏng lỗi truy vấn SQL: `/healthz` vẫn trả 200, `/ready` trả 503; sau khi bỏ lỗi, readiness trở lại 200. Khi chạy bằng Docker ở bài 3, API healthcheck dùng `/ready`.

# Bài 1 - Product API CRUD

Hoàn thiện Lab 1 với 6 endpoint của Product. Bài này dùng chung Application Factory, database và global error handler trong `product_api/`.

## Code cần xem

| File | Nội dung |
| --- | --- |
| `models.py` | Product, unique SKU, ràng buộc giá và tồn kho không âm |
| `schemas.py` | Validate input, PATCH, reserve và serialize response |
| `services.py` | CRUD, soft-delete và trừ tồn kho bằng UPDATE có điều kiện |
| `routes.py` | Blueprint `/api/v1/products`, khai báo OpenAPI |

## Chạy từ thư mục week7

Cài dependency theo README chính trước, rồi chạy:

```sh
flask --app product_api:create_app db upgrade
flask --app product_api:create_app run --port 8000
```

Application Factory chạy chung các bài; phần Product của bài 1 nằm tại `/api/v1/products`.

| Method | Đường dẫn | Kiểm tra |
| --- | --- | --- |
| GET | `/api/v1/products?page=1&size=20` | List phân trang, loại trừ sản phẩm archived |
| GET | `/api/v1/products/{id}` | Lấy một sản phẩm hoặc 404 |
| POST | `/api/v1/products` | Tạo mới 201, SKU trùng 409 |
| PATCH | `/api/v1/products/{id}` | Chỉ cập nhật field có trong body |
| DELETE | `/api/v1/products/{id}` | Soft-delete, response 204 |
| POST | `/api/v1/products/{id}/reserve` | Trừ kho; thiếu hàng 409, không cho tồn âm |

Ví dụ tạo sản phẩm:

```sh
curl -s -X POST http://localhost:8000/api/v1/products \
  -H 'Content-Type: application/json' \
  -d '{"sku":"BOOK-001","name":"Flask Book","price_cents":1500,"qty_in_stock":10}'
```

Kiểm tra tự động, vẫn đứng tại `week7`:

```sh
python -m pytest bai5_pytest/test_products.py -q
```

Test bao gồm CRUD, validation, phân trang, soft-delete, duplicate SKU và 8 request reserve đồng thời vào tồn kho 3.

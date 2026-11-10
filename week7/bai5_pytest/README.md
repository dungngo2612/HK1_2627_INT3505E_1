# Bài 5 - Pytest và eager loading

Chạy các lệnh dưới đây từ thư mục `week7`, sau khi cài dependency và package theo README chính.

Chạy toàn bộ kiểm thử:

```sh
python -m pytest bai5_pytest -q
```

Kiểm tra theo từng phần:

| Phần | Lệnh chạy từ `week7` |
| --- | --- |
| Bài 1 - Product CRUD, phân trang, soft-delete, reserve | `python -m pytest bai5_pytest/test_products.py -q` |
| Bài 2 - Order/OrderItem, rollback, eager loading | `python -m pytest bai5_pytest/test_orders.py -q` |
| Bài 3 - Migration dùng khi khởi động service | `python -m pytest bai5_pytest/test_migrations.py -q` |
| Bài 4 - Liveness và readiness | `python -m pytest bai5_pytest/test_health_and_contract.py -k liveness -q` |
| OpenAPI, JSON error và request logging | `python -m pytest bai5_pytest/test_health_and_contract.py -q` |

Bài 3 còn cần kiểm tra build/chạy Docker theo hướng dẫn riêng trong thư mục bài 3; pytest migration không thay thế kiểm thử container.

`test_orders_use_constant_query_count_with_eager_loading` so sánh GET danh sách 1 đơn với 10 đơn. Cả hai trường hợp đều dùng 3 câu SELECT: lấy đơn, lấy items kèm Product và đếm tổng đơn.

`test_concurrent_reservations_cannot_oversell` gửi 8 request reserve vào tồn kho 3, kiểm tra 3 request thành công, 5 request trả `409` và tồn kho cuối bằng 0.

Các fixture tạo database SQLite riêng cho từng test. Test migration dùng file SQLite tạm và thực hiện upgrade, kiểm tra schema, downgrade rồi upgrade lại.

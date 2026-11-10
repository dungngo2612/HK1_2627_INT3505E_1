# Bài 2 - Order và OrderItem

Bài này mở rộng Product của bài 1 bằng blueprint riêng `/api/v1/orders`. Mỗi Order có nhiều OrderItem; mỗi item tham chiếu một Product và lưu giá tại thời điểm đặt.

## Code cần xem

| File | Nội dung |
| --- | --- |
| `models.py` | Order, OrderItem, hai FK và quan hệ với Product |
| `schemas.py` | Input nhiều item, output nested Product và tổng tiền |
| `services.py` | Một transaction cho cả đơn, rollback khi thiếu hàng, eager loading |
| `routes.py` | POST/list/detail của `/api/v1/orders` |

`models.py` dùng lại Product từ bài 1. `services.py` dùng lại `take_stock()` của bài 1; toàn bộ item được xử lý trong cùng transaction.

## Chạy và kiểm tra từ thư mục week7

```sh
flask --app product_api:create_app db upgrade
flask --app product_api:create_app run --port 8000
```

Tạo sản phẩm qua bài 1 trước. Ví dụ khi database có Product ID 1 và đủ tồn kho:

```sh
curl -s -X POST http://localhost:8000/api/v1/orders \
  -H 'Content-Type: application/json' \
  -d '{"customer_name":"Nguyen Van A","items":[{"product_id":1,"qty":2}]}'

curl -s 'http://localhost:8000/api/v1/orders?page=1&size=20'
curl -s http://localhost:8000/api/v1/orders/1
```

Thêm nhiều phần tử trong `items` để đặt nhiều loại sản phẩm. Một sản phẩm chỉ xuất hiện một lần trong mỗi đơn. Tạo đơn tự trừ tồn kho; không gọi `/reserve` trước cho cùng lần đặt hàng.

Kiểm tra tự động:

```sh
python -m pytest bai5_pytest/test_orders.py -q
```

Test xác minh nhiều item, snapshot giá, soft-delete không mất lịch sử, rollback toàn bộ khi một item thất bại và phân trang. Test eager loading so sánh GET 1 với 10 đơn, đều dùng 3 SELECT.

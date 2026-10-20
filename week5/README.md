# Bài 2 — Phân trang Books

Ứng dụng Flask + SQLAlchemy cho `GET /api/v1/books` (cũng có đường dẫn
`/books`). API hỗ trợ phân trang offset, cursor, lọc theo thể loại và sắp xếp
theo nhiều trường.

## Chạy ứng dụng

```sh
cd week5
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Ứng dụng chạy ở `http://127.0.0.1:5000`. Lần đầu khởi động, ứng dụng tạo
SQLite database và thêm sách mẫu. Có thể đặt biến môi trường `DATABASE_URL`
để dùng database khác.

## Phân trang và truy vấn

Offset:

```http
GET /api/v1/books?strategy=offset&offset=0&limit=3&genre=technology&sort=-price_vnd,title
```

Cursor:

```http
GET /api/v1/books?strategy=cursor&limit=3&genre=technology&sort=-price_vnd,title
```

Gửi `page.next_cursor` từ response vào request kế tiếp; giữ nguyên `sort` và
`genre`. `limit` mặc định là 20, tối đa 100. `genre` không phân biệt chữ hoa,
chữ thường.

`sort` nhận các trường `id`, `title`, `author`, `genre`, `price_vnd` và
`published_year`. Dấu `-` phía trước nghĩa là giảm dần; ví dụ
`sort=-price_vnd,title` sắp giá giảm dần, rồi tên sách tăng dần. API thêm `id`
tăng dần làm khóa phụ nếu danh sách sort chưa có `id`.

Cursor mã hóa các giá trị sort cùng thể loại lọc bằng Base64 URL-safe. Cursor
không chứa dữ liệu nhạy cảm và hiện chưa được ký HMAC. Tham số không hợp lệ
trả JSON error với HTTP 400.

## Kiểm tra

Chạy từ thư mục gốc project:

```sh
python -m unittest discover -s week5 -p 'test_*.py' -v
```

## Postman

Import [`Bookstore Pagination.postman_collection.json`](Bookstore%20Pagination.postman_collection.json).
Collection có request cho offset, trang cursor đầu, trang cursor tiếp theo và
kiểm tra sort không hợp lệ. Request trang đầu tự lưu cursor để dùng ở request
kế tiếp.

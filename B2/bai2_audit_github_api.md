# Bài 2: Audit một số endpoint của GitHub REST API

Nguồn tham khảo chính: https://docs.github.com/en/rest

Mình chọn GitHub REST API vì API này có tài liệu khá rõ, dễ kiểm tra các yếu tố REST như method, status code, header, phân trang và cache. Phần dưới đây không audit toàn bộ GitHub API mà chỉ lấy 5 endpoint tiêu biểu để đối chiếu với các tiêu chí đã học.

## Cách đánh giá

Các endpoint được xem theo những điểm sau:

| Tiêu chí | Nội dung kiểm tra |
|---|---|
| HTTP method | Method có đúng với hành động trên resource không |
| Status code | Có dùng status code đúng ngữ nghĩa không |
| URI | URI có biểu diễn resource rõ ràng, hạn chế động từ không |
| Header | Có dùng các header cần thiết như `ETag`, `Location`, `Link` không |
| Stateless | Việc xác thực có tách khỏi session phía server không |

## 1. `GET /repos/{owner}/{repo}`

Endpoint này dùng để lấy thông tin chi tiết của một repository.

| Mục | Nhận xét |
|---|---|
| Method | `GET` |
| Ví dụ | `GET https://api.github.com/repos/torvalds/linux` |
| Thành công | `200 OK` |
| Lỗi thường gặp | `404 Not Found` nếu repo không tồn tại, bị private hoặc người gọi không có quyền |
| Header đáng chú ý | `Content-Type`, `ETag`, `Cache-Control`, các header rate limit |
| Auth | Không bắt buộc với public repo, nhưng token giúp tăng rate limit |

Đánh giá: URI `/repos/{owner}/{repo}` mô tả đúng resource, không đưa hành động vào đường dẫn. `GET` là method phù hợp vì chỉ đọc dữ liệu, không làm thay đổi trạng thái server. Endpoint này cũng dùng `ETag`, nên client có thể gửi `If-None-Match` ở lần sau để tiết kiệm băng thông nếu dữ liệu chưa đổi.

Kết luận: endpoint này RESTful tốt, đặc biệt ở phần cache/conditional request.

## 2. `POST /user/repos`

Endpoint này tạo một repository mới cho user đang đăng nhập.

| Mục | Nhận xét |
|---|---|
| Method | `POST` |
| Ví dụ | `POST https://api.github.com/user/repos` |
| Body mẫu | `{"name": "my-repo", "private": false}` |
| Thành công | `201 Created` |
| Lỗi thường gặp | `401 Unauthorized`, `422 Unprocessable Entity` |
| Header đáng chú ý | `Content-Type`, `Location` |
| Auth | Bắt buộc, thường dùng Bearer token |

Đánh giá: `POST` hợp lý vì client yêu cầu server tạo resource mới. Khi tạo thành công, API trả `201 Created`, đúng hơn so với việc trả `200 OK` chung chung. Header `Location` cũng có ích vì cho client biết resource mới nằm ở đâu.

Điểm cần lưu ý là URI `/user/repos` hơi khác kiểu `/repos/...`, vì nó dựa trên user hiện tại trong token. Tuy vậy endpoint vẫn stateless vì server không cần session cookie; thông tin user được lấy từ access token đi kèm request.

Kết luận: RESTful tốt, status code và header trả về rõ ràng.

## 3. `PATCH /repos/{owner}/{repo}`

Endpoint này cập nhật một phần thông tin repository, ví dụ mô tả, homepage, visibility hoặc một số cấu hình khác.

| Mục | Nhận xét |
|---|---|
| Method | `PATCH` |
| Ví dụ | `PATCH https://api.github.com/repos/torvalds/linux` |
| Body mẫu | `{"description": "Linux kernel"}` |
| Thành công | `200 OK` |
| Lỗi thường gặp | `403 Forbidden`, `404 Not Found`, `422 Unprocessable Entity` |
| Header đáng chú ý | `Content-Type` |
| Auth | Bắt buộc, người gọi phải có quyền quản trị repo |

Đánh giá: dùng `PATCH` là đúng vì request chỉ gửi những trường cần đổi, không thay thế toàn bộ repository như `PUT`. URI vẫn giữ nguyên resource chính là repository, không dùng dạng như `/updateRepo`, nên phù hợp với cách thiết kế REST.

Một điểm mình thấy có thể bàn thêm là API trả `200 OK` kèm body mới nhất của repo. Cách này tiện cho client vì sau khi cập nhật không cần gọi thêm một request `GET`.

Kết luận: endpoint này dùng method và URI đúng với mục đích cập nhật một phần.

## 4. `GET /repos/{owner}/{repo}/issues`

Endpoint này lấy danh sách issue của một repository, có hỗ trợ filter và pagination.

| Mục | Nhận xét |
|---|---|
| Method | `GET` |
| Ví dụ | `GET /repos/torvalds/linux/issues?state=open&page=2&per_page=30` |
| Query thường dùng | `state`, `labels`, `assignee`, `page`, `per_page` |
| Thành công | `200 OK` |
| Lỗi thường gặp | `404 Not Found`, `422 Unprocessable Entity` |
| Header đáng chú ý | `Link`, `ETag`, các header rate limit |
| Auth | Không bắt buộc với public repo |

Đánh giá: `/repos/{owner}/{repo}/issues` thể hiện quan hệ cha-con khá rõ: issues thuộc về một repo cụ thể. Các tham số lọc được đặt trong query string, hợp lý hơn so với tạo nhiều endpoint riêng cho từng kiểu lọc.

Điểm tốt nhất của endpoint này là header `Link` cho phân trang. Client có thể dựa vào các quan hệ như `next`, `prev`, `first`, `last` để đi qua danh sách kết quả, thay vì tự đoán URL tiếp theo. Đây là một phần gần với HATEOAS trong REST.

Kết luận: RESTful tốt, đặc biệt ở phần pagination.

## 5. `DELETE /repos/{owner}/{repo}`

Endpoint này dùng để xoá repository.

| Mục | Nhận xét |
|---|---|
| Method | `DELETE` |
| Ví dụ | `DELETE https://api.github.com/repos/{owner}/{repo}` |
| Thành công | `204 No Content` |
| Lỗi thường gặp | `403 Forbidden`, `404 Not Found` |
| Body trả về | Không có body khi xoá thành công |
| Auth | Bắt buộc, cần quyền phù hợp với repository |

Đánh giá: dùng `DELETE` cho thao tác xoá là đúng. Khi thành công, `204 No Content` cũng hợp lý vì server đã xử lý xong và không cần trả thêm nội dung. Endpoint vẫn dùng URI của resource cần xoá, không dùng đường dẫn kiểu `/delete`.

Về idempotent, sau lần xoá đầu tiên thì trạng thái resource đã là "không còn tồn tại". Nếu gọi lại có thể nhận `404`, nhưng trạng thái cuối cùng của server vẫn không thay đổi thêm. Vì vậy có thể xem là phù hợp với tinh thần idempotent của `DELETE`.

Kết luận: thiết kế endpoint rõ ràng và đúng convention REST.

## Tổng kết

| Endpoint | Đánh giá ngắn |
|---|---|
| `GET /repos/{owner}/{repo}` | Dùng resource URI rõ, có cache bằng `ETag` |
| `POST /user/repos` | Tạo resource đúng bằng `POST`, trả `201 Created` |
| `PATCH /repos/{owner}/{repo}` | Phù hợp cho cập nhật một phần |
| `GET /repos/{owner}/{repo}/issues` | Có filter, pagination và `Link` header |
| `DELETE /repos/{owner}/{repo}` | Dùng `DELETE`, trả `204 No Content` khi thành công |

Nhìn chung, GitHub REST API tuân thủ khá tốt các nguyên tắc REST cơ bản: dùng resource URI, tận dụng HTTP method, trả status code có ý nghĩa và không phụ thuộc vào session phía server. API đạt tốt ở mức dùng resource + HTTP verb. Một số endpoint danh sách còn có `Link` header cho phân trang, nhưng không phải mọi endpoint đều thể hiện HATEOAS đầy đủ, nên mình sẽ không xem GitHub REST API là Level 3 hoàn toàn theo Richardson Maturity Model.

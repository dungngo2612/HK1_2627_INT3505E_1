# Buổi 6 - Authentication và Authorization

Bài nộp gồm [`openapi.yaml`](openapi.yaml) cho ba endpoint và
[`SecurityAudit.md`](SecurityAudit.md) với 13 điểm có thể lộ dữ liệu hoặc quyền
truy cập, kèm cách phòng tránh và kịch bản kiểm tra. Tài liệu viết cho một API
social-network giả định; chưa triển khai backend trong bài này.

## Scope, lỗi và status code

| Endpoint | Credential / scope bắt buộc | Thành công | Lỗi |
| --- | --- | --- | --- |
| `POST /auth/login` | JSON email/password; không cần scope hoặc token có sẵn | `200`: cặp access/refresh JWT | `400 invalid_request`; `401 invalid_credentials`; `413 payload_too_large`; `415 unsupported_media_type`; `429 rate_limit_exceeded`; `500 internal_error`; `503 service_unavailable` |
| `POST /auth/refresh` | Refresh JWT qua Bearer; không cần scope ứng dụng | `200`: cặp token mới, refresh cũ vô hiệu | `400 invalid_request`; `401 authentication_required/invalid_token`; `429 rate_limit_exceeded`; `500 internal_error`; `503 service_unavailable` |
| `GET /posts/{id}` | Access JWT qua Bearer và `posts:read`, sau đó kiểm quyền xem bài | `200`: bài viết được phép xem | `400 invalid_request`; `401 authentication_required/invalid_token`; `403 insufficient_scope`; `404 post_not_found`; `429 rate_limit_exceeded`; `500 internal_error`; `503 service_unavailable` |

`401` của Bearer có `WWW-Authenticate`; `403` ghi rõ scope cần có. Bài không tồn
tại và bài không được xem cùng trả `404` để giảm lộ thông tin. Không dùng refresh
token để gọi GET hoặc access token để gọi refresh.

## Quyết định thiết kế

- OpenAPI **3.1.1**, đúng ba operation; request/response schema, lỗi JSON và ví dụ
  được khai báo trong spec. Tên miền `.example` và mọi token/password ví dụ là giả.
- Dùng JWT của ứng dụng chính chủ theo bài học. HTTP Bearer được khai báo trong
  `components.securitySchemes`; scope ứng dụng nằm ở `x-scopes`,
  `x-required-scopes` và claim `scopes`. Extension là yêu cầu triển khai, công cụ
  OpenAPI thông thường không tự kiểm scope. Không thêm OAuth2 Password grant để
  mô tả một login JSON riêng.
- Access sống tối đa **900 giây**. Phiên sống tối đa **2.592.000 giây (30 ngày)**
  từ lúc login; refresh rotation không đẩy lùi hạn này. Scope refresh không được
  vượt grant ban đầu hoặc quyền hiện tại; server kiểm thu hồi user/sid/jti.
- Mọi bài đều cần access token và `posts:read`. Owner xem bài của mình; người khác
  xem public nếu không bị chặn, hoặc friends khi đủ quan hệ hai chiều và không
  bị chặn. Bài private chỉ dành cho owner. Không có ngoại lệ admin tự động.
- Mọi response có `Cache-Control: no-store` và request ID; token thêm
  `Pragma: no-cache`; `429` và `503` có `Retry-After`. Không đưa secret vào log.

## Xem và kiểm tra spec

Mở file bằng Swagger Editor hoặc công cụ hỗ trợ OpenAPI 3.1. Với Swagger UI,
dùng nút Authorize để nhập access hoặc refresh token vào đúng scheme.

Kiểm tra từ thư mục gốc repository bằng môi trường Python riêng:

```sh
python3 -m venv /tmp/soa-b6-openapi-venv
/tmp/soa-b6-openapi-venv/bin/python -m pip install 'openapi-spec-validator==0.9.0'
/tmp/soa-b6-openapi-venv/bin/openapi-spec-validator week6/openapi.yaml
git diff --check
```

Validator kiểm cấu trúc OpenAPI và các tham chiếu. Kịch bản bảo mật trong audit
chỉ có thể xác nhận khi backend đã triển khai; spec không chứng minh runtime an toàn.

Kết quả kiểm tra bài nộp với Python 3.12 và validator 0.9.0: spec hợp lệ;
109 tham chiếu giải quyết được; 42 ví dụ (tính cả component được tái sử dụng)
khớp schema; 9 payload sai như thêm `is_admin`, thiếu password, lộ trường ngoài
DTO hoặc TTL vượt giới hạn bị schema từ chối. Đây là kiểm tra hợp đồng, không phải
kiểm thử JWT hoặc phân quyền của backend.

Thiết kế tham chiếu [OpenAPI 3.1.1](https://spec.openapis.org/oas/v3.1.1.html),
[RFC 6750](https://www.rfc-editor.org/rfc/rfc6750.html) và nguyên tắc bảo vệ refresh
trong [RFC 9700](https://www.rfc-editor.org/rfc/rfc9700.html#section-4.14).

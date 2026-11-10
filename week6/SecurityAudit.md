# Security Audit - Social Network API (Buổi 6)

Phạm vi: `POST /auth/login`, `POST /auth/refresh`, `GET /posts/{id}` trong
[`openapi.yaml`](openapi.yaml). Đây là rà soát rủi ro của thiết kế, chưa phải
kết quả kiểm thử một backend đang chạy. Các biện pháp dưới đây là yêu cầu khi
triển khai; khai báo OpenAPI không tự tạo middleware bảo mật.

## Các điểm có thể lộ dữ liệu hoặc quyền truy cập

| # | Điểm có thể lộ | Tình huống và hậu quả | Biện pháp cần triển khai | Cách kiểm tra khi có backend |
| --- | --- | --- | --- | --- |
| 1 | Password/token trong đường truyền, URL và log | HTTP, query token, proxy/APM hoặc log body login làm lộ credential và cho phép chiếm phiên. | HTTPS; chỉ nhận token qua `Authorization`; lọc header/body nhạy cảm ở app, gateway và APM; giới hạn quyền đọc và thời gian lưu log. | Dùng credential giả có dấu nhận biết, gọi API rồi kiểm log app/proxy/APM không chứa password, access hoặc refresh token; token trong query không được dùng để xác thực. |
| 2 | Khóa ký trong Git hoặc cấu hình | Khóa HS256 bị commit hoặc dùng khóa yếu khiến người có khóa tạo JWT giả. | Khóa ngẫu nhiên tối thiểu 256 bit từ secret manager/env; secret scan trước commit; không đưa khóa thật vào example; khi lộ phải thay khóa, ngừng tin khóa cũ và thu hồi phiên bị ảnh hưởng. | Quét cả lịch sử Git trước phát hành; xác nhận JWT ký bằng khóa đã thu hồi bị từ chối `401`. Không dán token thật lên công cụ decode online. |
| 3 | Payload JWT chứa PII hoặc secret | JWT được ký vẫn đọc được payload; nhét email, password, password hash hoặc dữ liệu riêng tư vào claim làm tăng phạm vi rò rỉ. | Chỉ giữ claims cần thiết như `sub`, `sid`, `jti`, thời hạn, issuer/audience, type và scopes; không coi chữ ký là mã hóa. | Decode token thử nghiệm cục bộ; xác nhận không có password/hash/email/khóa ký hay dữ liệu bài private. |
| 4 | Nhận token giả hoặc sai dịch vụ | Chấp nhận `alg=none`, lẫn HS/RS, thiếu kiểm `iss`/`aud`/`exp`/`nbf` hoặc sai kiểu claim có thể bỏ qua xác thực. | Cố định allowlist HS256 và khóa tin cậy; thư viện JWT xác minh chữ ký và toàn bộ profile đã khai báo; kiểm `type=access` hoặc `type=refresh` đúng endpoint. | Token sai chữ ký, sai issuer/audience, hết hạn, `nbf` trong tương lai, thiếu claim hoặc đổi `type` phải bị `401`; không dùng trường `alg` để tự chọn thuật toán. |
| 5 | Dò tài khoản và mật khẩu qua login | Lỗi “email không tồn tại”, khác biệt thời gian lớn hoặc thiếu rate-limit giúp enumeration và credential stuffing. | Cùng `401 invalid_credentials` và thông điệp cho email lạ/sai password/user bị vô hiệu; dummy Argon2id verify khi user không tồn tại; limiter theo IP và tài khoản, không khóa vĩnh viễn. | So sánh status/body và phân bố thời gian của ba tình huống; vượt hạn trả `429` và `Retry-After`; log không chứa email đầy đủ nếu không cần thiết. |
| 6 | Password trong DB/backup | Lưu plaintext, mã hóa có thể đảo ngược hoặc hash nhanh khiến mật khẩu bị khôi phục nhanh khi DB lộ. | Argon2id với salt riêng; chọn cost theo tải, rehash khi tăng tham số; bảo vệ DB/backup và quyền đọc; truy vấn có tham số. | Hai tài khoản cùng mật khẩu có hash khác nhau; DB/backup không có plaintext; xác minh mật khẩu qua thư viện, không tự viết crypto. |
| 7 | Refresh token bị sao chép và replay | Token dài hạn bị trộm có thể tạo access mới; hai request refresh đồng thời có thể cùng thành công nếu rotation không atomic. | Lưu hash refresh và metadata phiên; rotate trong transaction/CAS; giữ lịch sử jti đến hết phiên; dùng lại token cũ thu hồi toàn bộ sid/family, kể cả access; phiên hết hạn tuyệt đối sau 30 ngày. | Refresh lần đầu `200`; dùng lại token cũ `401`; token con và access cùng sid sau đó `401`. Với hai request đồng thời cùng token, tối đa một request được `200`; phiên bị thu hồi khi phát hiện reuse. |
| 8 | Quyền cũ hoặc tự nâng scope | Tin `scopes` do client gửi hoặc sao chép quyền cũ khi refresh khiến user giữ quyền đã bị gỡ. | Login từ chối trường lạ; server nạp quyền từ DB; scope mới là giao của grant ban đầu và quyền hiện tại; kiểm trạng thái user/sid mỗi request; thu hồi phiên liên quan khi giảm quyền để access cũ cũng mất hiệu lực. | Gửi `scopes`/`is_admin` vào login trả `400`; gỡ quyền và thu hồi sid thì access cũ `401`; phiên mới không có `posts:read` nhận `403` tại GET. |
| 9 | Bài private của người khác (BOLA/IDOR) | Chỉ kiểm “đã login” hoặc `posts:read` rồi tra bài theo ID cho phép user A đọc bài của B. | Sau AuthN và scope, kiểm owner, visibility, bạn bè hai chiều và block trên mọi GET; không mặc định admin được bỏ qua; UUID chỉ giảm đoán ID. | A có `posts:read` đọc private của B nhận `404`; owner nhận `200`; friends chỉ `200` khi đủ quan hệ và không bị chặn; bài public của người chặn A vẫn `404`. |
| 10 | Lộ sự tồn tại của tài khoản/bài viết và chi tiết hệ thống | Trả lỗi khác nhau cho bài không tồn tại/bài bị cấm hoặc trả stack trace/SQL giúp dò dữ liệu và cấu trúc hạ tầng. | Cùng `404 post_not_found` cho bài không tồn tại/đã xóa/không được xem; `403` chỉ dành cho thiếu scope trước tra cứu bài; lỗi hệ thống trả chung và request ID. | So sánh 404 của ID ngẫu nhiên và bài private; ngoài request ID, body giống nhau. Gây lỗi DB phải không thấy SQL, tên bảng, đường dẫn nội bộ hoặc token trong response. |
| 11 | Response hoặc cache lộ trường riêng tư | Serialize nguyên DB row lộ `password_hash`, email, moderation flags; cache chung trả bài/token của A cho B. | DTO allowlist đúng schema `Post`; `additionalProperties: false`; mọi response `Cache-Control: no-store`, token thêm `Pragma: no-cache`; không để CDN ghi đè chính sách. | Response Post chỉ có sáu trường đã khai báo; truy cập bằng hai user qua cùng proxy không dùng lại nội dung; kiểm header trên cả thành công và lỗi. |
| 12 | Token trong trình duyệt và nội dung bài viết | XSS đọc token trong localStorage/sessionStorage hoặc nội dung bài chèn HTML; refresh bị lộ kéo dài chiếm phiên. | Client chính chủ giữ access trong bộ nhớ; mobile dùng secure storage. Web cân nhắc BFF giữ token phía server, cookie phiên `HttpOnly; Secure; SameSite` phù hợp và chống CSRF; escape nội dung bài, CSP và CORS allowlist. | Nội dung thử `<script>` hiển thị như văn bản; kiểm nơi lưu token và cấu hình CORS. Với BFF, JS không đọc cookie phiên và request thiếu CSRF token bị chặn. Giao diện hiện tại chỉ nhận Bearer, không tự xác thực bằng cookie. |
| 13 | Bỏ qua bảo mật khi hạ tầng lỗi | Khi Redis/kho phiên hỏng mà vẫn cho qua, token đã logout hoặc bị thu hồi lại truy cập được. | Fail-closed; không kiểm được user/sid/jti hoặc quyền thì `503 service_unavailable`, không trả dữ liệu; theo dõi lỗi bằng request ID đã lọc secret. | Ngắt kho phiên/thu hồi rồi gọi refresh và GET bằng token từng hợp lệ: đều `503`, không nhận token mới hoặc bài viết. |

## Các quyết định áp dụng trong hợp đồng

- **Không cần scope không có nghĩa là không cần credential:** login xác minh
  email/password; refresh xác minh refresh JWT. Chỉ GET yêu cầu `posts:read`.
- **401 / 403 / 404:** 401 khi xác thực thất bại; 403 khi access token hợp lệ
  nhưng thiếu scope; 404 khi bài không tồn tại hoặc không được xem theo object policy.
- **JWT ngoài OAuth2:** cơ chế login JSON và refresh Bearer ở đây là giao diện
  riêng của ứng dụng chính chủ; không khai báo OAuth2 Password grant. Nếu bổ sung
  ủy quyền cho ứng dụng bên thứ ba, thiết kế Authorization Code + PKCE riêng.
- **Giới hạn thu hồi:** access TTL tối đa 15 phút giảm thời gian bị lợi dụng,
  nhưng thu hồi tức thì vẫn cần kiểm sid/jti trên server. Khi logout, đổi mật khẩu,
  phát hiện reuse hoặc giảm quyền, phải thu hồi các phiên phù hợp; các route quản
  lý này nằm ngoài ba endpoint của bài.
- **Rate-limit:** login theo IP và tài khoản; refresh theo IP và phiên đã xác minh;
  GET theo IP và principal. Chỉ tin header IP từ proxy đã cấu hình tin cậy.

## Tài liệu đối chiếu

- Slide Buổi 6: trang 14-18 (JWT), 24-26 (scope và object policy), 27-29
  (password và rủi ro auth), 30 (đề bài).
- [OpenAPI 3.1.1 - Security Requirement và Specification Extensions](https://spec.openapis.org/oas/v3.1.1.html#security-requirement-object):
  mô tả Bearer bằng security scheme; scope ứng dụng được ghi bằng extension
  `x-required-scopes` và cần middleware thực thi.
- [RFC 6750, mục 3.1](https://www.rfc-editor.org/rfc/rfc6750.html#section-3.1):
  đối chiếu lỗi Bearer `invalid_token`/401 và `insufficient_scope`/403 của resource API.
- [RFC 9700, mục 4.14](https://www.rfc-editor.org/rfc/rfc9700.html#section-4.14):
  tham khảo bảo vệ refresh token, rotation và phát hiện replay; hợp đồng JWT riêng
  áp dụng các nguyên tắc này, không tuyên bố tuân thủ toàn bộ OAuth2.

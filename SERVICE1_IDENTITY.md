# Service 1 — Identity + Tester

## Phạm vi bàn giao

Backend Django REST Framework; Flutter dùng Provider; JWT do Identity cấp.
Giữ cấu trúc dự án hiện tại, không tách thêm server trong phần việc này.
Các service khác xác thực bằng JWTAuthentication và đọc role từ tài khoản
trong database. Role STAFF khác với cờ is_staff của trang Django Admin.

### Chức năng

- Đăng ký công khai: tạo LANDLORD, kiểm tra xác nhận và độ mạnh mật khẩu.
- Đăng nhập: access token, refresh token và thông tin người dùng.
- Access token 15 phút; refresh token 30 ngày; refresh được xoay và token cũ bị blacklist.
- Flutter tự refresh khi API trả 401, gộp các yêu cầu refresh đồng thời.
- Xem/sửa thông tin cá nhân, không cho tự đổi role/trạng thái tài khoản.
- Đổi mật khẩu yêu cầu mật khẩu cũ; vô hiệu hóa access/refresh cũ bằng kiểm tra hash mật khẩu.
- Đăng xuất blacklist refresh token. Access token đã phát còn hiệu lực tối đa 15 phút;
  việc logout không thu hồi ngay access token đó. Đổi mật khẩu/khóa tài khoản có kiểm tra ở server.
- Admin tạo tài khoản, sửa vai trò, khóa/mở khóa, tìm kiếm/lọc tài khoản.
- Không xóa cứng tài khoản qua REST API để tránh xóa dây chuyền hợp đồng/hóa đơn.
- Không cho Admin tự khóa/hạ quyền chính mình hoặc khóa/đổi role của superuser.
- Rate limit theo IP: login 20 lần/phút, đăng ký 10 lần/giờ (cache mặc định cho local).
- Giao diện: đăng ký, đăng nhập, hồ sơ, đổi mật khẩu, quản lý tài khoản cho Admin.
- Xóa dữ liệu nhà trọ/phòng đang lưu trong Provider khi đổi tài khoản.

## API

Prefix: `/api/v1/`. API yêu cầu đăng nhập nhận header `Authorization: Bearer <access>`.

| Method | URL | Quyền | Nội dung chính |
|---|---|---|---|
| POST | auth/register/ | Công khai | username, password, password_confirm, thông tin liên hệ |
| POST | auth/login/ | Công khai | username, password |
| POST | auth/refresh/ | Refresh token | refresh; trả access và refresh mới |
| POST | auth/logout/ | Refresh token | refresh; thành công 204 |
| GET | auth/me/ | Đã đăng nhập | Hồ sơ hiện tại |
| PATCH | auth/me/ | Đã đăng nhập | first_name, last_name, email, phone_number, identity_card, address, avatar_url |
| POST | auth/change-password/ | Đã đăng nhập | old_password, new_password, password_confirm |
| GET | users/ | ADMIN hoặc superuser | ?role=TENANT&search=... |
| POST | users/ | ADMIN hoặc superuser | username, password, role, thông tin liên hệ |
| GET/PATCH/PUT | users/{id}/ | ADMIN hoặc superuser | role, is_active, thông tin tài khoản; password tùy chọn |

Không gửi is_superuser/is_staff từ giao diện: REST API không cho cấp các cờ Django đó.
Đăng ký không được chọn ADMIN/STAFF/TENANT. Admin tạo tài khoản cho nhân viên/người thuê.
Service Tenant cần quản lý quan hệ người thuê–chủ trọ trước khi mở rộng quyền quản lý khách thuê cho LANDLORD.

## Chạy sau khi áp dụng thay đổi

Dừng backend đang chạy bằng Ctrl+C. Trong PowerShell:

```powershell
cd C:\Users\Admin\nhatro-management\backend
.\venv\Scripts\Activate.ps1
$env:DB_ENGINE = 'sqlite'
python manage.py migrate
python manage.py runserver 127.0.0.1:8000
```

Migrate tạo các bảng blacklist mới. Không xóa database, không chạy lại seed nếu đã có dữ liệu.
Những JWT phát trước khi bật CHECK_REVOKE_TOKEN có thể bị từ chối; đăng nhập lại để nhận token mới.

Terminal frontend:

```powershell
cd C:\Users\Admin\nhatro-management\frontend
flutter pub get
flutter run -d chrome
```

Đăng nhập Admin → Tài khoản → Quản lý tài khoản và phân quyền.
Chủ trọ/người thuê/nhân viên không có nút quản lý tài khoản.

## Chạy kiểm thử

```powershell
cd C:\Users\Admin\nhatro-management\backend
.\venv\Scripts\python.exe manage.py test services.identity_service services.property_service --settings=config.test_settings --verbosity 2
```

`config.test_settings` dùng SQLite trong bộ nhớ, không tác động dữ liệu đang dùng.
MD5PasswordHasher chỉ bật trong cấu hình test để tăng tốc; server thường vẫn dùng cấu hình hash Django mặc định.

```powershell
cd C:\Users\Admin\nhatro-management\frontend
flutter analyze
flutter test
```

## Kế hoạch kiểm thử thủ công

Có thể import `testing/identity.postman_collection.json` vào Postman rồi chạy tuần tự
8 request. Collection tự lưu access/refresh mới, kiểm tra mã HTTP và thử từ chối
token sau logout. Dùng database thử vì request cập nhật số điện thoại mẫu.

| ID | Thao tác | Kết quả mong đợi |
|---|---|---|
| ID-01 | Đăng ký tài khoản mới, mật khẩu mạnh, xác nhận đúng | Tạo chủ trọ; đăng nhập được |
| ID-02 | Đăng ký trùng username | Báo lỗi, không tạo bản ghi |
| ID-03 | Đăng ký mật khẩu yếu / xác nhận sai | Báo lỗi tương ứng |
| ID-04 | Gửi role=ADMIN vào API đăng ký | HTTP 400, không tạo Admin |
| ID-05 | Đăng nhập với từng vai trò | Hiện đúng hồ sơ, quyền tương ứng |
| ID-06 | Đăng nhập sai mật khẩu | HTTP 401, giữ màn hình và hiển thị lỗi |
| ID-07 | Mở lại trình duyệt với token còn dùng được | Xác minh /me; vào ứng dụng |
| ID-08 | Access hết hạn, refresh còn hạn | Refresh rồi gọi lại API; không bắt đăng nhập lại |
| ID-09 | Refresh hết hạn/đã thu hồi | Xóa phiên, trở về đăng nhập |
| ID-10 | Sửa số điện thoại/email/họ tên | Hồ sơ và dữ liệu lưu cục bộ cập nhật |
| ID-11 | Gửi role/is_active/is_superuser trong /auth/me/ | HTTP 400, quyền giữ nguyên |
| ID-12 | Đổi mật khẩu với mật khẩu cũ sai | HTTP 400 |
| ID-13 | Đổi mật khẩu đúng | Về đăng nhập, mật khẩu cũ/token cũ bị từ chối |
| ID-14 | Đăng xuất, thử refresh token vừa dùng | HTTP 401; local đã đăng xuất |
| ID-15 | Admin tạo tài khoản STAFF/TENANT | Đăng nhập tài khoản mới được |
| ID-16 | LANDLORD/STAFF/TENANT gọi /users/ | HTTP 403 |
| ID-17 | Admin đổi vai trò tài khoản khác | Role được kiểm tra theo dữ liệu mới ở server |
| ID-18 | Admin khóa tài khoản đang có token | Đăng nhập và truy cập bằng token cũ bị chặn |
| ID-19 | Admin tự khóa hoặc tự hạ quyền | HTTP 400 |
| ID-20 | Admin tìm username/email/số điện thoại và lọc role | Chỉ trả tài khoản phù hợp |
| ID-21 | Đăng nhập A → xem nhà trọ → đăng xuất → đăng nhập B | Không còn dữ liệu A trong Provider |
| ID-22 | Backend không chạy / mạng ngắt khi đăng nhập | Hiện lỗi, cho thử lại |
| ID-23 | Xem form ở kích thước màn hình nhỏ | Cuộn được, không tràn nội dung |

## Kết quả kiểm tra trong phiên bàn giao

- 41 test backend (36 Identity, 5 Property) đạt với xác thực JWT thật và SQLite trong bộ nhớ.
- Do Windows sandbox từ chối Path.resolve(strict=True) trong migration của thư viện SimpleJWT,
  lần chạy trong phiên sử dụng syncdb cho riêng các model token_blacklist; migrations của dự án
  vẫn chạy. Điều này chưa xác nhận migration của SimpleJWT trong môi trường Windows thông thường.
- Đã thêm 4 test phiên/token HTTP và 2 widget test Flutter. Chưa xác nhận kết quả Flutter:
  Dart/Flutter không mở được snapshot SDK trong sandbox (OS error 5), kể cả bản sao SDK.
- Đây không phải kết quả kiểm thử SQL Server hoặc Android/iOS/Windows Desktop.
- Django WSGI server đã khởi động trên database tạm. Kiểm tra HTTP qua socket bị sandbox
  chặn bằng WinError 10013, nên kết quả 41 test là kiểm thử request qua Django test client,
  không phải kiểm thử trình duyệt hay HTTP trên mạng thật.

## Các lỗi ngoài Service 1 cần nhóm xử lý

Các vấn đề đã tái hiện trước khi triển khai Identity, chưa sửa trong phần việc này:

1. PropertyViewSet/RoomViewSet chỉ yêu cầu IsAuthenticated nên TENANT có thể sửa dữ liệu
   nhà trọ/phòng qua API dù giao diện ẩn nút. Cần phân quyền ở service sở hữu dữ liệu.
2. Chủ trọ có thể tạo phòng với property thuộc chủ khác. Cần kiểm tra quyền sở hữu trong serializer.
3. API phòng nhận giá thuê âm. Cần validation nghiệp vụ.
4. Tenant/Contract/Billing hiện mới có model và status endpoint; chưa thể test luồng thuê trọ đầy đủ.

Tester không nên đánh dấu toàn hệ thống an toàn chỉ vì bộ test Identity đạt.

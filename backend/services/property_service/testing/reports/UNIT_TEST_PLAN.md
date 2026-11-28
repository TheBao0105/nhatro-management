# UNIT TEST PLAN — Sprint 1 / Service 2 (Property & Room)

## 1. Mục tiêu kiểm thử
- Xác minh toàn bộ logic nghiệp vụ và API thuộc phạm vi **Sprint 1** của **Service 2 — Property & Room** (`services.property_service`, cổng `:8002`) hoạt động chính xác theo thiết kế SOA.
- Đảm bảo kiểm tra đầy đủ ở các tầng: **Model**, **Serializer**, **Service / Business Helper**, **REST API / Search & Filter**, và **Authentication / RBAC Security**.
- Phát hiện sớm các lỗ hổng về validation dữ liệu, cô lập dữ liệu giữa các chủ trọ (`owner_id`), rò rỉ dữ liệu cá nhân (`TENANT`), và sai lệch truy vấn trước khi nghiệm thu Sprint 1.
- Đạt độ phủ kiểm thử (**Code Coverage**) tối thiểu **80%** cho phần mã nghiệp vụ thuộc Sprint 1 và tạo minh chứng kiểm thử phục vụ nghiệm thu học phần *Phát triển phần mềm chuyên nghiệp*.

---

## 2. Phân tích phạm vi Sprint 1 (Bảng đối chiếu Source Code)

Qua kiểm tra source code tại `backend/services/property_service/` (`models.py`, `serializers.py`, `views.py`, `urls.py`, `tests.py`), `backend/common/` (`auth.py`, `sprint.py`, `service_client.py`), và `README.md`:

| STT | Chức năng | Source Code thực tế | Phạm vi Sprint 1 | Unit / API Test triển khai |
|---|---|---|---|---|
| 1 | Model `Property` & `Room` (trường dữ liệu, mặc định, `UNIQUE`, FK cascade, `__str__`, bộ đếm phòng, `is_rentable`, `check_rentability()`) | `models.py` (dòng `15`–`224`) | **Thuộc Sprint 1** | `test_models.py` (`S2-MOD-001`..`S2-MOD-043`) |
| 2 | Serialization & Validation `PropertySerializer`, `RoomSerializer` (required, type, capacity `current_occupants <= max_occupants`, read-only `owner_id`, ẩn `PRIVATE_FIELDS` cho `TENANT`) | `serializers.py` (`_viewer_is_manager`, `RoomSerializer`, `PropertySerializer`) | **Thuộc Sprint 1** | `test_serializers.py` (`S2-SER-001`..`S2-SER-044`) |
| 3 | Business Helper & Scope (`_parse_decimal`, `_parse_number`, `_actor_name`, `scoped_properties`, `scoped_rooms`) | `views.py` (dòng `36`–`85`) | **Thuộc Sprint 1** | `test_services.py` (`S2-BIZ-001`..`S2-BIZ-019`) |
| 4 | Quản lý Nhà trọ CRUD, Soft/Hard Delete, `update_status`, `rooms`, `stats`, `room_matrix`, `summary` | `views.py` (`PropertyViewSet`, dòng `113`–`309`) | **Thuộc Sprint 1** | `test_views.py` (`S2-API-001`..`S2-API-029`) |
| 5 | Quản lý Phòng CRUD, Soft/Hard Delete, quản lý trạng thái `/status/`, `/check_rentable/`, `/available/`, `/occupied/`, `/maintenance/`, `/health/` | `views.py` (`RoomViewSet`, dòng `314`–`557`) & `common/health.py` | **Thuộc Sprint 1** | `test_views.py` (`S2-API-030`..`S2-API-063`) |
| 6 | Tìm kiếm, Lọc, Sắp xếp Phòng và Nhà trọ (`search`, `status`, `district`, `ward`, `address`, `floor`, `min/max_price`, `min/max_area`, `max_occupants`, `sort`/`ordering`, `include_deleted`) | `views.py` (`PropertyViewSet.get_queryset`, `RoomViewSet.get_queryset`) | **Thuộc Sprint 1** | `test_search_filter.py` (`S2-FLT-001`..`S2-FLT-040`) |
| 7 | Xác thực JWT Stateless & Phân quyền RBAC (`IsManagerRole`, `IsManagerOrReadOnly`, `ADMIN` / `LANDLORD` / `TENANT` / `STAFF` legacy, fail-closed `503` khi Tenant Service lỗi) | `common/auth.py`, `common/service_client.py`, `config/common.py` | **Thuộc Sprint 1** | `test_permissions.py` (`S2-SEC-001`..`S2-SEC-032`) |
| 8 | Bảo trì & Lịch sử bảo trì (`MaintenanceRequest`, `MaintenanceHistory`, `MaintenanceRequestViewSet`, `MaintenanceHistoryViewSet`) | `models.py` (`229`–`348`), `views.py` (`562`–`855`) | **Ngoài Sprint 1** (ghi bị khóa bởi `SprintFeatureLock` ở `views.py:586-587`; GET vẫn mở ở backend cho module đọc) | Không viết test nghiệp vụ mới trong `unit_tests/`; giữ nguyên 6 test khóa Sprint & luồng bảo trì trong `tests.py` |

> **Lưu ý kiến trúc SOA:** Do Service 2 (`services.property_service`) là app đã có sẵn `tests.py` (`35` test cũ gồm cả `MaintenanceSprintLockTests`), bộ test Sprint 1 mới được đặt trong package tập trung `backend/services/property_service/testing/unit_tests/` để chạy song song mà không che khuất hoặc ghi đè `tests.py`.

---

## 3. Công nghệ & Môi trường kiểm thử

- **Ngôn ngữ & Framework:** Python `3.13.15`, Django `6.1.3`, Django REST Framework (`djangorestframework>=3.18.0`), SimpleJWT (`djangorestframework-simplejwt>=5.5.0`).
- **Công cụ Test & Coverage:** Django `TestCase` / `SimpleTestCase`, DRF `APIClient`, `unittest.mock`, `Coverage.py 7.17.4` (`backend/.coveragerc`, `branch = True`).
- **Cơ sở dữ liệu kiểm thử:** `DB_ENGINE=sqlite` (Django tự tạo SQLite in-memory database cho từng lần chạy test với `DJANGO_SETTINGS_MODULE=config.service_settings.property` và `StatelessServiceRouter`), cô lập hoàn toàn khỏi SQL Server phát triển (`.\SQLEXPRESS` / `nhatro_property_db`).

---

## 4. Phương pháp kiểm thử & Chiến lược cô lập

1. **Nguyên tắc AAA (Arrange – Act – Assert):** Mỗi test case kiểm tra một hành vi rõ ràng, sử dụng dữ liệu tạo riêng qua `setUp` / `setUpTestData` và helper tại `testing/unit_tests/base.py`, không phụ thuộc thứ tự chạy test.
2. **Phân biệt rõ loại test:**
   - **Unit Test thuần (`114` test):** Kiểm tra `Model`, `Serializer`, helper nghiệp vụ (`_parse_decimal`, `_parse_number`, `_actor_name`, `scoped_*`) và lớp permission (`common.auth`) không đi qua tầng HTTP.
   - **API / Integration Test (`103` test):** Gọi qua DRF `APIClient` tới các URL thật của Service 2 (`/api/properties/...`, `/api/rooms/...`, `/health/`), xác minh HTTP Status Code, JSON response và trạng thái lưu trong DB test.
   - **API / Security Test (`24` test):** Kiểm tra JWT hợp lệ, hết hạn, sai định dạng, sai chữ ký, dùng `RefreshToken` làm access token, thiếu `user_id`, ma trận phân quyền `ADMIN`/`LANDLORD`/`TENANT`/`STAFF`.
3. **Cô lập phụ thuộc ngoài Service 2:**
   - **Identity Service (`:8001`):** Tạo JWT AccessToken cục bộ bằng `common.testing.jwt_client` (dùng chung `JWT_SIGNING_KEY`), không gọi mạng sang `:8001`.
   - **Tenant Service (`:8003`):** Dùng `mock.patch('services.property_service.views.own_rented_room_ids', ...)` hoặc `mock.patch('common.service_client.requests.get', ...)` để mô phỏng phòng `TENANT` đang thuê hoặc tình huống Tenant Service trả về `ConnectionError`/JSON lỗi (`503`).
4. **Quy tắc ghi nhận Bug:** Các test case xác nhận lỗi thực tế trong source code không bị xóa hay làm sai assertion mà được đánh dấu `@unittest.expectedFailure` kèm ID bug trong `BUG_REPORT.md` để theo dõi trung thực.

---

## 5. Phạm vi được kiểm thử và Ngoài phạm vi

### Trong phạm vi
- `backend/services/property_service/models.py`: `Property`, `PropertyStatus`, `Room`, `RoomStatus`, `RoomType`, `RENTED_STATUSES` (cùng quan hệ liên kết cơ bản `MaintenanceRequest`).
- `backend/services/property_service/serializers.py`: `PropertySerializer`, `RoomSerializer`, `_viewer_is_manager`.
- `backend/services/property_service/views.py`: `_actor_name`, `_parse_decimal`, `_parse_number`, `scoped_properties`, `scoped_rooms`, `PropertyViewSet`, `RoomViewSet`.
- `backend/services/property_service/urls.py`, `service_urls.py`, `common/auth.py`, `common/health.py`.

### Ngoài phạm vi
- Các service khác: Identity (`:8001`), Tenant (`:8003`), Contract (`:8004`), Billing & Notification (`:8005`), API Gateway (`:8000`).
- Nghiệp vụ ghi Bảo trì / Sửa chữa (`MaintenanceRequestViewSet` write actions — đã khóa tạm bằng `SprintFeatureLock` ở Sprint 1) và Django Admin (`admin.py`).
- Kiểm thử giao diện Flutter Web (thuộc phần kiểm thử E2E Frontend riêng).

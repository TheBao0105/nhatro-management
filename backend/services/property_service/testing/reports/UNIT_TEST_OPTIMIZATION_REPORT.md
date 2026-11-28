# BÁO CÁO TỐI ƯU HÓA BỘ UNIT TEST — SERVICE 2 (PROPERTY & ROOM)

> Tài liệu này ghi nhận toàn bộ quá trình phân tích, phân tách cấp độ kiểm thử (**Pure Unit Test** vs **API / HTTP Test**), gộp các test vụn bằng kỹ thuật parameterized (`subTest`) và kết quả kiểm chứng thực tế của **Service 2 — Property & Room** (`backend/services/property_service/testing/`).

---

## 1. Tổng quan Số lượng Trước & Sau Tối ưu

| Chỉ số | Ban đầu (Chưa dọn Legacy) | Sau Phương án A (Đã bỏ 29 Legacy trùng) | **Sau Tối ưu (Hiện tại)** | Ghi chú & Đánh giá |
|---|---:|---:|---:|---|
| **1. Pure Unit Tests (`testing/unit_tests/`)** | `126` | `126` | **`72`** | Nằm gọn trong khung mục tiêu **`70–90` Unit Tests chất lượng cao** (`0.28s`) |
| **2. API / HTTP Tests (`testing/api_tests/`)** | `129` (+ `35` `tests.py`) | `135` | **`135`** | Tách riêng 100% vào `testing/api_tests/`, không trộn lẫn với Unit Test (`1.18s`) |
| **TỔNG SỐ TEST TOÀN SERVICE 2** | `290` | `261` | **`207`** | Giảm `83` test trùng/vụn (`-28.6%`), thời gian chạy chỉ còn `1.39s` |
| **Thuộc phạm vi Sprint 1 (Property & Room)** | `242` | `244` | **`188`** | **`59` Pure Unit Tests + `129` API/HTTP Tests** |
| **Ngoài phạm vi Sprint 1 (Maintenance)** | `13` (+ `6` `tests.py`) | `17` | **`19`** | **`13` Pure Unit Tests + `6` API/HTTP Tests** (đánh dấu rõ `[Ngoài Sprint 1]`) |
| **Tỷ lệ PASS / FAIL / ERROR** | `290 / 0 / 0` | `261 / 0 / 0` | **`207 / 0 / 0`** | **100% PASS** |
| **Statement Coverage (`759` stmts)** | `100%` (`0` miss) | `100%` (`0` miss) | **`100%` (`0` miss)** | Không mất bất kỳ dòng code nào |
| **Branch Coverage (`210` branches)** | `100%` (`0` part) | `100%` (`0` part) | **`100%` (`0` part)** | Không mất bất kỳ nhánh điều kiện nào |

---

## 2. Phân bổ 72 Pure Unit Tests so với Khung Mục Tiêu

| Module (Pure Unit Test) | File thực tế trong `testing/unit_tests/` | Khung mục tiêu | Số lượng trước tối ưu | **Số lượng sau tối ưu** | Mã Test Case | Phạm vi (Sprint 1 / Ngoài Sprint 1) |
|---|---|---:|---:|---:|---|---|
| **1. Models** | [test_models.py](file:///c:/Users/Asus/.gemini/antigravity/scratch/nhatro_management/backend/services/property_service/testing/unit_tests/test_models.py) | `12–15` | `46` | **`15`** | `S2-MOD-001`..`015` | `13` Sprint 1 + `2` Ngoài Sprint 1 (`014`..`015`) |
| **2. Serializers** | [test_serializers.py](file:///c:/Users/Asus/.gemini/antigravity/scratch/nhatro_management/backend/services/property_service/testing/unit_tests/test_serializers.py) | `15–20` | `44` | **`18`** | `S2-SER-001`..`018` | `18` Sprint 1 |
| **3. Services / Business Logic** | [test_services.py](file:///c:/Users/Asus/.gemini/antigravity/scratch/nhatro_management/backend/services/property_service/testing/unit_tests/test_services.py) (`ScopedQuerysetTests`, `MaintenanceViewSetUnitTests`) | `20–25` | `19` | **`21`** | `S2-BIZ-001`..`021` | `10` Sprint 1 + `11` Ngoài Sprint 1 (`011`..`021`) |
| **4. Permissions (Unit)** | [test_permissions.py](file:///c:/Users/Asus/.gemini/antigravity/scratch/nhatro_management/backend/services/property_service/testing/unit_tests/test_permissions.py) (`PermissionClassUnitTests`) | `10–15` | `8` | **`11`** | `S2-PERM-001`..`011` | `11` Sprint 1 |
| **5. Validators / Utilities** | [test_services.py](file:///c:/Users/Asus/.gemini/antigravity/scratch/nhatro_management/backend/services/property_service/testing/unit_tests/test_services.py) (`ParseHelperTests`, `ActorNameTests`) | `5–10` | `9` | **`7`** | `S2-UTL-001`..`007` | `7` Sprint 1 |
| **TỔNG PURE UNIT TESTS** | **`4` files trong `testing/unit_tests/`** | **`70–90`** | **`126`** | **`72`** | **`72` Pure Unit Tests** | **`59` Sprint 1 + `13` Ngoài Sprint 1** |

---

## 3. Phân tách rõ Pure Unit Tests và API / HTTP Tests

Trước khi tối ưu, các file `test_views.py`, `test_search_filter.py` và 26 test HTTP trong `test_permissions.py` đều nằm chung trong thư mục `testing/unit_tests/` dù thực chất là **API / HTTP Tests** (gọi qua DRF `APIClient` + HTTP routing + database).

Sau khi tối ưu, cấu trúc được phân tách rành mạch theo đúng bản chất kỹ thuật:

1. **`testing/unit_tests/` (`72` Pure Unit Tests — chạy trực tiếp Python / ORM / Serializer / ViewSet method / Permission class, hoàn toàn không qua HTTP):**
   - [unit_tests/test_models.py](file:///c:/Users/Asus/.gemini/antigravity/scratch/nhatro_management/backend/services/property_service/testing/unit_tests/test_models.py): **`15`** tests (`S2-MOD-001`..`015`)
   - [unit_tests/test_serializers.py](file:///c:/Users/Asus/.gemini/antigravity/scratch/nhatro_management/backend/services/property_service/testing/unit_tests/test_serializers.py): **`18`** tests (`S2-SER-001`..`018`)
   - [unit_tests/test_services.py](file:///c:/Users/Asus/.gemini/antigravity/scratch/nhatro_management/backend/services/property_service/testing/unit_tests/test_services.py): **`28`** tests (`7` Utilities `S2-UTL-001`..`007` + `21` Business/Service `S2-BIZ-001`..`021`)
   - [unit_tests/test_permissions.py](file:///c:/Users/Asus/.gemini/antigravity/scratch/nhatro_management/backend/services/property_service/testing/unit_tests/test_permissions.py): **`11`** tests (`S2-PERM-001`..`011`)
2. **`testing/api_tests/` (`135` API / HTTP Tests — giữ nguyên 100%, không chuyển thành Unit Test, không xóa bất kỳ kịch bản API nào):**
   - [api_tests/test_views.py](file:///c:/Users/Asus/.gemini/antigravity/scratch/nhatro_management/backend/services/property_service/testing/api_tests/test_views.py): **`63`** tests (`S2-API-001`..`063` — Sprint 1)
   - [api_tests/test_search_filter.py](file:///c:/Users/Asus/.gemini/antigravity/scratch/nhatro_management/backend/services/property_service/testing/api_tests/test_search_filter.py): **`42`** tests (`S2-FLT-001`..`040` Sprint 1 + `S2-FLT-041`..`042` Ngoài Sprint 1)
   - [api_tests/test_permissions_api.py](file:///c:/Users/Asus/.gemini/antigravity/scratch/nhatro_management/backend/services/property_service/testing/api_tests/test_permissions_api.py): **`26`** tests (`S2-SEC-009`..`034` — Sprint 1)
   - [api_tests/test_maintenance_api.py](file:///c:/Users/Asus/.gemini/antigravity/scratch/nhatro_management/backend/services/property_service/testing/api_tests/test_maintenance_api.py): **`4`** tests (`S2-MAPI-001`..`004` — Ngoài Sprint 1)

---

## 4. Danh sách Test Đã Loại Bỏ (`29` Legacy Tests trùng lặp hoàn toàn)

Toàn bộ **29 Legacy tests** trong `backend/services/property_service/tests.py` trùng 100% mục tiêu, vai trò và assertion với bộ test chuẩn đã được loại bỏ (bảng ánh xạ chi tiết từng test xem tại [LEGACY_TEST_MIGRATION.md](file:///c:/Users/Asus/.gemini/antigravity/scratch/nhatro_management/backend/services/property_service/testing/reports/LEGACY_TEST_MIGRATION.md)):
- **`PropertyServiceTests` (`19` test bị loại):** `S2-LEG-001`..`017`, `S2-LEG-022`..`024` (đã được thay thế hoàn toàn bởi `S2-API-001`..`062` và `S2-FLT-001`..`042`).
- **`PropertyRoleScopeTests` (`7` test bị loại):** `S2-LEG-025`..`028`, `S2-LEG-030`..`032` (đã được thay thế hoàn toàn bởi `S2-SEC-019`..`032`).
- **`MaintenanceSprintLockTests` (`2` test bị loại):** `S2-LEG-034`, `S2-LEG-035` (đã được thay thế bởi `S2-FLT-041`..`042` và `S2-API-053`).
- *(Lưu ý: Không có bất kỳ test nghiệp vụ có giá trị nào trong `unit_tests/` hay `api_tests/` bị xóa bỏ; việc giảm từ `126` xuống `72` Pure Unit Tests hoàn toàn thông qua **gộp parameterized `subTest`**).*

---

## 5. Danh sách Test Được Gộp / Tái Cấu Trúc Trong `testing/unit_tests/` (`126` → `72` Pure Unit Tests)

### 5.1. Module Models (`test_models.py`: từ `46` tests gộp thành `15` tests)

| Mã mới | Các mã cũ được gộp | Nội dung gộp & Cơ chế bảo toàn assertion |
|---|---|---|
| **`S2-MOD-001`** | `S2-MOD-001`, `007`, `008`, `009`, `014` | Gộp kiểm tra khởi tạo `Property` mặc định, enum `PropertyStatus`, `__str__`, `full_address` (bỏ `ward=''`) và `area_location`. |
| **`S2-MOD-002`** | `S2-MOD-002`, `003`, `004` | Gộp chuỗi tự sinh mã `Property.code` (`NT001` → `NT002`) và nhảy qua mã đã tồn tại (`NT004` → `NT005`). |
| **`S2-MOD-003`** | `S2-MOD-005`, `006` | Gộp giữ nguyên `code='ABC-1'` truyền sẵn và kiểm tra ràng buộc `UNIQUE` (`IntegrityError`). |
| **`S2-MOD-004`** | `S2-MOD-010`, `011`, `012`, `013` | Dùng `subTest` kiểm tra `Property.full_clean()` cho `name=''`, `address=''`, `status='BOGUS'` và biên độ dài `name` (`150` hợp lệ, `151` lỗi). |
| **`S2-MOD-005`** | `S2-MOD-015`, `016`, `018` | Kiểm tra bộ đếm phòng khi nhà chưa có phòng (`0, 0, 0`) và khi có đủ 6 trạng thái phòng + `active_rooms_qs` loại trừ `INACTIVE`. |
| **`S2-MOD-006`** | `S2-MOD-017` | Giữ nguyên test độc lập cho `FK CASCADE` khi xóa `Property` có phòng. |
| **`S2-MOD-007`** | `S2-MOD-019`, `024`, `027`, `028`, `029` | Gộp khởi tạo `Room` mặc định, `__str__`, enum `RoomStatus`/`RoomType`/`RENTED_STATUSES` và thứ tự mặc định `(property, floor, room_number)`. |
| **`S2-MOD-008`** | `S2-MOD-020`, `021`, `022` | Gộp tự sinh mã `Room.code` (`NT001-101`), chuẩn hóa ký tự đặc biệt (`a-01 vip` → `NT001-A01VIP`) và hậu tố chống trùng (`NT001-101-2`). |
| **`S2-MOD-009`** | `S2-MOD-023`, `025`, `026` | Gộp giữ `code='X1'` truyền sẵn, `UNIQUE` `code` và bắt buộc `FK property`. |
| **`S2-MOD-010`** | `S2-MOD-030`..`037` *(8 tests)* | Dùng `subTest` kiểm tra toàn bộ `Room.full_clean()`: `status='BOGUS'`, `max_occupants=-1/0` (`BUG-04`), `current_occupants=-1`, `rent_price` 12 vs 13 chữ số, `rent_price=-1` (`BUG-01`), `area=-5/0` (`BUG-02`), `room_number` 60 vs 61 ký tự và rỗng. |
| **`S2-MOD-011`** | `S2-MOD-038` | Giữ nguyên test độc lập cho `is_rentable=True` khi phòng `AVAILABLE` trong nhà `ACTIVE`. |
| **`S2-MOD-012`** | `S2-MOD-040` | Giữ nguyên test độc lập khi nhà trọ `INACTIVE` khiến phòng `AVAILABLE` không thể cho thuê. |
| **`S2-MOD-013`** | `S2-MOD-039`, `041`, `042`, `044` | Gộp kiểm tra `check_rentability()` cho `OCCUPIED` (`1/3`, `còn 2`), `FULL`, `RESERVED`, `MAINTENANCE`, `INACTIVE` và nhánh fallback `UNKNOWN_STATE`. |
| **`S2-MOD-014`** | `S2-MOD-043`, `045` *(Ngoài Sprint 1)* | Gộp quan hệ `room.maintenance_requests`, `is_open=True`, giữ mã `BT0002` và tự tăng lên `BT0003` khi trùng mã. |
| **`S2-MOD-015`** | `S2-MOD-046` *(Ngoài Sprint 1)* | Giữ nguyên kiểm tra `__str__` của `MaintenanceRequest` và `MaintenanceHistory`. |

### 5.2. Module Serializers (`test_serializers.py`: từ `44` tests gộp thành `18` tests)

| Mã mới | Các mã cũ được gộp | Nội dung gộp & Cơ chế bảo toàn assertion |
|---|---|---|
| **`S2-SER-001`** | `S2-SER-001`, `003` | Tạo `Property` qua serializer gán `owner_id` từ `request.user` và bỏ qua `owner_id=999` trong payload. |
| **`S2-SER-002`** | `S2-SER-002` | Tạo `Property` khi không có `request` trong context dùng `owner_id=1` mặc định. |
| **`S2-SER-003`** | `S2-SER-004`, `005`, `006`, `007` | Kiểm tra payload rỗng `{}`, thiếu `name`, thiếu `address`, và `name` rỗng/chỉ chứa khoảng trắng. |
| **`S2-SER-004`** | `S2-SER-008`, `009` | Dùng `subTest` kiểm tra cả 3 `PropertyStatus` hợp lệ và từ chối `status='BOGUS'`. |
| **`S2-SER-005`** | `S2-SER-010`, `011`, `012` | Dùng `subTest` kiểm tra `total_floors='abc'/-1` và cả 3 đơn giá dịch vụ âm (`electricity_rate`, `water_rate`, `internet_rate` = `-1` — `BUG-03`). |
| **`S2-SER-006`** | `S2-SER-013`, `014` | Kiểm tra trùng `Property.code` và `image_url='not-a-url'`. |
| **`S2-SER-007`** | `S2-SER-015` | Kiểm tra dữ liệu đầu ra `PropertySerializer` (`full_address`, `status_display`, bộ đếm phòng, `rooms`). |
| **`S2-SER-008`** | `S2-SER-016`, `017`, `018` | Kiểm tra `partial=True` cập nhật đúng trường, bỏ qua `id`/`created_at`/`rooms` read-only và giữ nguyên `owner_id` khi `ADMIN` sửa. |
| **`S2-SER-009`** | `S2-SER-019`, `038` | Tạo `Room` sinh mã `NT1-101` và bỏ qua các trường read-only (`id`, `is_rentable`, `property_name`). |
| **`S2-SER-010`** | `S2-SER-020`, `021`, `022`, `024` | Kiểm tra payload rỗng `{}`, chuỗi rỗng `''` và `property=999999` / `'abc'`. |
| **`S2-SER-011`** | `S2-SER-023`, `025`..`031` *(8 tests)* | Dùng `subTest` cho 11 trường hợp lỗi kiểu số & biên của `RoomSerializer` (`rent_price='abc'/-1/'3000000.50'/10**12`, `area='abc'/-5/0`, `floor='abc'`, `max_occupants='abc'/-1/0` — `BUG-01`, `BUG-02`, `BUG-04`). |
| **`S2-SER-012`** | `S2-SER-032`, `036`, `037` | Kiểm tra `status`/`room_type='BOGUS'`, trùng `code='DUP-ROOM'` và biên `amenities` (`500` vs `501` ký tự). |
| **`S2-SER-013`** | `S2-SER-033`, `034`, `035` | Kiểm tra quy tắc sức chứa `current_occupants <= max_occupants` khi tạo mới (`2<=2` OK, `3>2` lỗi) và khi `PATCH partial=True` (`5>2` lỗi). |
| **`S2-SER-014`**..**`018`** | `S2-SER-039`..`044` | Giữ nguyên 5 test kiểm tra cấu trúc đầu ra cho `LANDLORD`, ẩn `PRIVATE_FIELDS` cho `TENANT` và khi thiếu `request`, đếm `active_maintenance_count` và serialize `many=True`. |

### 5.3. Module Utilities, Services & Permissions (`test_services.py` & `test_permissions.py`)

- **Validators / Utilities (`7` tests — `S2-UTL-001`..`007`):**
  - Gộp `S2-BIZ-005` + `S2-BIZ-007` thành **`S2-UTL-005`** (`_parse_number` ép kiểu `int`/`float` và biên `0`/`-3`).
  - Gộp `S2-BIZ-008` + `S2-BIZ-009` thành **`S2-UTL-007`** (`_actor_name` cho anonymous và thứ tự ưu tiên `full_name > username > User #id`).
- **Services / Business Logic (`21` tests — `S2-BIZ-001`..`021`):**
  - Giữ nguyên 10 test `scoped_properties`/`scoped_rooms` (`S2-BIZ-001`..`010` — Sprint 1) và 2 test helper bảo trì (`S2-BIZ-011`..`012` — Ngoài Sprint 1).
  - Tách 2 test quá dài trong `MaintenanceViewSetUnitTests` (`S2-BIZ-027` và `S2-BIZ-028` cũ) thành 4 unit test đơn trách nhiệm rõ ràng: **`S2-BIZ-018`** (`record_cost`), **`S2-BIZ-019`** (`complete`), **`S2-BIZ-020`** (`cancel` chặn `TENANT` khác `403`), **`S2-BIZ-021`** (`cancel` cho phép người báo hủy `200`).
- **Permissions Unit (`11` tests — `S2-PERM-001`..`011`):**
  - Giữ nguyên 8 unit test `common.auth` (`S2-PERM-001`..`008`).
  - Bổ sung 3 Pure Unit Tests kiểm tra trực tiếp lớp `SprintFeatureLock` khi bật/tắt (`S2-PERM-009`, `S2-PERM-010`) và helper `_viewer_is_manager` (`S2-PERM-011`).

---

## 6. Kết quả Chạy Kiểm Chứng Thực Tế & Code Coverage

### 6.1. Chạy độc lập từng tầng và toàn bộ Test Suite (`.\backend\services\property_service\testing\run_tests.ps1`)

1. **Chạy riêng Pure Unit Tests (`services.property_service.testing.unit_tests`):**
   ```text
   Ran 72 tests in 0.281s — OK
   [PURE UNIT TESTS ONLY] Total=72, PASS=72, FAIL/ERROR=0, Duration=0.28s
   ```
2. **Chạy riêng API / HTTP Tests (`services.property_service.testing.api_tests`):**
   ```text
   Ran 135 tests in 1.180s — OK
   [API/HTTP TESTS ONLY] Total=135, PASS=135, FAIL/ERROR=0, Duration=1.18s
   ```
3. **Chạy riêng phạm vi Sprint 1 (`--sprint1-only`):**
   ```text
   Ran 188 tests in 1.259s — OK
   [SPRINT 1 ONLY] Total=188, PASS=188, FAIL/ERROR=0, Duration=1.26s
   ```
4. **Chạy toàn bộ Test Suite Service 2 (`207` tests = `72` Pure Unit + `135` API/HTTP) kèm Branch Coverage:**
   ```text
   Ran 207 tests in 2.206s — OK
   Name                                        Stmts   Miss Branch BrPart  Cover   Missing
   ---------------------------------------------------------------------------------------
   services\property_service\models.py           207      0     30      0   100%
   services\property_service\serializers.py       85      0      8      0   100%
   services\property_service\service_urls.py       2      0      0      0   100%
   services\property_service\urls.py               9      0      0      0   100%
   services\property_service\views.py            456      0    172      0   100%
   ---------------------------------------------------------------------------------------
   TOTAL                                         759      0    210      0   100%
   ```

---

## 7. Các Nghiệp Vụ Đã Được Bao Phủ & Đánh Giá Chất Lượng Cuối Cùng

1. **Đầy đủ 100% nghiệp vụ Sprint 1 (`188` tests = `59` Pure Unit + `129` API/HTTP):**
   - **Property:** Khởi tạo mặc định, tự sinh mã `NTxxx` chống trùng, `UNIQUE`, `FK CASCADE`, `full_address`/`area_location`, bộ đếm phòng theo 6 trạng thái, `active_rooms_qs`, validation đơn giá dịch vụ không âm (`BUG-03`), CRUD API, Soft/Hard Delete, chặn xóa nhà có phòng đang thuê, `update_status`, `rooms?status=` (`BUG-05`), `stats`, `room_matrix`, `summary`.
   - **Room:** Tự sinh mã `NTxxx-xxx` chuẩn hóa ký tự & hậu tố chống trùng, validation `rent_price >= 0` (`BUG-01`), `area > 0` (`BUG-02`), `max_occupants >= 1` (`BUG-04`), `current_occupants <= max_occupants`, `is_rentable` & `check_rentability()` trên mọi trạng thái (kể cả fallback), CRUD API, Soft/Hard Delete, quản lý trạng thái `/status/` (tự nâng `OCCUPIED` lên `FULL`, dọn PII khi về `AVAILABLE`), `/check_rentable/`, `/available/`, `/occupied/`, `/maintenance/`, `/health/`.
   - **Search / Filter / Sort:** Tìm kiếm & lọc đa điều kiện không phân biệt hoa thường, biên giá/diện tích, chống rò rỉ tìm kiếm theo `tenant_name` với `TENANT`, xử lý lỗi tham số số học `400`, sắp xếp 8 chiều.
   - **Security / JWT / RBAC:** Xác thực JWT stateless (hết hạn, sai chữ ký, sai định dạng, dùng `RefreshToken` làm access, thiếu `user_id`), cô lập dữ liệu tuyệt đối giữa các `LANDLORD`, ẩn `PRIVATE_FIELDS` và doanh thu với `TENANT`, lọc liên kết `MOVED_OUT`, fail-closed `503` khi Tenant Service lỗi, và ma trận `SprintFeatureLock` chặn toàn bộ 9 write endpoints bảo trì.
2. **Bảo toàn 100% kiểm thử chuẩn bị cho Sprint sau (`19` tests `[Ngoài Sprint 1]` = `13` Pure Unit + `6` API/HTTP):**
   - Kiểm tra đầy đủ model, helper, method nội bộ của `MaintenanceRequestViewSet`, bộ lọc đọc `GET /api/maintenance/` & `/api/maintenance-history/` và luồng HTTP pipeline bảo trì.
3. **Đánh giá chất lượng:**
   - Bộ **72 Pure Unit Tests** chạy chỉ mất **`0.28 giây`**, hoàn toàn độc lập với tầng HTTP, mỗi test có mục tiêu rõ ràng, mật độ assertion cao và dễ bảo trì.
   - Bộ **135 API / HTTP Tests** được tách riêng trong `testing/api_tests/`, kiểm chứng toàn diện giao thức REST, mã trạng thái HTTP, phân quyền và trạng thái cơ sở dữ liệu.
   - Đạt **100% Statement Coverage (`759/759`)** và **100% Branch Coverage (`210/210`)** đã được kiểm chứng thực tế bằng `Coverage.py 7.17.4`.

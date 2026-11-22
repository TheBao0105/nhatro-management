# Hệ Thống Kiểm Thử Service 2 — Property & Room (`services.property_service`)

> Tài liệu hướng dẫn tổng quan và tra cứu kỹ thuật cho toàn bộ hệ thống kiểm thử (**Unit Tests** & **API/HTTP Tests**) của **Service 2 — Property & Room** trong dự án **Hệ thống Quản lý Nhà trọ kiến trúc SOA**, phục vụ Developer, Tester, Scrum Master và Giảng viên khi nghiệm thu **Sprint 1**.

---

## Mục Lục

1. [Giới thiệu](#1-giới-thiệu)
2. [Cấu trúc thư mục](#2-cấu-trúc-thư-mục)
3. [Phân loại kiểm thử (207 Tests = 72 Unit + 135 API)](#3-phân-loại-kiểm-thử-207-tests--72-unit--135-api)
4. [Thống kê theo phạm vi Sprint](#4-thống-kê-theo-phạm-vi-sprint)
5. [Cách chạy kiểm thử](#5-cách-chạy-kiểm-thử)
6. [Coverage Report (100% trên 5 file phạm vi cấu hình)](#6-coverage-report-100-trên-5-file-phạm-vi-cấu-hình)
7. [Phân biệt các loại kiểm thử trong Service 2](#7-phân-biệt-các-loại-kiểm-thử-trong-service-2)
8. [Hệ thống báo cáo & bằng chứng kiểm thử](#8-hệ-thống-báo-cáo--bằng-chứng-kiểm-thử)
9. [Những hạn chế kỹ thuật hiện tại](#9-những-hạn-chế-kỹ-thuật-hiện-tại)
10. [Quy trình khi bổ sung Test Case mới](#10-quy-trình-khi-bổ-sung-test-case-mới)

---

## 1. Giới thiệu

### 1.1. Mục đích của hệ thống kiểm thử Service 2
- Xác minh toàn bộ quy tắc nghiệp vụ, ràng buộc dữ liệu, phân quyền theo vai trò (`ADMIN`, `LANDLORD`, `TENANT`, `STAFF`) và giao thức REST API của **Service 2 — Property & Room** (`services.property_service`, cổng độc lập `:8002`).
- Phát hiện sớm và ngăn ngừa hồi quy (regression) đối với các lỗi dữ liệu biên (như `BUG-01`..`BUG-05`: giá thuê âm, diện tích `<= 0`, đơn giá dịch vụ âm, `max_occupants = 0`, xung đột query param `?status=` khi lọc phòng của nhà trọ).
- Cung cấp bộ bằng chứng kiểm thử tự động, minh bạch (`HTML Report`, `JUnit XML`, `HTML Coverage`, `Execution Log`, `JSON`) để nghiệm thu **Sprint 1** của học phần *Phát triển phần mềm chuyên nghiệp*.

### 1.2. Phạm vi kiểm thử
- **Trong phạm vi Sprint 1 (`188` tests):**
  - Quản lý Nhà trọ (`Property`): khởi tạo, tự sinh mã `NTxxx`, địa chỉ đầy đủ, bộ đếm phòng theo 6 trạng thái, đơn giá điện/nước/internet, CRUD API, xóa cứng/xóa mềm (`DELETED`), chặn xóa khi còn phòng đang thuê, đổi trạng thái, thống kê doanh thu & tỷ lệ lấp đầy (`stats`, `summary`), sơ đồ phòng theo tầng (`room_matrix`).
  - Quản lý Phòng trọ (`Room`): khởi tạo, tự sinh mã `NTxxx-xxx`, kiểm tra điều kiện cho thuê (`is_rentable`, `check_rentability()`), ràng buộc sức chứa (`current_occupants <= max_occupants`), CRUD API, xóa cứng/xóa mềm (`INACTIVE`), chuyển trạng thái phòng (`/status/`), danh sách theo trạng thái (`/available/`, `/occupied/`, `/maintenance/`).
  - Tìm kiếm, lọc đa điều kiện & sắp xếp (`search`, `status`, `district`, `ward`, `address`, `floor`, `min_price`, `max_price`, `min_area`, `max_area`, `max_occupants`, `sort`/`ordering`, `include_deleted`).
  - Xác thực JWT Stateless, cô lập dữ liệu giữa các chủ trọ (`owner_id`), ẩn thông tin cá nhân người thuê (`PRIVATE_FIELDS`) đối với `TENANT`, cơ chế fail-closed `503` khi Tenant Service ngừng hoạt động, và khóa tính năng bảo trì ghi ở Sprint 1 (`SprintFeatureLock`).
- **Ngoài phạm vi Sprint 1 (`19` tests — gắn nhãn `[Ngoài Sprint 1]`):**
  - Kiểm thử cho phần mã nguồn Bảo trì (`MaintenanceRequest`, `MaintenanceHistory`, `MaintenanceRequestViewSet`, `MaintenanceHistoryViewSet`) đã có sẵn trong codebase của Service 2 để chuẩn bị cho Sprint sau mà không mở khóa `SPRINT_FEATURE_LOCK` trên môi trường mặc định.

### 1.3. Công nghệ & Công cụ sử dụng
| Thành phần | Công nghệ / Phiên bản thực tế |
|---|---|
| **Ngôn ngữ & Web Framework** | Python `3.13.15`, Django `6.1.3`, Django REST Framework (`>=3.18.0`), SimpleJWT (`>=5.5.0`) |
| **Test Framework** | `django.test.SimpleTestCase`, `django.test.TestCase`, `rest_framework.test.APIClient`, `unittest.mock` |
| **Test Database** | `DB_ENGINE=sqlite` (SQLite In-Memory test database với `DJANGO_SETTINGS_MODULE=config.service_settings.property`, cô lập hoàn toàn khỏi SQL Server phát triển) |
| **Code Coverage** | `Coverage.py 7.17.4` (`backend/.coveragerc`, bật `branch = True`) |
| **Automation & Reporting** | PowerShell (`run_tests.ps1`) + Python Collector (`tools/collect_results.py` xuất JSON, Markdown, HTML, JUnit XML) |

---

## 2. Cấu trúc thư mục

Toàn bộ hệ thống kiểm thử của Service 2 được tổ chức tập trung bên trong `backend/services/property_service/testing/`:

```text
backend/services/property_service/
├── models.py                             # Model Property, Room, MaintenanceRequest, MaintenanceHistory
├── serializers.py                        # PropertySerializer, RoomSerializer, Maintenance*Serializer
├── views.py                              # Helpers, scoped_*, PropertyViewSet, RoomViewSet, Maintenance*ViewSet
├── urls.py                               # DRF Router URLs (/api/properties/, /api/rooms/, ...)
├── service_urls.py                       # Root URLconf khi chạy độc lập Service 2 (:8002)
├── tests.py                              # File chỉ dẫn docstring trỏ sang gói testing/ (0 test trùng)
└── testing/                              # HỆ THỐNG KIỂM THỬ TẬP TRUNG CỦA SERVICE 2
    ├── __init__.py                       # Giúp Django DiscoverRunner tự động đệ quy phát hiện đủ 207 tests
    ├── README.md                         # Tài liệu hướng dẫn tổng quan hệ thống kiểm thử (file này)
    ├── run_tests.ps1                     # Script PowerShell chạy tự động 6 bước (Unit, API, Coverage, Reports)
    ├── unit_tests/                       # 72 UNIT TESTS (không gọi HTTP API)
    │   ├── __init__.py
    │   ├── base.py                       # Factory/helper dùng chung: make_property, make_room, fake_user, patch_rented_rooms
    │   ├── test_models.py                # 15 tests (S2-MOD-001..015): Model Property, Room, Maintenance*
    │   ├── test_serializers.py           # 18 tests (S2-SER-001..018): PropertySerializer & RoomSerializer
    │   ├── test_services.py              # 28 tests (S2-UTL-001..007 & S2-BIZ-001..021): Utilities, scoped_*, ViewSet methods
    │   └── test_permissions.py           # 11 tests (S2-PERM-001..011): common.auth, SprintFeatureLock, _viewer_is_manager
    ├── api_tests/                        # 135 API / HTTP TESTS (gọi qua DRF APIClient)
    │   ├── __init__.py
    │   ├── test_views.py                 # 63 tests (S2-API-001..063): CRUD, Soft/Hard Delete, Status, Stats, Matrix, Health
    │   ├── test_search_filter.py         # 42 tests (S2-FLT-001..042): Search, Filter, Sort cho Room, Property, Maintenance
    │   ├── test_permissions_api.py       # 26 tests (S2-SEC-009..034): JWT Auth (401), RBAC (403/404), Fail-closed (503), Feature Lock
    │   └── test_maintenance_api.py       #  4 tests (S2-MAPI-001..004): Luồng HTTP Bảo trì khi SPRINT_FEATURE_LOCK=False
    ├── reports/                          # BÁO CÁO PHÂN TÍCH & NGHIỆM THU (MARKDOWN & JSON)
    │   ├── UNIT_TEST_PLAN.md             # Kế hoạch, phạm vi và chiến lược cô lập kiểm thử Sprint 1
    │   ├── UNIT_TEST_CASES.md            # Danh mục chi tiết toàn bộ 207 Test Cases (sinh tự động từ kết quả chạy thật)
    │   ├── UNIT_TEST_REPORT.md           # Báo cáo tổng hợp kết quả kiểm thử, Coverage & bảng ánh xạ Jira Sprint 1
    │   ├── UNIT_TEST_OPTIMIZATION_REPORT.md # Báo cáo quá trình tối ưu hóa (290 -> 261 -> 207 tests, tách 72 Unit / 135 API)
    │   ├── LEGACY_TEST_MIGRATION.md      # Bảng ánh xạ 35 Legacy tests trong tests.py (bỏ 29 test trùng, chuyển 6 test đặc thù)
    │   ├── FINAL_REVIEW.md               # Báo cáo đánh giá độc lập cuối cùng & 5 hạn chế kỹ thuật hiện tại
    │   ├── BUG_REPORT.md                 # Phân tích nguyên nhân gốc & cách sửa 5 lỗi (BUG-01..BUG-05)
    │   ├── COVERAGE_GAP_ANALYSIS.md      # Phân tích quá trình lấp đầy khoảng trống Coverage (93% -> 100%)
    │   ├── TEST_EXECUTION.md             # Nhật ký môi trường, lệnh chạy và kết quả thực thi
    │   └── results.json                  # Dữ liệu JSON chi tiết của 207 test cases (ID, scope, level, duration_sec, status)
    ├── evidence/                         # BẰNG CHỨNG THỰC THI (HTML, JUNIT XML, LOG, COVERAGE)
    │   ├── TEST_EXECUTION_REPORT.html    # Báo cáo HTML trực quan hiển thị tổng quan, bảng Coverage và 207 test cases
    │   ├── junit-report.xml              # Báo cáo chuẩn JUnit XML phục vụ tích hợp CI/CD hoặc import Jira Xray/Zephyr
    │   ├── test-execution.log            # Log console chi tiết (-v 2) của lần chạy 207 tests gần nhất
    │   ├── coverage_full_service2.txt    # Bảng tổng hợp text từ lệnh `coverage report --rcfile=.coveragerc -m`
    │   ├── individual_modules.log        # Bằng chứng lịch sử duy nhất ghi nhận 9 expectedFailure trước khi sửa BUG-01..05
    │   └── coverage/                     # Thư mục báo cáo HTML Coverage tương tác (`coverage/index.html`)
    └── tools/
        └── collect_results.py            # Công cụ thực thi test có đo thời gian và tự động xuất JSON, MD, HTML, JUnit XML
```

---

## 3. Phân loại kiểm thử (`207` Tests = `72` Unit + `135` API)

Hệ thống kiểm thử được tách thành hai gói riêng biệt theo đúng bản chất kỹ thuật:

### 3.1. Unit Tests — `72` tests (`testing/unit_tests/`)

Toàn bộ `72` tests trong `testing/unit_tests/` **không gọi HTTP API**, **không sử dụng `APIClient`**, và **không đi qua URL routing / Middleware**. Thời gian chạy toàn bộ `72` Unit Tests chỉ khoảng **`0.28 giây`**.

| File trong `unit_tests/` | Lớp Test | Số lượng | Mã Test Case | Phạm vi kiểm thử chính |
|---|---|---:|---|---|
| `test_models.py` | `PropertyModelTests` (`6`), `RoomModelTests` (`4`), `RoomRentabilityAndMaintenanceModelTests` (`5`) | **`15`** | `S2-MOD-001`..`015` | Giá trị mặc định, tự sinh mã `NTxxx`/`NTxxx-xxx`/`BTxxxx` chống trùng, `full_clean()`, `BUG-01`/`02`/`04`, bộ đếm phòng, `FK CASCADE`, `is_rentable` & `check_rentability()`. |
| `test_serializers.py` | `PropertySerializerTests` (`8`), `RoomSerializerTests` (`10`) | **`18`** | `S2-SER-001`..`018` | Validation trường bắt buộc, kiểu dữ liệu, đơn giá dịch vụ không âm (`BUG-03`), sức chứa `current_occupants <= max_occupants`, gán `owner_id` từ user, ẩn `PRIVATE_FIELDS` với `TENANT`. |
| `test_services.py` | `ParseHelperTests` (`6`), `ActorNameTests` (`1`), `ScopedQuerysetTests` (`12`), `MaintenanceViewSetUnitTests` (`9`) | **`28`** | `S2-UTL-001`..`007`, `S2-BIZ-001`..`021` | `7` test hàm tiện ích (`_parse_decimal`, `_parse_number`, `_actor_name`) + `21` test logic nghiệp vụ (`scoped_properties`, `scoped_rooms`, `scoped_maintenance`, `_room_status_after_maintenance` và các method của `MaintenanceRequestViewSet`). |
| `test_permissions.py` | `PermissionClassUnitTests` (`11`) | **`11`** | `S2-PERM-001`..`011` | Kiểm thử trực tiếp `auth.get_role`, `get_user_id`, `is_admin`, `is_landlord`, `is_manager`, `IsManagerOrReadOnly`, `IsManagerRole`, `SprintFeatureLock` và `_viewer_is_manager`. |

> **Lưu ý kỹ thuật trung thực về mức độ phụ thuộc ORM trong 72 Unit Tests:**
> Không phải toàn bộ `72` Unit Tests đều là kiểm thử thuần bộ nhớ (No-DB Solitary Unit Test):
> - **`18 / 72` tests** (`PermissionClassUnitTests`: `11`, `ParseHelperTests`: `6`, `ActorNameTests`: `1`) kế thừa `django.test.SimpleTestCase` — chạy **100% trong bộ nhớ Python, không chạm tới bất kỳ database nào (`0` DB queries)**.
> - **`54 / 72` tests** (`test_models.py`: `15`, `test_serializers.py`: `18`, `ScopedQuerysetTests`: `12`, `MaintenanceViewSetUnitTests`: `9`) kế thừa `django.test.TestCase` và sử dụng **SQLite In-Memory ORM**, bởi vì các quy tắc nghiệp vụ cốt lõi của Django/DRF (như `Model.save()` truy vấn chống trùng mã, `UniqueValidator`, `PrimaryKeyRelatedField`, `on_delete=CASCADE` và `QuerySet.filter()`) gắn liền với tầng ORM. Không có test nào kết nối tới SQL Server thật.

### 3.2. API / HTTP Tests — `135` tests (`testing/api_tests/`)

Toàn bộ `135` tests trong `testing/api_tests/` gửi HTTP request qua DRF `APIClient` để kiểm tra trọn vẹn chu trình **Request → Middleware/Authentication → Permission → ViewSet/QuerySet → Serializer → Database State → HTTP Response (Status Code & JSON Body)**. Thời gian chạy khoảng **`1.18 giây`**.

| File trong `api_tests/` | Lớp Test | Số lượng | Mã Test Case | Phạm vi kiểm thử chính |
|---|---|---:|---|---|
| `test_views.py` | `PropertyApiTests` (`30`), `RoomApiTests` (`33`) | **`63`** | `S2-API-001`..`063` | CRUD `/api/properties/` & `/api/rooms/`, Hard Delete vs Soft Delete (`DELETED`/`INACTIVE`), chặn xóa khi có phòng đang thuê, `update_status`, `rooms?status=` (`BUG-05`), `stats`, `room_matrix`, `summary`, `/status/`, `/check_rentable/`, `/available/`, `/occupied/`, `/maintenance/`, `/health/`. |
| `test_search_filter.py` | `RoomSearchTests` (`8`), `RoomFilterTests` (`17`), `RoomSortTests` (`7`), `PropertySearchFilterTests` (`8`), `MaintenanceReadFilterTests` (`2`) | **`42`** | `S2-FLT-001`..`042` | Tìm kiếm từ khóa, lọc theo nhà trọ, quận/phường/địa chỉ, tầng, trạng thái, khoảng giá, khoảng diện tích, sức chứa, lỗi tham số số học (`400`), chống rò rỉ tìm kiếm theo `tenant_name` với `TENANT`, sắp xếp 8 chiều, và lọc danh sách đọc Bảo trì. |
| `test_permissions_api.py` | `JwtAuthenticationApiTests` (`10`), `RoleAccessApiTests` (`16`) | **`26`** | `S2-SEC-009`..`034` | Xác thực JWT (`401` khi thiếu token, token hết hạn, sai chữ ký, sai định dạng, dùng `RefreshToken` làm access, thiếu `user_id`), cô lập dữ liệu giữa các `LANDLORD` (`404`), chặn `TENANT`/`STAFF` ghi dữ liệu (`403`), lọc liên kết `MOVED_OUT` (`S2-SEC-033`), fail-closed `503` khi Tenant Service lỗi, và ma trận `SprintFeatureLock` trên 9 endpoints bảo trì (`S2-SEC-034`). |
| `test_maintenance_api.py` | `MaintenanceAPIPipelineTests` (`4`) | **`4`** | `S2-MAPI-001`..`004` | Dùng `@override_settings(SPRINT_FEATURE_LOCK=False)` kiểm tra luồng HTTP E2E của `/api/maintenance/` (`create` → `start` → `update_status` → `record_cost` → `complete` → `cancel` → `history`) và phân quyền `TENANT` tạo/hủy yêu cầu bảo trì. |

---

## 4. Thống kê theo phạm vi Sprint

Bảng đối chiếu chính xác từ `reports/results.json` và `reports/FINAL_REVIEW.md`:

| Nhóm kiểm thử | Thuộc phạm vi Sprint 1 | Ngoài phạm vi Sprint 1 (Maintenance) | Tổng cộng | Kết quả thực thi |
|---|---:|---:|---:|---|
| **Unit Tests (`testing/unit_tests/`)** | **59** | **13** (`S2-MOD-014`..`015`, `S2-BIZ-011`..`021`) | **72** | **72 / 72 PASS** |
| **API / HTTP Tests (`testing/api_tests/`)** | **129** | **6** (`S2-FLT-041`..`042`, `S2-MAPI-001`..`004`) | **135** | **135 / 135 PASS** |
| **Tổng toàn bộ Service 2** | **188** | **19** | **207** | **207 / 207 PASS (`0` FAIL, `0` ERROR, `0` SKIP)** |

---

## 5. Cách chạy kiểm thử

Tất cả các lệnh bên dưới đều được chạy trên **Windows PowerShell** từ thư mục gốc dự án:
`C:\Users\Asus\.gemini\antigravity\scratch\nhatro_management`

### 5.1. Chạy tự động toàn bộ quy trình 6 bước (Khuyên dùng)

Script `run_tests.ps1` không nhận tham số dòng lệnh; khi gọi sẽ tự động thiết lập `DB_ENGINE=sqlite`, `DJANGO_SETTINGS_MODULE=config.service_settings.property`, chạy tuần tự cả 6 bước (Pure Unit Tests → API Tests → Full Suite + Coverage → Text & HTML Coverage → HTML/JUnit XML/Markdown Reports → Sprint 1 Verification), tự động xóa file tạm `backend/.coverage` và **tự động mở ngay 2 trang báo cáo HTML (`TEST_EXECUTION_REPORT.html` và `coverage/index.html`) trên trình duyệt mặc định sau khi chạy xong**:

```powershell
.\backend\services\property_service\testing\run_tests.ps1
```

*(Hoặc nếu đang đứng trực tiếp tại thư mục `backend\services\property_service\testing`, chạy: `.\run_tests.ps1`)*

### 5.2. Chạy riêng từng chế độ qua `tools/collect_results.py`

Script `collect_results.py` hỗ trợ đúng 3 cờ dòng lệnh (`--unit-only`, `--api-only`, `--sprint1-only`) và chế độ mặc định (Full Suite):

```powershell
# 1. Chạy riêng 72 Unit Tests (testing/unit_tests/)
.\backend\venv\Scripts\python.exe backend\services\property_service\testing\tools\collect_results.py --unit-only

# 2. Chạy riêng 135 API / HTTP Tests (testing/api_tests/)
.\backend\venv\Scripts\python.exe backend\services\property_service\testing\tools\collect_results.py --api-only

# 3. Chạy riêng 188 Tests thuộc phạm vi Sprint 1 (59 Unit + 129 API)
.\backend\venv\Scripts\python.exe backend\services\property_service\testing\tools\collect_results.py --sprint1-only

# 4. Chạy toàn bộ 207 Tests và cập nhật results.json, UNIT_TEST_CASES.md, TEST_EXECUTION_REPORT.html, junit-report.xml
.\backend\venv\Scripts\python.exe backend\services\property_service\testing\tools\collect_results.py
```

### 5.3. Chạy trực tiếp bằng Django `manage.py test`

```powershell
Push-Location backend
$env:DB_ENGINE = "sqlite"
$env:DJANGO_SETTINGS_MODULE = "config.service_settings.property"

# Chạy toàn bộ 207 tests của Service 2
.\venv\Scripts\python.exe manage.py test services.property_service -v 2

# Chỉ chạy 72 Unit Tests
.\venv\Scripts\python.exe manage.py test services.property_service.testing.unit_tests -v 2

# Chỉ chạy 135 API Tests
.\venv\Scripts\python.exe manage.py test services.property_service.testing.api_tests -v 2

Pop-Location
```

---

## 6. Coverage Report (`100%` trên 5 file phạm vi cấu hình)

Kết quả đo thực tế từ `Coverage.py 7.17.4` với cấu hình `backend/.coveragerc` (`branch = True`):

| File trong phạm vi đo | Statements | Missed | Branches | Partial | Statement Coverage | Branch Coverage | Total Coverage |
|---|---:|---:|---:|---:|---:|---:|---:|
| `services/property_service/models.py` | `207` | `0` | `30` | `0` | **100%** | **100%** | **100%** |
| `services/property_service/serializers.py` | `85` | `0` | `8` | `0` | **100%** | **100%** | **100%** |
| `services/property_service/service_urls.py` | `2` | `0` | `0` | `0` | **100%** | **100%** | **100%** |
| `services/property_service/urls.py` | `9` | `0` | `0` | `0` | **100%** | **100%** | **100%** |
| `services/property_service/views.py` | `456` | `0` | `172` | `0` | **100%** | **100%** | **100%** |
| **TOTAL** | **`759`** | **`0`** | **`210`** | **`0`** | **`100%`** | **`100%`** | **`100%`** |

> **Ghi chú minh bạch về phạm vi đo Coverage:**
> - Con số **100% Statement Coverage (`759/759`)** và **100% Branch Coverage (`210/210`)** là độ phủ của **5 file mã nguồn nghiệp vụ nằm trong phạm vi cấu hình `backend/.coveragerc`** (`models.py`, `serializers.py`, `views.py`, `urls.py`, `service_urls.py`), **không phải** độ phủ 100% trên mọi file trong toàn bộ repository.
> - Cấu hình `.coveragerc` chủ đích loại trừ (`omit`) các file cấu hình/khai báo tĩnh trong app (`admin.py`, `apps.py`, `migrations/*`, `__init__.py`, `tests.py`, `testing/*`).
> - Các module hạ tầng dùng chung đặt tại `backend/common/` (`auth.py`, `sprint.py`, `service_client.py`, `health.py`) và `backend/config/` (`service_settings/property.py`, `db_router.py`) tuy được bộ test của Service 2 thực thi nhưng **chưa nằm trong phạm vi `source = services/property_service`** của báo cáo Coverage này.

---

## 7. Phân biệt các loại kiểm thử trong Service 2

Để tránh nhầm lẫn khi đọc báo cáo nghiệm thu, bốn khái niệm kiểm thử trong dự án được phân biệt rõ như sau:

| Loại kiểm thử | Mục tiêu kiểm tra | Cách thực hiện & Ví dụ thực tế trong Service 2 |
|---|---|---|
| **1. Unit Test** | Kiểm tra tính đúng đắn của từng đơn vị mã nguồn nhỏ (hàm helper, phương thức của Model, logic validate của Serializer, biểu thức kiểm tra quyền) một cách cô lập, không đi qua tầng giao thức HTTP. | Gọi trực tiếp `_parse_decimal('abc', 'min_price')` (`S2-UTL-003`), `Room(rent_price=-1).full_clean()` (`S2-MOD-010`), hoặc `IsManagerRole().has_permission(req, None)` (`S2-PERM-008`). |
| **2. API Test** | Kiểm tra hợp đồng giao diện lập trình (REST API Contract) và quy tắc nghiệp vụ thông qua tầng HTTP: URL routing, HTTP Method, Status Code (`200`, `201`, `400`, `401`, `403`, `404`, `503`), cấu trúc JSON trả về, phân quyền JWT, lọc/tìm kiếm và trạng thái lưu xuống DB sau request. | Gọi `client.post('/api/rooms/', ...)` kiểm tra mã `201` & `code='NT100-102'` (`S2-API-032`), hoặc `client.delete('/api/properties/{id}/')` khi có phòng đang thuê phải bị chặn với `400 Bad Request` (`S2-API-017`). **Lưu ý: API Test kiểm tra toàn diện logic nghiệp vụ và bảo mật qua giao thức HTTP chứ không đơn thuần kiểm tra xem service có đang sống hay không.** |
| **3. Integration Test** | Kiểm tra sự phối hợp thực tế giữa nhiều thành phần hoặc nhiều microservice thật chạy đồng thời trên mạng và cơ sở dữ liệu thật (SQL Server). | Kiểm thử Service 2 (`:8002`) gọi HTTP thật sang Tenant Service (`:8003`) và Identity Service (`:8001`) trên SQL Server `nhatro_property_db` (thuộc bộ 22 test E2E Integration của toàn hệ thống, tách biệt với bộ test cô lập dùng mock trong thư mục `testing/` này). |
| **4. Health Check** | Chỉ kiểm tra tình trạng sẵn sàng hoạt động (liveness / readiness) và thông tin định danh cơ bản của tiến trình service mà không kiểm tra các luồng nghiệp vụ phức tạp. | Duy nhất test `S2-API-062` gọi `GET /health/` không cần JWT token, xác nhận service trả về `200 OK` kèm `{"key": "property", "port": 8002, "status": "UP"}`. |

---

## 8. Hệ thống báo cáo & bằng chứng kiểm thử

### 8.1. Các file trong `testing/reports/`
| Tên file | Vai trò & Nội dung chính |
|---|---|
| `FINAL_REVIEW.md` | Báo cáo rà soát độc lập cuối cùng: kiểm chứng bản chất của 72 Unit Tests (`18` `SimpleTestCase` + `54` ORM `TestCase`), 135 API Tests, các module ngoài phạm vi Coverage và 5 hạn chế kỹ thuật. |
| `UNIT_TEST_REPORT.md` | Báo cáo nghiệm thu tổng hợp của Service 2: thống kê kết quả chạy, bảng Coverage 100%, tổng hợp lỗi đã sửa và bảng ánh xạ 188 test Sprint 1 vào các Jira Issue (`[QLNT-*]`). |
| `UNIT_TEST_CASES.md` | Danh mục chi tiết toàn bộ **207 Test Cases** chia theo 8 file kiểm thử, ghi rõ Mã ID, Mã Legacy (nếu có), Phạm vi Sprint, Loại Test, Input, Expected Result, Actual Result và Trạng thái. |
| `UNIT_TEST_OPTIMIZATION_REPORT.md` | Báo cáo chi tiết quá trình tối ưu hóa bộ test từ `290` → `261` → `207` tests (`72` Unit + `135` API), liệt kê từng nhóm test đã gộp bằng `subTest`. |
| `LEGACY_TEST_MIGRATION.md` | Bảng đối chiếu toàn bộ 35 Legacy tests trong `tests.py`: lý do loại bỏ 29 test trùng lặp kèm mã test thay thế và chi tiết 6 test đặc thù được chuyển sang `testing/`. |
| `UNIT_TEST_PLAN.md` | Kế hoạch kiểm thử Sprint 1: mục tiêu, bảng đối chiếu chức năng với source code, phương pháp AAA và chiến lược mock cô lập Identity/Tenant Service. |
| `BUG_REPORT.md` | Hồ sơ 5 lỗi phát hiện qua Unit Test (`BUG-01`..`BUG-05`), bước tái hiện, nguyên nhân gốc trong `models.py`/`views.py` và các test xác nhận sửa lỗi. |
| `COVERAGE_GAP_ANALYSIS.md` | Phân tích chi tiết từng dòng lệnh và nhánh điều kiện giúp nâng Coverage từ `93%` (`36` missed stmts, `24` partial branches) lên `100%`. |
| `TEST_EXECUTION.md` | Nhật ký thông tin môi trường thực thi (Python, Django, Coverage.py, OS) và kết quả console thực tế qua từng đợt chạy. |
| `results.json` | File dữ liệu JSON có cấu trúc của 207 test cases (sinh tự động bởi `tools/collect_results.py`), là nguồn dữ liệu chuẩn cho các báo cáo. |

### 8.2. Các file trong `testing/evidence/`
| Tên file / thư mục | Vai trò & Nội dung chính |
|---|---|
| `TEST_EXECUTION_REPORT.html` | Báo cáo HTML độc lập (mở trực tiếp bằng trình duyệt) hiển thị thẻ tổng quan, bảng Coverage và bảng chi tiết 207 test cases kèm thời gian chạy (`ms`) và nhãn màu. |
| `junit-report.xml` | Báo cáo chuẩn JUnit XML (`<testsuites>` / `<testsuite>` / `<testcase>`) chứa kết quả và metadata của 207 tests để tích hợp CI/CD hoặc import vào Jira. |
| `coverage/index.html` | Báo cáo HTML Coverage tương tác do `coverage html` sinh ra, cho phép xem từng dòng lệnh và từng nhánh `if/else` của 5 file source trong Service 2. |
| `coverage_full_service2.txt` | Kết quả xuất dạng bảng text từ lệnh `coverage report --rcfile=.coveragerc -m`. |
| `test-execution.log` | Bản ghi toàn bộ đầu ra console (`-v 2`) khi chạy 207 tests trong `run_tests.ps1`. |
| `individual_modules.log` | Bằng chứng lịch sử từ giai đoạn trước khi sửa bug, ghi nhận `9 expectedFailure` tái hiện `BUG-01`..`BUG-05`. |

---

## 9. Những hạn chế kỹ thuật hiện tại

Để đảm bảo tính minh bạch học thuật và kỹ thuật khi nghiệm thu, hệ thống kiểm thử hiện tại có **5 hạn chế** được ghi nhận rõ:

1. **54/72 Unit Tests sử dụng SQLite In-Memory ORM (`django.test.TestCase`):**
   - Chỉ có `18/72` Unit Tests sử dụng `SimpleTestCase` thuần bộ nhớ 100%; `54/72` Unit Tests còn lại có truy vấn qua SQLite In-Memory ORM do đặc thù thiết kế gắn liền ORM của Django `Model`, `ModelSerializer` và `QuerySet`.
2. **SQLite In-Memory không mô phỏng đầy đủ mọi đặc tính của SQL Server:**
   - Môi trường chạy Unit/API Test dùng `DB_ENGINE=sqlite` để đảm bảo tốc độ (`~1.4s`) và tính cô lập, nhưng SQLite có sự khác biệt so với SQL Server (`mssql-django`) về xử lý collation tiếng Việt có dấu, cơ chế khóa bảng/giao dịch và độ chính xác kiểu số thập phân ở tầng DB engine.
3. **Giao tiếp với Tenant Service (`:8003`) đang sử dụng Mock tĩnh:**
   - Các kịch bản của `TENANT` sử dụng `patch_rented_rooms` hoặc `patch_tenant_links` để giả lập kết quả trả về từ `http://127.0.0.1:8003/api/tenants/links/`. Nếu Tenant Service thay đổi cấu trúc JSON trả về mà không cập nhật mock tại Service 2, bộ test cô lập này sẽ không tự phát hiện được (cần kiểm thử tích hợp liên service để kiểm chứng).
4. **9 Maintenance Unit Tests (`S2-BIZ-013`..`021`) gọi trực tiếp các private/internal methods của ViewSet:**
   - Do `SPRINT_FEATURE_LOCK=True` khóa các API ghi bảo trì ở tầng HTTP trong Sprint 1, 9 unit test trong `MaintenanceViewSetUnitTests` khởi tạo trực tiếp `MaintenanceRequestViewSet` và gọi các phương thức nội bộ (`_set_room_status`, `_ensure_transition`, `_do_start`, `perform_create`, `perform_update`). Việc này tạo sự phụ thuộc vào chi tiết cài đặt nội bộ (implementation coupling) nếu sau này đổi tên các helper đó.
5. **Coverage 100% chưa bao gồm các module dùng chung ngoài thư mục `services/property_service/`:**
   - Báo cáo Coverage hiện chỉ đo 5 file trong `services/property_service/`, chưa thống kê tỷ lệ bao phủ dòng lệnh của các module dùng chung trong `backend/common/` (`auth.py`, `sprint.py`, `service_client.py`, `health.py`) và `backend/config/`.

---

## 10. Quy trình khi bổ sung Test Case mới

Khi mở rộng tính năng cho Service 2 (hoặc khi mở khóa module Bảo trì ở Sprint tiếp theo), hãy tuân thủ quy trình 6 bước sau:

### Bước 1: Xác định đúng loại Test và vị trí đặt file
- **Tạo Unit Test trong `testing/unit_tests/` khi:**
  - Kiểm tra phương thức/thuộc tính/validator của Model (`test_models.py`).
  - Kiểm tra logic validate hoặc biểu diễn dữ liệu của Serializer không cần qua HTTP (`test_serializers.py`).
  - Kiểm tra hàm tiện ích (`_parse_*`, `_actor_name` — dùng `SimpleTestCase`) hoặc hàm lọc phạm vi dữ liệu `scoped_*` (`test_services.py`).
  - Kiểm tra lớp phân quyền (`BasePermission`) hoặc hàm kiểm tra role (`test_permissions.py` — dùng `SimpleTestCase`).
- **Tạo API / HTTP Test trong `testing/api_tests/` khi:**
  - Kiểm tra HTTP Status Code (`200`, `201`, `400`, `401`, `403`, `404`, `503`), URL routing, JSON payload trả về từ endpoint (`test_views.py`).
  - Kiểm tra query parameters tìm kiếm, lọc, sắp xếp qua URL (`test_search_filter.py`).
  - Kiểm tra xác thực JWT header hoặc phân quyền truy cập giữa các role qua HTTP (`test_permissions_api.py`).
  - Kiểm tra luồng HTTP của module Bảo trì (`test_maintenance_api.py`).

### Bước 2: Quy ước đặt tên hàm và docstring định danh (`S2-<NHÓM>-<STT>`)
- Tên hàm bắt đầu bằng `test_<mô_tả_hành_vi_và_kết_quả_mong_đợi>`.
- Dòng đầu tiên của docstring **bắt buộc** bắt đầu bằng mã Test Case theo định dạng chuẩn để `tools/collect_results.py` tự động trích xuất vào báo cáo:
  ```python
  def test_ten_kich_ban_kiem_thu(self):
      """S2-MOD-016 | Mô tả ngắn mục tiêu | Data: dữ liệu đầu vào | Expected: kết quả kỳ vọng"""
  ```
  Các tiền tố mã chuẩn:
  - `S2-MOD-xxx`: Model Unit Tests (`unit_tests/test_models.py`)
  - `S2-SER-xxx`: Serializer Unit Tests (`unit_tests/test_serializers.py`)
  - `S2-UTL-xxx`: Utility / Validator Unit Tests (`unit_tests/test_services.py`)
  - `S2-BIZ-xxx`: Service / Business Logic Unit Tests (`unit_tests/test_services.py`)
  - `S2-PERM-xxx`: Permission Logic Unit Tests (`unit_tests/test_permissions.py`)
  - `S2-API-xxx`: Property & Room CRUD / Status API Tests (`api_tests/test_views.py`)
  - `S2-FLT-xxx`: Search / Filter / Sort API Tests (`api_tests/test_search_filter.py`)
  - `S2-SEC-xxx`: JWT Auth & RBAC Security API Tests (`api_tests/test_permissions_api.py`)
  - `S2-MAPI-xxx`: Maintenance HTTP Pipeline API Tests (`api_tests/test_maintenance_api.py`)

### Bước 3: Phân loại rõ phạm vi Sprint 1 vs Ngoài Sprint 1
- Nếu test kiểm tra chức năng thuộc **Sprint 1 (Property & Room)**: viết docstring bình thường như trên.
- Nếu test kiểm tra chức năng **ngoài phạm vi Sprint 1 (ví dụ: Maintenance)**:
  1. Thêm nhãn `[Ngoài Sprint 1]` ngay trong docstring:
     ```python
     """S2-BIZ-022 | [Ngoài Sprint 1] Mô tả kịch bản bảo trì | Data: ... | Expected: ..."""
     ```
  2. (Tùy chọn) Thêm mã ID vào tập `OUT_OF_SPRINT1_IDS` trong `testing/tools/collect_results.py`. Công cụ `collect_results.py` tự động nhận diện cả qua `OUT_OF_SPRINT1_IDS` lẫn chuỗi `[Ngoài Sprint 1]` trong docstring để tách riêng khi chạy `--sprint1-only`.

### Bước 4: Chạy lại bộ kiểm thử và cập nhật báo cáo tự động
Sau khi thêm test, chạy lệnh duy nhất từ thư mục gốc dự án:
```powershell
.\backend\services\property_service\testing\run_tests.ps1
```

### Bước 5: Kiểm tra kết quả đầu ra
1. Xác nhận script kết thúc với thông báo `[SUCCESS]` và exit code `0`.
2. Kiểm tra bảng `coverage report -m` trên màn hình (hoặc trong `testing/evidence/coverage_full_service2.txt`) không phát sinh dòng `Miss` hay nhánh `BrPart` mới.
3. Kiểm tra các file báo cáo được cập nhật tự động:
   - `testing/reports/results.json`
   - `testing/reports/UNIT_TEST_CASES.md`
   - `testing/evidence/TEST_EXECUTION_REPORT.html`
   - `testing/evidence/junit-report.xml`
   - `testing/evidence/coverage/index.html`

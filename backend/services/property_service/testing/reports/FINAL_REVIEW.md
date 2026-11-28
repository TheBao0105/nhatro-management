# FINAL REVIEW — BỘ KIỂM THỬ SERVICE 2 (PROPERTY & ROOM)

> Tài liệu này đánh giá độc lập, khách quan và minh bạch toàn bộ hệ thống kiểm thử của **Service 2 — Property & Room** (`backend/services/property_service/testing/`) ở trạng thái hiện tại (**`207` tests = `72` Unit Tests + `135` API/HTTP Tests**, **`188` Sprint 1 + `19` Ngoài Sprint 1**), chỉ rõ mức độ "thuần đơn vị" (Pure Unit) của 72 Unit Tests, các module chưa đưa vào phạm vi đo Coverage và những hạn chế kỹ thuật còn tồn tại.

---

## 1. Kiểm tra thực tế 72 Unit Tests (`testing/unit_tests/`) có đúng là Unit Test thuần không?

Qua đọc trực tiếp mã nguồn của 4 file trong `backend/services/property_service/testing/unit_tests/` (`test_models.py`, `test_serializers.py`, `test_services.py`, `test_permissions.py`), kết quả đánh giá theo 4 tiêu chí như sau:

### 1.1. Đánh giá theo 4 tiêu chí

| Tiêu chí kiểm tra | Kết quả thực tế trên 72 Unit Tests | Phân tích chi tiết |
|---|---|---|
| **1. Không gọi HTTP API** | **ĐẠT 100% (`72/72` tests)** | Không có bất kỳ test nào trong `testing/unit_tests/` khởi tạo hay gọi `APIClient`, `self.client.get/post/patch/delete`, hoặc gửi request qua tầng URL routing / WSGI của Django. |
| **2. Không kiểm thử toàn bộ request–response pipeline** | **ĐẠT 100% (`72/72` tests)** | Các test chỉ gọi trực tiếp hàm/phương thức Python (`_parse_decimal`, `_parse_number`, `_actor_name`, `scoped_*`, `Model.full_clean()`, `Room.check_rentability()`, `Serializer.is_valid()`, `Permission.has_permission()`, hoặc method nội bộ `ViewSet.perform_create/start/complete/cancel` với `SimpleNamespace` giả lập `request`). Không đi qua Middleware, URL resolver, Authentication backend hay Renderer. |
| **3. Có assertion kiểm tra kết quả nghiệp vụ** | **ĐẠT 100% (`72/72` tests)** | Mọi test đều có assertion nghiệp vụ cụ thể (kiểm tra mã tự sinh `NTxxx`/`NTxxx-xxx`/`BTxxxx`, kiểm tra `ValidationError` đúng tên trường cho `BUG-01`..`BUG-04`, kiểm tra ẩn PII `tenant_name`/`tenant_phone`, kiểm tra cô lập queryset theo role, kiểm tra luồng chuyển trạng thái phòng và bảo trì). |
| **4. Không phụ thuộc vào database thật** | **ĐẠT 100% đối với SQL Server thật, NHƯNG chỉ `18/72` test là hoàn toàn không chạm SQLite In-Memory DB** | - **0/72 test** kết nối tới database SQL Server thật (`nhatro_property_db`).<br>- Tuy nhiên, nếu xét theo định nghĩa **Strict Solitary Unit Test** (không chạm tới cả SQLite in-memory test DB của Django ORM), thì trong `72` test có **`18` test dùng `SimpleTestCase`** (100% in-memory Python, không có DB) và **`54` test kế thừa `django.test.TestCase`** (có đọc/ghi qua SQLite in-memory ORM). |

### 1.2. Phân loại chi tiết 72 Unit Tests theo mức độ phụ thuộc Django ORM (SQLite In-Memory)

| File trong `testing/unit_tests/` | Lớp Test (`TestCase` vs `SimpleTestCase`) | Số test | Có gọi HTTP không? | Có dùng SQLite In-Memory ORM không? | Lý do kỹ thuật |
|---|---|---:|---|---|---|
| `test_permissions.py` | `PermissionClassUnitTests(SimpleTestCase)` | **`11`** | Không | **Không (`0` DB queries)** | Kiểm thử thuần hàm/lớp Python (`common.auth`, `SprintFeatureLock`, `_viewer_is_manager`) với `SimpleNamespace` và `unittest.mock.Mock`. |
| `test_services.py` | `ParseHelperTests(SimpleTestCase)`, `ActorNameTests(SimpleTestCase)` | **`7`** | Không | **Không (`0` DB queries)** | Kiểm thử thuần hàm Python (`_parse_decimal`, `_parse_number`, `_actor_name`). |
| `test_models.py` | `PropertyModelTests(TestCase)`, `RoomModelTests(TestCase)`, `RoomRentabilityAndMaintenanceModelTests(TestCase)` | **`15`** | Không | **Có (Django ORM + SQLite In-Memory)** | Trong Django, các hành vi cốt lõi của Model như `save()` tự sinh mã chống trùng (`Property.objects.filter(code=...).exists()`), ràng buộc `IntegrityError` (`UNIQUE`, `FK NOT NULL`, `on_delete=CASCADE`), `Meta.ordering` và các thuộc tính đếm phòng (`self.rooms.filter(...)`) đều gắn chặt với tầng ORM. |
| `test_serializers.py` | `PropertySerializerTests(TestCase)`, `RoomSerializerTests(TestCase)` | **`18`** | Không | **Có (Django ORM + SQLite In-Memory)** | `PropertySerializer` và `RoomSerializer` là `ModelSerializer`: `UniqueValidator` trên `code`, `PrimaryKeyRelatedField(queryset=Property.objects.all())` và `ser.save()` đều truy vấn ORM. |
| `test_services.py` | `ScopedQuerysetTests(TestCase)`, `MaintenanceViewSetUnitTests(TestCase)` | **`21`** | Không | **Có (Django ORM + SQLite In-Memory)** | `scoped_properties`, `scoped_rooms`, `scoped_maintenance` trả về Django `QuerySet` (`Property.objects.filter(...)`), và các hàm `perform_create`/`perform_update`/`_do_start` thao tác trực tiếp trên model instance & `MaintenanceHistory`. |
| **TỔNG CỘNG** | **4 files (`72` Unit Tests)** | **`72`** | **0 HTTP** | **`18` No-DB + `54` ORM Unit Tests** | Hoàn toàn không chạm SQL Server thật; chạy toàn bộ 72 test chỉ mất **`0.28s`**. |

---

## 2. Kiểm tra 135 API / HTTP Tests (`testing/api_tests/`) có được phân loại đúng không?

Qua rà soát toàn bộ 4 file trong `backend/services/property_service/testing/api_tests/`:

| File trong `testing/api_tests/` | Lớp Test | Số test | Bản chất kỹ thuật thực tế | Kết luận phân loại |
|---|---|---:|---|---|
| [test_views.py](file:///c:/Users/Asus/.gemini/antigravity/scratch/nhatro_management/backend/services/property_service/testing/api_tests/test_views.py) | `PropertyApiTests`, `RoomApiTests` | **`63`** | Gửi HTTP request qua DRF `APIClient` (`GET`, `POST`, `PUT`, `PATCH`, `DELETE`) tới `/api/properties/...`, `/api/rooms/...`, `/health/`; kiểm tra HTTP status code, JSON response và trạng thái DB. | **100% đúng là API / HTTP Test** |
| [test_search_filter.py](file:///c:/Users/Asus/.gemini/antigravity/scratch/nhatro_management/backend/services/property_service/testing/api_tests/test_search_filter.py) | `RoomSearchTests`, `RoomFilterTests`, `RoomSortTests`, `PropertySearchFilterTests`, `MaintenanceReadFilterTests` | **`42`** | Gửi HTTP `GET` có query string (`?search=...&min_price=...&sort=...`) qua `APIClient` tới `/api/rooms/`, `/api/properties/`, `/api/maintenance/`, `/api/maintenance-history/`. | **100% đúng là API / HTTP Test** |
| [test_permissions_api.py](file:///c:/Users/Asus/.gemini/antigravity/scratch/nhatro_management/backend/services/property_service/testing/api_tests/test_permissions_api.py) | `JwtAuthenticationApiTests`, `RoleAccessApiTests` | **`26`** | Gửi HTTP request kèm header `Authorization: Bearer <jwt>` qua `APIClient` để kiểm tra middleware/authentication (`401`), phân quyền RBAC (`403`/`404`), fail-closed khi gọi `requests.get` sang Tenant Service (`503`) và ma trận `SprintFeatureLock` trên 9 endpoints. *(Lưu ý: `S2-SEC-018` kiểm tra `settings.SIMPLE_JWT` để bổ trợ cho nhóm `JwtAuthenticationApiTests`).* | **Đúng nhóm API / Security Integration Test** |
| [test_maintenance_api.py](file:///c:/Users/Asus/.gemini/antigravity/scratch/nhatro_management/backend/services/property_service/testing/api_tests/test_maintenance_api.py) | `MaintenanceAPIPipelineTests` | **`4`** | Dùng `@override_settings(SPRINT_FEATURE_LOCK=False)` gửi chuỗi HTTP request E2E qua `APIClient` tới `/api/maintenance/...`. | **100% đúng là API / HTTP Pipeline Test** |
| **TỔNG CỘNG** | **4 files (`135` API Tests)** | **`135`** | Đi qua full DRF HTTP request–response pipeline | **Phân loại chính xác** |

---

## 3. Rà soát Source Code Service 2 & Các Module Chưa Đưa Vào Coverage

### 3.1. Các file trong `backend/services/property_service/`
Hiện tại `backend/.coveragerc` đặt `source = services/property_service` và `omit`:
```ini
[run]
branch = True
source = services/property_service
omit =
    */migrations/*
    */testing/*
    */unit_tests/*
    */tests.py
    */admin.py
    */apps.py
    */__init__.py
```

Đối chiếu toàn bộ các file `.py` trong `backend/services/property_service/`:

| File Source | Đưa vào Coverage? | Stmts / Branches | Độ phủ hiện tại | Đánh giá & Lý do nếu chưa đưa vào Coverage |
|---|---|---|---|---|
| `models.py` | **Có** | `207` stmts / `30` branches | **100%** | Chứa toàn bộ model `Property`, `Room`, `MaintenanceRequest`, `MaintenanceHistory` và validators. |
| `serializers.py` | **Có** | `85` stmts / `8` branches | **100%** | Chứa `_viewer_is_manager`, `RoomSerializer`, `PropertySerializer`, `Maintenance*Serializer`. |
| `views.py` | **Có** | `456` stmts / `172` branches | **100%** | Chứa helpers `_parse_*`, `_actor_name`, `scoped_*`, `PropertyViewSet`, `RoomViewSet`, `Maintenance*ViewSet`. |
| `urls.py` | **Có** | `9` stmts / `0` branches | **100%** | Định tuyến DRF `DefaultRouter` cho `properties`, `rooms`, `maintenance`, `maintenance-history`. |
| `service_urls.py` | **Có** | `2` stmts / `0` branches | **100%** | Gắn `make_service_urlpatterns` cho Service 2 độc lập (`:8002`). |
| `admin.py` (`32` dòng) | **Không (`omit`)** | ~`20` stmts | *Không đo* | Chỉ chứa khai báo `@admin.register(...)` tĩnh cho Django Admin (`PropertyAdmin`, `RoomAdmin`, `MaintenanceRequestAdmin`, `MaintenanceHistoryAdmin`), không có phương thức tuỳ chỉnh và không phục vụ REST API SOA. |
| `apps.py` (`7` dòng) | **Không (`omit`)** | `4` stmts | *Không đo* | Khai báo metadata `PropertyServiceConfig(AppConfig)` mặc định của Django. |
| `migrations/*.py` | **Không (`omit`)** | Schema auto-gen | *Không đo* | File migration sinh tự động bởi Django. |
| `tests.py` & `testing/*` | **Không (`omit`)** | Mã kiểm thử | *Không đo* | Theo chuẩn Coverage, không tính mã test vào độ phủ của mã sản phẩm. |

### 3.2. Các module dùng chung bên ngoài `services/property_service/` mà Service 2 phụ thuộc
Mặc dù các test trong `testing/` **đã thực thi và kiểm thử** các module dùng chung dưới đây, nhưng do `.coveragerc` chỉ đặt `source = services/property_service` nên các file này **không nằm trong bảng báo cáo Coverage của riêng Service 2**:
1. **`backend/common/auth.py`**: Chứa `StatelessJWTAuthentication`, `get_role`, `get_user_id`, `is_admin`, `is_landlord`, `is_manager`, `IsManagerOrReadOnly`, `IsManagerRole` (đã được kiểm thử bởi `S2-PERM-001`..`008` và `S2-SEC-009`..`028`).
2. **`backend/common/sprint.py`**: Chứa `SprintFeatureLock` (đã được kiểm thử bởi `S2-PERM-009`..`010` và `S2-SEC-034`).
3. **`backend/common/service_client.py`**: Chứa `own_rented_room_ids` gọi HTTP sang Tenant Service `:8003` và ném `UpstreamServiceUnavailable` `503` (đã được kiểm thử bởi `S2-SEC-029`..`033`).
4. **`backend/common/health.py` & `backend/common/schema.py`**: Endpoint `/health/` và wrapper URL của service (đã được kiểm thử bởi `S2-API-062`).
5. **`backend/config/service_settings/property.py` & `backend/config/db_router.py`**: Cấu hình settings độc lập của Service 2 và `StatelessServiceRouter`.

---

## 4. Đối chiếu Số lượng Test trong Từng File với Kết quả Thực tế từ Test Runner

Kết quả trích xuất trực tiếp từ `DiscoverRunner` và `results.json` khớp tuyệt đối 100% với mã nguồn trong từng file:

|Thư mục|File kiểm thử|Lớp Test (`TestCase` / `SimpleTestCase`)|Số test trong code|Số test Runner chạy|Trong Sprint 1|Ngoài Sprint 1|Kết quả|
|---|---|---|---:|---:|---:|---:|---|
|`unit_tests/`|`test_models.py`|`PropertyModelTests` (`6`), `RoomModelTests` (`4`), `RoomRentabilityAndMaintenanceModelTests` (`5`)|**15**|**15**|`13`|`2` (`S2-MOD-014`, `015`)|**15 PASS**|
|`unit_tests/`|`test_serializers.py`|`PropertySerializerTests` (`8`), `RoomSerializerTests` (`10`)|**18**|**18**|`18`|`0`|**18 PASS**|
|`unit_tests/`|`test_services.py`|`ParseHelperTests` (`6`), `ActorNameTests` (`1`), `ScopedQuerysetTests` (`12`), `MaintenanceViewSetUnitTests` (`9`)|**28**|**28**|`17`|`11` (`S2-BIZ-011`..`021`)|**28 PASS**|
|`unit_tests/`|`test_permissions.py`|`PermissionClassUnitTests` (`11`)|**11**|**11**|`11`|`0`|**11 PASS**|
|`api_tests/`|`test_views.py`|`PropertyApiTests` (`30`), `RoomApiTests` (`33`)|**63**|**63**|`63`|`0`|**63 PASS**|
|`api_tests/`|`test_search_filter.py`|`RoomSearchTests` (`8`), `RoomFilterTests` (`17`), `RoomSortTests` (`7`), `PropertySearchFilterTests` (`8`), `MaintenanceReadFilterTests` (`2`)|**42**|**42**|`40`|`2` (`S2-FLT-041`, `042`)|**42 PASS**|
|`api_tests/`|`test_permissions_api.py`|`JwtAuthenticationApiTests` (`10`), `RoleAccessApiTests` (`16`)|**26**|**26**|`26`|`0`|**26 PASS**|
|`api_tests/`|`test_maintenance_api.py`|`MaintenanceAPIPipelineTests` (`4`)|**4**|**4**|`0`|`4` (`S2-MAPI-001`..`004`)|**4 PASS**|
|**TỔNG**|**8 files**|**18 Test Classes**|**207**|**207**|**188**|**19**|**207 PASS**|

---

## 5. Kiểm tra Tính Thống Nhất Số Liệu Sprint 1 vs Ngoài Sprint 1

Đối chiếu với 4 con số yêu cầu trong đề bài:

| Nhóm phân loại | Con số trong yêu cầu | Kết quả kiểm đếm từ Test Runner (`results.json`) | Chi tiết các mã Test ID cấu thành | Đánh giá |
|---|---:|---:|---|---|
| **1. Unit Tests — Sprint 1** | **`59`** | **`59`** | `S2-MOD-001`..`013` (`13`) + `S2-SER-001`..`018` (`18`) + `S2-UTL-001`..`007` (`7`) + `S2-BIZ-001`..`010` (`10`) + `S2-PERM-001`..`011` (`11`) = **`59`** | **Khớp chính xác 100%** |
| **2. Unit Tests — Ngoài Sprint 1** | **`13`** | **`13`** | `S2-MOD-014`..`015` (`2`) + `S2-BIZ-011`..`021` (`11`) = **`13`** | **Khớp chính xác 100%** |
| **3. API Tests — Sprint 1** | **`129`** | **`129`** | `S2-API-001`..`063` (`63`) + `S2-FLT-001`..`040` (`40`) + `S2-SEC-009`..`034` (`26`) = **`129`** | **Khớp chính xác 100%** |
| **4. API Tests — Ngoài Sprint 1** | **`6`** | **`6`** | `S2-FLT-041`..`042` (`2`) + `S2-MAPI-001`..`004` (`4`) = **`6`** | **Khớp chính xác 100%** |
| **TỔNG CỘNG** | **`207`** | **`207`** | **Sprint 1 = `59 + 129 = 188` \| Ngoài Sprint 1 = `13 + 6 = 19`** | **Thống nhất tuyệt đối** |

### Phát hiện và đính chính 1 điểm chưa đồng bộ nhỏ trong comment/log của script:
- Trong file báo cáo `UNIT_TEST_REPORT.md`, `UNIT_TEST_CASES.md`, `UNIT_TEST_OPTIMIZATION_REPORT.md` và `TEST_EXECUTION.md`, toàn bộ các bảng đều đã ghi đúng **`188` Sprint 1 + `19` Ngoài Sprint 1**.
- Tuy nhiên, tại dòng docstring đầu file `testing/tools/collect_results.py` và dòng `Write-Host` cuối của `testing/run_tests.ps1` còn sót chuỗi comment tĩnh `"189 Sprint 1 + 18 Out-of-Sprint-1"` (do viết trước khi tách `S2-BIZ-027` và `S2-BIZ-028` ngoài Sprint 1 thành 4 test `S2-BIZ-018`..`021`).
- **Đã xử lý:** Đã cập nhật lại đúng chuỗi comment trong `collect_results.py` và `run_tests.ps1` thành `188 Sprint 1 + 19 Out-of-Sprint-1` mà không thay đổi bất kỳ test nào.

---

## 6. Những Hạn Chế Kỹ Thuật Còn Tồn Tại (Báo cáo trung thực)

Dù bộ kiểm thử đạt `207/207 PASS` và `100%` Statement/Branch Coverage trên 5 file source chính của Service 2, hệ thống kiểm thử hiện tại vẫn có **5 hạn chế kỹ thuật** cần được ghi nhận rõ khi nghiệm thu:

1. **54/72 Unit Tests trong `testing/unit_tests/` là Sociable/ORM Unit Tests (dùng SQLite In-Memory), không phải Solitary Unit Tests thuần bộ nhớ 100%:**
   - Chỉ có `18/72` test (`PermissionClassUnitTests`, `ParseHelperTests`, `ActorNameTests`) chạy bằng `SimpleTestCase` hoàn toàn không chạm database.
   - `54/72` test còn lại (`test_models.py`, `test_serializers.py`, `ScopedQuerysetTests`, `MaintenanceViewSetUnitTests`) kế thừa `django.test.TestCase` và tương tác với SQLite in-memory database vì logic nghiệp vụ của Django/DRF (`Model.save()`, `UniqueValidator`, `QuerySet.filter()`, `on_delete=CASCADE`) gắn liền với ORM.
2. **Môi trường kiểm thử dùng SQLite In-Memory trong khi môi trường triển khai thực tế dùng SQL Server (`mssql-django`):**
   - `run_tests.ps1` chạy với `DB_ENGINE=sqlite` để tốc độ nhanh (`1.39s`) và cô lập hoàn toàn khỏi DB phát triển.
   - Tuy nhiên, SQLite có một số khác biệt so với SQL Server về collation (`icontains` với tiếng Việt có dấu), hành vi khóa giao dịch (transaction locking) và kiểu `Decimal`. (Rủi ro này đã được giảm thiểu nhờ bộ 22 test tích hợp E2E trên SQL Server thật ở giai đoạn trước, nhưng bản thân bộ Unit Test hiện tại chạy trên SQLite).
3. **Cô lập giao tiếp liên Service (`Tenant Service :8003` và `Identity Service :8001`) dựa trên Mock tĩnh:**
   - Các test của `TENANT` sử dụng `patch_rented_rooms` hoặc `patch_tenant_links` để giả lập payload JSON trả về từ `http://127.0.0.1:8003/api/tenants/links/`. Nếu bên Service 3 (Tenant Service) thay đổi cấu trúc schema JSON của endpoint `/api/tenants/links/` mà không cập nhật mock ở Service 2, Unit Test của Service 2 vẫn sẽ PASS (cần Contract Test hoặc E2E Integration Test để phát hiện).
4. **Một số Unit Test trong `MaintenanceViewSetUnitTests` (`S2-BIZ-013`..`021`) gắn chặt với cài đặt nội bộ (Implementation Coupling):**
   - Để kiểm thử mã nguồn bảo trì trong khi vẫn giữ `SPRINT_FEATURE_LOCK=True` ở Sprint 1, các test `S2-BIZ-013`..`021` khởi tạo trực tiếp `MaintenanceRequestViewSet()` với `SimpleNamespace` và gọi các helper nội bộ như `_set_room_status`, `_ensure_transition`, `_do_start`. Nếu sau này refactor đổi tên các private method này, các unit test đó sẽ cần cập nhật theo.
5. **Coverage 100% chỉ tính trên 5 file của `services/property_service/`, chưa bao gồm `backend/common/`:**
   - Bảng Coverage `100%` (`759/759` statements, `210/210` branches) đo lường phạm vi `source = services/property_service` (đã omit `admin.py`, `apps.py`, `migrations/*`). Các module hạ tầng dùng chung tại `backend/common/` (`auth.py`, `service_client.py`, `sprint.py`, `health.py`) tuy được các test của Service 2 gọi tới nhưng không nằm trong báo cáo số liệu Coverage của riêng Service 2.

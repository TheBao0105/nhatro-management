# COVERAGE GAP ANALYSIS — Sprint 1 / Service 2 (Property & Room)

> Báo cáo phân tích khoảng trống Coverage ban đầu (`93%`, `36` missed statements, `24` partial branches) và kết quả sau khi bổ sung **14 test case** (`1` test Sprint 1 + `13` test bổ sung ngoài Sprint 1 cho module Bảo trì) đưa toàn bộ **Service 2 — Property & Room** lên **100% Statement Coverage, 100% Branch Coverage, 100% Total Coverage** (xác nhận thực tế lúc `2026-11-22 09:30`).

---

## 1. So sánh Độ phủ Trước & Sau khi bổ sung Test

| File | Stmts | Branches | Trước bổ sung (`276` tests) | Sau bổ sung (`290` tests / `255` `unit_tests`) | Missed Stmts hiện tại | Partial Branches hiện tại |
|---|---:|---:|---:|---:|---:|---:|
| `services/property_service/models.py` | `207` | `30` | `97%` (`4` miss, `2` par) | **100%** | **`0`** | **`0`** |
| `services/property_service/serializers.py` | `85` | `8` | `100%` (`0` miss, `0` par) | **100%** | **`0`** | **`0`** |
| `services/property_service/service_urls.py` | `2` | `0` | `100%` (`0` miss, `0` par) | **100%** | **`0`** | **`0`** |
| `services/property_service/urls.py` | `9` | `0` | `100%` (`0` miss, `0` par) | **100%** | **`0`** | **`0`** |
| `services/property_service/views.py` | `456` | `172` | `90%` (`32` miss, `22` par) | **100%** | **`0`** | **`0`** |
| **TOTAL** | **`759`** | **`210`** | **`93%` (`36` miss, `24` par)** | **`100%`** | **`0`** | **`0`** |

Bằng chứng HTML Coverage mới nhất:
- Toàn bộ Service 2 (`290` tests): [../evidence/coverage/index.html](file:///c:/Users/Asus/.gemini/antigravity/scratch/nhatro_management/backend/services/property_service/testing/evidence/coverage/index.html)
- HTML Test Report (`290` tests): [../evidence/TEST_EXECUTION_REPORT.html](file:///c:/Users/Asus/.gemini/antigravity/scratch/nhatro_management/backend/services/property_service/testing/evidence/TEST_EXECUTION_REPORT.html)

---

## 2. Bảng đối chiếu 14 Test Case đã bổ sung & Các dòng/nhánh đã phủ

> **Phân biệt rõ phạm vi:**
> - **Thuộc phạm vi Sprint 1 (`1` test):** `S2-MOD-044` (nhánh phòng thủ `Room.check_rentability()`).
> - **Bổ sung ngoài phạm vi Sprint 1 (`13` test — gắn nhãn `[Ngoài Sprint 1]`):** `S2-MOD-045`..`046`, `S2-BIZ-020`..`028`, `S2-FLT-041`..`042` kiểm thử trực tiếp model, helper, method nội bộ của `MaintenanceRequestViewSet` và bộ lọc `GET` của module Bảo trì mà **không tắt `SPRINT_FEATURE_LOCK`** và không mở khóa các API ghi bảo trì.

| Test ID | Phạm vi | File Test | Dòng / Nhánh đã phủ | Mục đích & Kết quả xác nhận | Trạng thái |
|---|---|---|---|---|---|
| **`S2-MOD-044`** | **Sprint 1** | `unit_tests/test_models.py` | `models.py:228->230`, `L230` | Kiểm tra nhánh fallback `Room.check_rentability()` khi `status='UNKNOWN_STATE'` → trả `(False, 'Không xác định.')` | **PASS (100% phủ)** |
| **`S2-MOD-045`** | Ngoài Sprint 1 | `unit_tests/test_models.py` | `models.py:329->334`, `331->332`, `L332` | Kiểm tra `MaintenanceRequest.save()` giữ `code='BT0002'` truyền sẵn và tự tăng `idx` lên `BT0003` khi mã tự sinh bị trùng | **PASS (100% phủ)** |
| **`S2-MOD-046`** | Ngoài Sprint 1 | `unit_tests/test_models.py` | `models.py:337`, `L371` | Kiểm tra `__str__()` của `MaintenanceRequest` và `MaintenanceHistory` | **PASS (100% phủ)** |
| **`S2-BIZ-020`** | Ngoài Sprint 1 | `unit_tests/test_services.py` | `views.py:98–107` (`99->100`, `105->107`) | Kiểm tra `_room_status_after_maintenance(req, requested)` với `requested` hợp lệ, `requested='BOGUS'` (`ValidationError`), `previous_room_status`, và `current_occupants` `0`/`1` | **PASS (100% phủ)** |
| **`S2-BIZ-021`** | Ngoài Sprint 1 | `unit_tests/test_services.py` | `views.py:89->90`, `L90` | Kiểm tra `scoped_maintenance(user)` với `ADMIN`, `LANDLORD`, `TENANT` | **PASS (100% phủ)** |
| **`S2-BIZ-022`** | Ngoài Sprint 1 | `unit_tests/test_services.py` | `views.py:589–592`, `646–655` (`647->exit`) | Kiểm tra `MaintenanceRequestViewSet.get_permissions()`, `_set_room_status()` (khi phòng cùng/khác status) và `_ensure_transition()` (khi sai luồng trạng thái) | **PASS (100% phủ)** |
| **`S2-BIZ-023`** | Ngoài Sprint 1 | `unit_tests/test_services.py` | `views.py:657–680` (`671->673`) | Kiểm tra `perform_create()` với phòng ngoài phạm vi (`ValidationError`), quản lý khóa phòng mặc định, và truyền sẵn `reported_by` + `set_room_maintenance='false'` | **PASS (100% phủ)** |
| **`S2-BIZ-024`** | Ngoài Sprint 1 | `unit_tests/test_services.py` | `views.py:682–690` | Kiểm tra `perform_update()` cập nhật hợp lệ (ghi `MaintenanceHistory`) và chặn đổi sang phòng thuộc chủ trọ khác (`ValidationError`) | **PASS (100% phủ)** |
| **`S2-BIZ-025`** | Ngoài Sprint 1 | `unit_tests/test_services.py` | `views.py:695–711`, `762–769` (`702->703`, `705->706`, `706->708`) | Kiểm tra `_do_start()` và action `start()` khi phòng `AVAILABLE` (chưa có / đã có `previous_room_status`) và khi phòng đã ở `MAINTENANCE` | **PASS (100% phủ)** |
| **`S2-BIZ-026`** | Ngoài Sprint 1 | `unit_tests/test_services.py` | `views.py:740–760` (`746->747`, `754->757`, `757->758`, `757->759`) | Kiểm tra `update_status()` với `status='PENDING'` (`400`), `IN_PROGRESS`, `COMPLETED` (có `technician_name`), và `CANCELLED` (không `technician_name`, phòng không ở `MAINTENANCE`) | **PASS (100% phủ)** |
| **`S2-BIZ-027`** | Ngoài Sprint 1 | `unit_tests/test_services.py` | `views.py:771–815` (`778->779`, `782->784`, `784->786`, `786->787`, `808->809`) | Kiểm tra `record_cost()` (chi phí âm → `ValidationError`, payload rỗng `{}`, payload đầy đủ) và `complete()` (chi phí âm → `ValidationError`, hoàn tất hợp lệ) | **PASS (100% phủ)** |
| **`S2-BIZ-028`** | Ngoài Sprint 1 | `unit_tests/test_services.py` | `views.py:817–828` (`823->824`, `L824`) | Kiểm tra nhánh bảo vệ quyền trong `cancel()` khi `TENANT` khác cố hủy (`403 Forbidden`) và khi người báo hủy hợp lệ (`200 OK`) | **PASS (100% phủ)** |
| **`S2-FLT-041`** | Ngoài Sprint 1 | `unit_tests/test_search_filter.py` | `views.py:595–626`, `830–834` | Kiểm tra `GET /api/maintenance/` không lọc & lọc kết hợp `?room_id=&property_id=&status=&priority=&search=` cùng `GET /api/maintenance/{id}/history/` | **PASS (100% phủ)** |
| **`S2-FLT-042`** | Ngoài Sprint 1 | `unit_tests/test_search_filter.py` | `views.py:845–855` (`850->851`, `853->854`) | Kiểm tra `GET /api/maintenance-history/` không lọc và lọc theo `?room_id=&property_id=` | **PASS (100% phủ)** |

---

## 3. Kết luận
- Không còn bất kỳ dòng lệnh (`0/759`) hay nhánh điều kiện (`0/210`) nào chưa được kiểm thử trong toàn bộ `backend/services/property_service/`.
- Không có bất kỳ thay đổi nào đối với source code nghiệp vụ của Service 2 ở bước này, giữ nguyên `SPRINT_FEATURE_LOCK=True` và giữ nguyên toàn bộ `276` test trước đó.

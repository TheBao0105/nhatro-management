# UNIT TEST REPORT — Sprint 1 / Service 2 (Property & Room)

> Báo cáo tổng hợp kết quả kiểm thử **Service 2 — Property & Room** (`backend/services/property_service`) sau khi:
> 1. Khắc phục toàn bộ `BUG-01`..`BUG-05` trong phạm vi Service 2.
> 2. Đạt **100% Statement Coverage (`759/759`)** và **100% Branch Coverage (`210/210`)**.
> 3. Tổ chức tập trung toàn bộ hệ thống kiểm thử vào `backend/services/property_service/testing/`.
> 4. Tinh gọn `35` Legacy tests trong `tests.py` (loại bỏ `29` test trùng lặp hoàn toàn, chuyển `6` test đặc thù sang `testing/`) và tối ưu hóa bộ **Pure Unit Tests** về **`72` Unit Tests chất lượng cao** trong `testing/unit_tests/` (nằm đúng khung mục tiêu `70–90` Unit Tests), tách bạch hoàn toàn với **`135` API / HTTP Tests** trong `testing/api_tests/` (chi tiết xem tại [UNIT_TEST_OPTIMIZATION_REPORT.md](file:///c:/Users/Asus/.gemini/antigravity/scratch/nhatro_management/backend/services/property_service/testing/reports/UNIT_TEST_OPTIMIZATION_REPORT.md) và [LEGACY_TEST_MIGRATION.md](file:///c:/Users/Asus/.gemini/antigravity/scratch/nhatro_management/backend/services/property_service/testing/reports/LEGACY_TEST_MIGRATION.md)).

---

## 1. Tóm tắt kết quả chạy test (`207` Tests = `72` Pure Unit + `135` API/HTTP — 100% PASS)

| Phạm vi chạy | Số lượng Test | PASS | FAIL | ERROR | SKIP | Thời gian |
|---|---:|---:|---:|---:|---:|---|
| **1. Riêng Pure Unit Tests (`testing/unit_tests/` — `--unit-only`)** | **72** | **72** | **0** | **0** | **0** | **`0.28s`** |
| **2. Riêng API / HTTP Tests (`testing/api_tests/` — `--api-only`)** | **135** | **135** | **0** | **0** | **0** | **`1.18s`** |
| **3. Riêng phạm vi Sprint 1 (`--sprint1-only`)** | **188** | **188** | **0** | **0** | **0** | **`1.26s`** |
| **4. Toàn bộ Service 2 (`services.property_service`)** | **207** | **207** | **0** | **0** | **0** | **`2.21s`** *(có coverage)* / **`1.39s`** *(không coverage)* |

### 1.1. Phân bổ 72 Pure Unit Tests (`testing/unit_tests/`) theo Khung Mục Tiêu (`70–90` Unit Tests)

| Module (Pure Unit Test) | File Test | Khung mục tiêu | Số lượng thực tế | Trong Sprint 1 | Ngoài Sprint 1 | PASS |
|---|---|---:|---:|---:|---:|---:|
| **Models** | `testing/unit_tests/test_models.py` (`S2-MOD-001`..`015`) | `12–15` | **15** | `13` | `2` (`014`, `015`) | **15/15** |
| **Serializers** | `testing/unit_tests/test_serializers.py` (`S2-SER-001`..`018`) | `15–20` | **18** | `18` | `0` | **18/18** |
| **Services / Business Logic** | `testing/unit_tests/test_services.py` (`S2-BIZ-001`..`021`) | `20–25` | **21** | `10` | `11` (`011`..`021`) | **21/21** |
| **Permissions (Unit)** | `testing/unit_tests/test_permissions.py` (`S2-PERM-001`..`011`) | `10–15` | **11** | `11` | `0` | **11/11** |
| **Validators / Utilities** | `testing/unit_tests/test_services.py` (`S2-UTL-001`..`007`) | `5–10` | **7** | `7` | `0` | **7/7** |
| **TỔNG PURE UNIT TESTS** | **`4` files trong `testing/unit_tests/`** | **`70–90`** | **72** | **59** | **13** | **72/72** |

### 1.2. Phân loại Ma trận Phạm vi Sprint (Sprint 1 vs Ngoài Sprint 1) × Cấp độ Kiểm thử (Pure Unit vs API/HTTP)

| Phân nhóm | Pure Unit Test (`testing/unit_tests/`) | API / HTTP Test (`testing/api_tests/`) | Tổng số Test | Tỷ lệ PASS |
|---|---:|---:|---:|---:|
| **1. Thuộc phạm vi Sprint 1 (Property, Room, Search/Filter, JWT/RBAC, Feature Lock)** | **59** | **129** | **188** | **188 / 188 (100%)** |
| **2. Ngoài phạm vi Sprint 1 (Maintenance Model/Helper/Filter/HTTP Pipeline)** | **13** | **6** | **19** | **19 / 19 (100%)** |
| **TỔNG TOÀN BỘ SERVICE 2** | **72** | **135** | **207** | **207 / 207 (100%)** |

### 1.3. Kết quả chi tiết theo từng file kiểm thử (`8` files trong `testing/`)

| File Test | Mã Test ID | Tổng test | Thuộc Sprint 1 | Ngoài Sprint 1 | Pure Unit | API/HTTP | PASS | FAIL |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| `testing/unit_tests/test_models.py` | `S2-MOD-001`..`015` | `15` | `13` | `2` (`014`, `015`) | `15` | `0` | **15** | `0` |
| `testing/unit_tests/test_serializers.py` | `S2-SER-001`..`018` | `18` | `18` | `0` | `18` | `0` | **18** | `0` |
| `testing/unit_tests/test_services.py` | `S2-UTL-001`..`007`, `S2-BIZ-001`..`021` | `28` | `17` | `11` (`BIZ-011`..`021`) | `28` | `0` | **28** | `0` |
| `testing/unit_tests/test_permissions.py` | `S2-PERM-001`..`011` | `11` | `11` | `0` | `11` | `0` | **11** | `0` |
| `testing/api_tests/test_views.py` | `S2-API-001`..`063` | `63` | `63` | `0` | `0` | `63` | **63** | `0` |
| `testing/api_tests/test_search_filter.py` | `S2-FLT-001`..`042` | `42` | `40` | `2` (`041`, `042`) | `0` | `42` | **42** | `0` |
| `testing/api_tests/test_permissions_api.py` | `S2-SEC-009`..`034` | `26` | `26` | `0` | `0` | `26` | **26** | `0` |
| `testing/api_tests/test_maintenance_api.py` | `S2-MAPI-001`..`004` | `4` | `0` | `4` (`001`..`004`) | `0` | `4` | **4** | `0` |
| **TỔNG CỘNG** | **`207` Test Cases** | **`207`** | **`188`** | **`19`** | **`72`** | **`135`** | **`207`** | **`0`** |

---

## 2. Kết quả Code Coverage thực tế (`Coverage.py 7.17.4`, `branch = True`)

Bộ **`207` tests** (`72` Pure Unit + `135` API/HTTP) đạt **100% Statement Coverage và 100% Branch Coverage trên toàn bộ 5 file source nghiệp vụ của Service 2**:

| File | Statements | Missed Stmts | Branches | Partial Branches | Statement Coverage | Branch Coverage | Total Coverage | Missing |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| `services/property_service/models.py` | `207` | `0` | `30` | `0` | **100%** | **100%** | **100%** | — |
| `services/property_service/serializers.py` | `85` | `0` | `8` | `0` | **100%** | **100%** | **100%** | — |
| `services/property_service/service_urls.py` | `2` | `0` | `0` | `0` | **100%** | **100%** | **100%** | — |
| `services/property_service/urls.py` | `9` | `0` | `0` | `0` | **100%** | **100%** | **100%** | — |
| `services/property_service/views.py` | `456` | `0` | `172` | `0` | **100%** | **100%** | **100%** | — |
| **TOTAL** | **`759`** | **`0`** | **`210`** | **`0`** | **`100%`** | **`100%`** | **`100%`** | **Không còn dòng hoặc nhánh nào thiếu** |

Báo cáo HTML Coverage và Evidence thực tế:
- HTML Coverage (`207` tests): [../evidence/coverage/index.html](file:///c:/Users/Asus/.gemini/antigravity/scratch/nhatro_management/backend/services/property_service/testing/evidence/coverage/index.html)
- HTML Test Execution Report (`207` tests): [../evidence/TEST_EXECUTION_REPORT.html](file:///c:/Users/Asus/.gemini/antigravity/scratch/nhatro_management/backend/services/property_service/testing/evidence/TEST_EXECUTION_REPORT.html)
- JUnit XML Report (`207` tests): [../evidence/junit-report.xml](file:///c:/Users/Asus/.gemini/antigravity/scratch/nhatro_management/backend/services/property_service/testing/evidence/junit-report.xml)
- Verbose Execution Log (`207` tests): [../evidence/test-execution.log](file:///c:/Users/Asus/.gemini/antigravity/scratch/nhatro_management/backend/services/property_service/testing/evidence/test-execution.log)

---

## 3. Kết luận nghiệm thu Sprint 1

- **Kết luận:** **ĐẠT 100% TIÊU CHÍ KIỂM THỬ SPRINT 1 VÀ 100% COVERAGE TOÀN SERVICE 2** — Bộ kiểm thử sau khi tối ưu gồm **`207/207` tests PASS** (**`72`** Pure Unit Tests trong `testing/unit_tests/` + **`135`** API/HTTP Tests trong `testing/api_tests/`; **`188`** test thuộc phạm vi Sprint 1 + **`19`** test ngoài phạm vi Sprint 1), đạt **100% Statement Coverage (`759/759`)**, **100% Branch Coverage (`210/210`)**, và **100% Total Coverage**.

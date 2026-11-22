# TEST EXECUTION LOG — Sprint 1 / Service 2 (Property & Room)

## 1. Thông tin môi trường thực thi

| Hạng mục | Giá trị quan sát thực tế |
|---|---|
| **Ngày thực hiện** | `2026-11-22` (lần chạy đạt 100% Coverage lúc `09:30` +07:00) |
| **Hệ điều hành** | Windows (`win32`, PowerShell) |
| **Thư mục làm việc** | `C:\Users\Asus\.gemini\antigravity\scratch\nhatro_management\backend` |
| **Môi trường ảo Python** | `backend\venv\Scripts\python.exe` |
| **Phiên bản Python** | `3.13.15` (`tags/v3.13.15:4061bc4`, MSC v.1944 64 bit) |
| **Phiên bản Django** | `6.1.3` |
| **Công cụ Coverage** | `Coverage.py 7.17.4 with C extension` (`backend\.coveragerc`, `branch = True`) |
| **Settings Service 2** | `DJANGO_SETTINGS_MODULE=config.service_settings.property` (`SPRINT_FEATURE_LOCK=True` mặc định) |
| **Database kiểm thử** | `DB_ENGINE=sqlite` (Django in-memory test DB; không chạm SQL Server phát triển) |

---

## 2. Quy trình chạy tự động một lệnh qua `testing/run_tests.ps1` (`2026-11-22 10:00`)

### 2.1. Lệnh thực thi chuẩn

Chạy từ thư mục gốc dự án (`c:\Users\Asus\.gemini\antigravity\scratch\nhatro_management`):
```powershell
.\backend\services\property_service\testing\run_tests.ps1
```
Hoặc chạy trực tiếp từ thư mục `testing`:
```powershell
Set-Location "c:\Users\Asus\.gemini\antigravity\scratch\nhatro_management\backend\services\property_service\testing"
.\run_tests.ps1
```

Script `run_tests.ps1` tự động thực hiện tuần tự 6 bước:
1. Chạy riêng **72 Pure Unit Tests** (`services.property_service.testing.unit_tests` qua `collect_results.py --unit-only`).
2. Chạy riêng **135 API / HTTP Tests** (`services.property_service.testing.api_tests` qua `collect_results.py --api-only`).
3. Chạy toàn bộ **207 Unit & API Tests** (`services.property_service`) dưới `Coverage.py 7.17.4` (`branch = True`) và ghi log chi tiết (`-v 2`) vào `backend/services/property_service/testing/evidence/test-execution.log`.
4. Sinh bảng tổng hợp `coverage report -m` vào `testing/evidence/coverage_full_service2.txt` và báo cáo HTML Coverage vào `testing/evidence/coverage/index.html`.
5. Chạy `testing/tools/collect_results.py` để sinh `testing/reports/results.json`, `testing/reports/UNIT_TEST_CASES.md`, `testing/evidence/TEST_EXECUTION_REPORT.html` và `testing/evidence/junit-report.xml`.
6. Chạy `collect_results.py --sprint1-only` để xác minh độc lập riêng **188 test thuộc phạm vi Sprint 1** (`188/188 PASS`) và tự động xóa file tạm `backend/.coverage`.

### 2.2. Kết quả thực tế từ `run_tests.ps1` (`72` Pure Unit + `135` API/HTTP = `207` tests & `188` tests Sprint 1)

```text
[PURE UNIT TESTS ONLY] Total=72, PASS=72, FAIL/ERROR=0, Duration=0.28s
[API/HTTP TESTS ONLY] Total=135, PASS=135, FAIL/ERROR=0, Duration=1.18s
Ran 207 tests in 2.206s
OK
Name                                        Stmts   Miss Branch BrPart  Cover   Missing
---------------------------------------------------------------------------------------
services\property_service\models.py           207      0     30      0   100%
services\property_service\serializers.py       85      0      8      0   100%
services\property_service\service_urls.py       2      0      0      0   100%
services\property_service\urls.py               9      0      0      0   100%
services\property_service\views.py            456      0    172      0   100%
---------------------------------------------------------------------------------------
TOTAL                                         759      0    210      0   100%
Wrote HTML report to C:\Users\Asus\.gemini\antigravity\scratch\nhatro_management\backend\services\property_service\testing\evidence\coverage\index.html
Summary: Total=207 (PureUnit=72, API/HTTP=135 | Sprint1=188, OutOfSprint1=19), PASS=207, FAIL/ERROR=0, Duration=1.39s
[SPRINT 1 ONLY] Total=188, PASS=188, FAIL/ERROR=0, Duration=1.26s
```

Bằng chứng HTML, JUnit XML và log đã lưu tại:
- [../evidence/coverage/index.html](file:///c:/Users/Asus/.gemini/antigravity/scratch/nhatro_management/backend/services/property_service/testing/evidence/coverage/index.html)
- [../evidence/TEST_EXECUTION_REPORT.html](file:///c:/Users/Asus/.gemini/antigravity/scratch/nhatro_management/backend/services/property_service/testing/evidence/TEST_EXECUTION_REPORT.html)
- [../evidence/junit-report.xml](file:///c:/Users/Asus/.gemini/antigravity/scratch/nhatro_management/backend/services/property_service/testing/evidence/junit-report.xml)
- [../evidence/test-execution.log](file:///c:/Users/Asus/.gemini/antigravity/scratch/nhatro_management/backend/services/property_service/testing/evidence/test-execution.log)
- [../evidence/coverage_full_service2.txt](file:///c:/Users/Asus/.gemini/antigravity/scratch/nhatro_management/backend/services/property_service/testing/evidence/coverage_full_service2.txt)

---

## 3. Lịch sử các đợt chạy trước đó
1. **Đợt 1 (`2026-11-21 18:52` — trước khi sửa 5 bug):** `276` tests (`267` PASS, `9` `expectedFailure` tái hiện `BUG-01`..`BUG-05`), Coverage tổng `93%` (`unit_tests` `75%`).
2. **Đợt 2 (`2026-11-21 19:05` — sau khi sửa `BUG-01`..`BUG-05`):** `276/276` PASS (`0` `expectedFailure`), Coverage tổng `93%` (`36` missed statements, `24` partial branches).
3. **Đợt 3 (`2026-11-22 09:30` — sau khi bổ sung 14 test `S2-MOD-044`..`046`, `S2-BIZ-020`..`028`, `S2-FLT-041`..`042`):** **`290/290` PASS (`0` FAIL, `0` ERROR), Statement Coverage = `100%` (`759/759`), Branch Coverage = `100%` (`210/210`), Total Coverage = `100%`**.

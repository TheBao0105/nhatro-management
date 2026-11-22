# BUG REPORT — Sprint 1 / Service 2 (Property & Room)

> Tổng hợp các lỗi phát hiện qua bộ Unit Test Sprint 1 cho Service 2 (`backend/services/property_service/`) và kết quả xác minh sau khi khắc phục ngày `2026-11-21`.  
> Tất cả **5 bug (`BUG-01`..`BUG-05`)** đã được sửa triệt để trong phạm vi **Service 2** (`models.py` và `views.py`), chuyển toàn bộ **9 test tái hiện** sang **PASS bình thường**. Không sửa Identity, Tenant, Contract, Billing hoặc API Gateway.

---

## 1. Bảng tổng hợp lỗi

| Bug ID | Mô tả lỗi | Mức độ | Bước tái hiện | Trạng thái |
|---|---|---|---|---|
| **BUG-01** | Cho phép nhập và lưu **giá thuê phòng âm** (`rent_price < 0`, vd `-1`, `-100`) qua cả Model, Serializer và API `POST /api/rooms/` | **High** | 1. Tạo JWT của `LANDLORD`/`ADMIN`.<br>2. Gửi `POST /api/rooms/` với `rent_price = -100` hoặc gọi `Room(rent_price=-1).full_clean()`.<br>3. Trước sửa: trả `201` / không báo lỗi. Sau sửa: trả `400 Bad Request` / `ValidationError`. | **Fixed & Verified PASS** *(`S2-MOD-036`, `S2-SER-025`, `S2-API-037`)* |
| **BUG-02** | Cho phép nhập **diện tích phòng âm hoặc bằng 0** (`area <= 0`, vd `0`, `-5`) ở Model và `RoomSerializer` | **High** | 1. Gọi `Room(area=-5).full_clean()` hoặc `RoomSerializer(data={..., 'area': 0}).is_valid()`.<br>2. Trước sửa: chấp nhận hợp lệ. Sau sửa: báo lỗi validation ở `area`. | **Fixed & Verified PASS** *(`S2-MOD-037`, `S2-SER-026`, `S2-SER-027`)* |
| **BUG-03** | Cho phép **đơn giá điện, nước, internet âm** (`electricity_rate`, `water_rate`, `internet_rate` = `-1`) trong `Property` & `PropertySerializer` | **Medium** | 1. Truyền `electricity_rate=-1` / `water_rate=-1` / `internet_rate=-1` vào `PropertySerializer`.<br>2. Trước sửa: `is_valid()` trả `True`. Sau sửa: trả `False` kèm lỗi ở trường tương ứng. | **Fixed & Verified PASS** *(`S2-SER-012`)* |
| **BUG-04** | Cho phép tạo phòng với **sức chứa tối đa bằng 0** (`max_occupants = 0`) | **Medium** | 1. Truyền `max_occupants=0` vào `RoomSerializer` hoặc `POST /api/rooms/`.<br>2. Trước sửa: `PositiveIntegerField` chấp nhận `0`. Sau sửa: yêu cầu tối thiểu `>= 1`. | **Fixed & Verified PASS** *(`S2-SER-029`)* |
| **BUG-05** | Endpoint `GET /api/properties/{id}/rooms/?status=OCCUPIED` trả về **404 Not Found** cho nhà trọ đang `ACTIVE` | **Medium** | 1. Tạo `Property` (`status='ACTIVE'`) có 2 phòng (`AVAILABLE` và `OCCUPIED`).<br>2. Gọi `GET /api/properties/{id}/rooms/?status=occupied`.<br>3. Trước sửa: trả `404`. Sau sửa: trả `200 OK` đúng 1 phòng `OCCUPIED`. | **Fixed & Verified PASS** *(`S2-API-063`)* |

---

## 2. Nguyên nhân gốc & Cách đã khắc phục (trong phạm vi Service 2)

### `BUG-01`: Giá thuê phòng âm (`rent_price < 0`)
- **Nguyên nhân gốc:** Tại `backend/services/property_service/models.py`, trường `Room.rent_price` (và `deposit_amount`) dùng `DecimalField` nhưng chưa gắn `MinValueValidator(0)`, và `RoomSerializer` không chặn giá âm.
- **Cách đã sửa:** Gắn `validators=[MinValueValidator(0)]` cho `Room.rent_price` và `Room.deposit_amount` trong `models.py`. Vì `RoomSerializer` kế thừa từ `ModelSerializer`, validator tự động áp dụng cho cả `Model.full_clean()`, `RoomSerializer` và API `POST`/`PATCH` `/api/rooms/`.
- **Xác minh:** `S2-MOD-036`, `S2-SER-025`, `S2-API-037` đã bỏ `@unittest.expectedFailure` và **PASS**.

### `BUG-02`: Diện tích phòng âm hoặc bằng 0 (`area <= 0`)
- **Nguyên nhân gốc:** `Room.area` trong `backend/services/property_service/models.py` là `FloatField(default=20.0)` chưa có validator kiểm tra giá trị dương `> 0`.
- **Cách đã sửa:** Định nghĩa hàm `validate_positive_area(value)` (lưu ở cấp module để tương thích Django migrations/serialization) ném `ValidationError('Diện tích phòng phải lớn hơn 0.')` khi `value is not None and value <= 0`, và gắn `validators=[validate_positive_area]` vào `Room.area`.
- **Xác minh:** `S2-MOD-037`, `S2-SER-026`, `S2-SER-027` đã bỏ `@unittest.expectedFailure` và **PASS**.

### `BUG-03`: Đơn giá dịch vụ âm trên `Property`
- **Nguyên nhân gốc:** Ba trường `Property.electricity_rate`, `Property.water_rate`, `Property.internet_rate` trong `models.py` dùng `DecimalField` nhưng thiếu `MinValueValidator(0)`.
- **Cách đã sửa:** Gắn `validators=[MinValueValidator(0)]` cho cả 3 trường `electricity_rate`, `water_rate`, `internet_rate` trong `models.py`.
- **Xác minh:** `S2-SER-012` đã bỏ `@unittest.expectedFailure` và **PASS**.

### `BUG-04`: `max_occupants = 0` được chấp nhận
- **Nguyên nhân gốc:** `Room.max_occupants` sử dụng `PositiveIntegerField(default=2)` vốn chấp nhận `0` (`>= 0`) theo mặc định của Django, thiếu ràng buộc `>= 1`.
- **Cách đã sửa:** Gắn `validators=[MinValueValidator(1)]` cho `Room.max_occupants` trong `models.py`.
- **Xác minh:** `S2-SER-029` đã bỏ `@unittest.expectedFailure` và **PASS**.

### `BUG-05`: Xung đột query param `?status=` ở action `GET /api/properties/{id}/rooms/`
- **Nguyên nhân gốc:** Trong `backend/services/property_service/views.py`, hàm `PropertyViewSet.get_queryset()` đọc `params.get('status')` để lọc bảng `Property` bất kể `self.action` là gì. Khi `@action rooms` gọi `self.get_object()`, `Property` đang `ACTIVE` bị loại bởi bộ lọc `Property.status == 'OCCUPIED'` nên trả `404` trước khi chạy tới đoạn lọc `Room` bằng `status_filter`.
- **Cách đã sửa:** Giới hạn điều kiện lọc `status_param` trong `PropertyViewSet.get_queryset()` (`views.py:137`) chỉ áp dụng khi `self.action == 'list'`, giữ nguyên hành vi lọc danh sách nhà trọ đồng thời để `?status=` đi tới `PropertyViewSet.rooms()` lọc phòng bình thường.
- **Xác minh:** `S2-API-063` đã bỏ `@unittest.expectedFailure` và **PASS** (đồng thời nâng độ phủ nhánh `views.py` — dòng `222` không còn miss).

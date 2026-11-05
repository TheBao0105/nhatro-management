# HỆ THỐNG QUẢN LÝ NHÀ TRỌ (MICROSERVICES ARCHITECTURE)

Hệ thống quản lý nhà trọ và phòng trọ chuyên nghiệp với kiến trúc phân tầng Microservices.
- **Frontend**: Flutter (Provider State Management, Material 3, Clean Architecture)
- **Backend**: Django REST Framework + SimpleJWT Authentication
- **Database**: Microsoft SQL Server (mssql-django / pyodbc)

---

## 🏛️ KIẾN TRÚC 5 DỊCH VỤ (5 SERVICES)

| Service | Tên dịch vụ | Vai trò | Trạng thái |
| :--- | :--- | :--- | :--- |
| **SERVICE 1** | **Identity Service** | Đăng nhập JWT, Phân quyền (ADMIN, LANDLORD, STAFF, TENANT), Quản lý hồ sơ | 🟢 **Sprint 1 — Hoàn thành** |
| **SERVICE 2** | **Property & Maintenance** | Quản lý nhà trọ, danh sách phòng, trạng thái phòng (Trống, Đang thuê, Bảo trì, Đã cọc), chỉ số điện nước, phiếu bảo trì | 🟢 **Sprint 1 — Hoàn thành** |
| **SERVICE 3** | **Tenant Service** | Quản lý người thuê, CCCD, thông tin tạm trú, liên hệ khẩn cấp | 🟡 **Sprint 2 — Đã scaffold service & models** |
| **SERVICE 4** | **Contract Service** | Tạo hợp đồng, gia hạn hợp đồng, kết thúc hợp đồng & hoàn cọc | 🟡 **Sprint 2 — Đã scaffold service & models** |
| **SERVICE 5** | **Billing & Notification** | Tính hóa đơn tự động, VietQR thanh toán, thông báo nhắc nợ | ⚪ **Sprint 3 — Đã scaffold service & models** |

---

## 🚀 HƯỚNG DẪN KHỞI CHẠY (QUICK START)

### 1. Khởi chạy Backend (Django + SQL Server)

```bash
cd backend

# Kích hoạt môi trường ảo Python
.\venv\Scripts\Activate.ps1

# Cài đặt thư viện (nếu cần)
pip install -r requirements.txt

# Chạy migrate cơ sở dữ liệu trên SQL Server
python manage.py migrate

# Khởi tạo dữ liệu mẫu (Tài khoản Admin, Chủ trọ, Nhà trọ, Phòng mẫu)
python seed_data.py

# Khởi động Backend API server tại cổng 8000
python manage.py runserver 0.0.0.0:8000
```

> **Swagger UI API Docs**: Truy cập `http://127.0.0.1:8000/api/docs/` để xem và test toàn bộ API endpoints trực tiếp trên trình duyệt.

### 2. Khởi chạy Frontend (Flutter)

```bash
cd frontend

# Lấy dependencies
flutter pub get

# Chạy ứng dụng trên Windows Desktop, Chrome hoặc thiết bị di động
flutter run -d windows
# hoặc chạy Web:
flutter run -d chrome
```

---

## 🔑 TÀI KHOẢN MẪU ĐỂ TEST HỆ THỐNG (ĐÃ SEED SẴN)

| Vai trò (Role) | Username | Password | Quyền hạn |
| :--- | :--- | :--- | :--- |
| **Chủ nhà trọ (LANDLORD)** | `chutro1` | `chutropassword123` | Quản lý toàn bộ nhà trọ và phòng trọ của mình, thay đổi trạng thái phòng |
| **Quản trị viên (ADMIN)** | `admin` | `adminpassword123` | Toàn quyền quản trị hệ thống, người dùng và tất cả nhà trọ |
| **Khách thuê (TENANT)** | `khach1` | `khachpassword123` | Xem thông tin phòng, tiện ích, biểu phí |

---

## 📁 CẤU TRÚC THƯ MỤC

```
nhatro_management/
├── backend/
│   ├── config/                      # Django Settings & Global URL routing & Swagger
│   ├── services/
│   │   ├── identity_service/        # SERVICE 1: Auth & Role-Based Access Control
│   │   ├── property_service/        # SERVICE 2: Nhà trọ & Phòng trọ
│   │   ├── tenant_service/          # SERVICE 3: Khách thuê (Sprint 2)
│   │   ├── contract_service/        # SERVICE 4: Hợp đồng (Sprint 2)
│   │   └── billing_notification_service/ # SERVICE 5: Hóa đơn & Thông báo
│   ├── manage.py
│   ├── seed_data.py                 # Nạp sẵn tài khoản và phòng trọ mẫu
│   └── requirements.txt
└── frontend/                        # Ứng dụng Flutter
    ├── lib/
    │   ├── core/                    # Constants, API Client, Theme, Storage
    │   ├── models/                  # User, Property, Room Models
    │   ├── providers/               # AuthProvider, PropertyProvider
    │   ├── screens/
    │   │   ├── auth/                # Màn hình đăng nhập
    │   │   ├── home/                # Main Navigation Shell
    │   │   ├── property/            # Danh sách & Chi tiết & Thêm/Sửa nhà trọ
    │   │   ├── room/                # Chi tiết & Thêm/Sửa & Đổi trạng thái phòng
    │   │   └── future_services/     # Màn hình lộ trình Sprint 2 & 3
    │   ├── widgets/                 # Badge, StatCard, CustomTextField
    │   └── main.dart
    └── pubspec.yaml
```


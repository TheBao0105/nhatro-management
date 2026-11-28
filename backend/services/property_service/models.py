import builtins
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone


def validate_positive_area(value):
    """Diện tích phòng phải lớn hơn 0 m²."""
    if value is not None and value <= 0:
        raise ValidationError('Diện tích phòng phải lớn hơn 0.')


# ==============================================================================
# I. MODULE PROPERTY — QUẢN LÝ NHÀ TRỌ
# ==============================================================================
class PropertyStatus(models.TextChoices):
    ACTIVE = 'ACTIVE', 'Đang hoạt động'
    INACTIVE = 'INACTIVE', 'Ngừng hoạt động'
    DELETED = 'DELETED', 'Đã xóa (Soft Delete)'


class Property(models.Model):
    """
    SERVICE 2 (PROPERTY & MAINTENANCE SERVICE): Đại diện cho Nhà trọ / Tòa nhà.
    Kiến trúc SOA: Không dùng ForeignKey sang User của Identity Service, chỉ lưu owner_id.
    """
    code = models.CharField(max_length=30, unique=True, blank=True, verbose_name='Mã nhà trọ')
    owner_id = models.IntegerField(default=1, db_index=True, verbose_name='ID Chủ nhà trọ (Identity Service)')
    name = models.CharField(max_length=150, verbose_name='Tên nhà trọ')
    address = models.CharField(max_length=255, verbose_name='Địa chỉ số nhà, tên đường')
    ward = models.CharField(max_length=100, blank=True, default='', verbose_name='Phường / Xã')
    district = models.CharField(max_length=100, blank=True, default='', db_index=True, verbose_name='Quận / Huyện (Khu vực)')
    city = models.CharField(max_length=100, default='TP. Hồ Chí Minh', verbose_name='Tỉnh / Thành phố')
    total_floors = models.PositiveIntegerField(
        default=1, validators=[MinValueValidator(1)], verbose_name='Số tầng',
    )

    electricity_rate = models.DecimalField(
        max_digits=12, decimal_places=0, default=3500,
        validators=[MinValueValidator(0)], verbose_name='Đơn giá điện (VNĐ/kWh)',
    )
    water_rate = models.DecimalField(
        max_digits=12, decimal_places=0, default=20000,
        validators=[MinValueValidator(0)], verbose_name='Đơn giá nước (VNĐ/m³)',
    )
    internet_rate = models.DecimalField(
        max_digits=12, decimal_places=0, default=100000,
        validators=[MinValueValidator(0)], verbose_name='Phí Internet (VNĐ/tháng)',
    )

    description = models.TextField(blank=True, default='', verbose_name='Mô tả nhà trọ')
    rules = models.TextField(blank=True, default='', verbose_name='Nội quy nhà trọ')
    image_url = models.URLField(blank=True, default='', verbose_name='Ảnh đại diện')

    status = models.CharField(
        max_length=20,
        choices=PropertyStatus.choices,
        default=PropertyStatus.ACTIVE,
        db_index=True,
        verbose_name='Trạng thái hoạt động',
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Ngày tạo')
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Nhà trọ'
        verbose_name_plural = 'Danh sách Nhà trọ'
        ordering = ['-created_at']

    @property
    def full_address(self):
        parts = [self.address, self.ward, self.district, self.city]
        return ', '.join([p for p in parts if p])

    @property
    def area_location(self):
        parts = [self.ward, self.district, self.city]
        return ', '.join([p for p in parts if p])

    @property
    def active_rooms_qs(self):
        return self.rooms.exclude(status=RoomStatus.INACTIVE)

    @property
    def total_rooms_count(self):
        return self.rooms.count()

    @property
    def available_rooms_count(self):
        return self.rooms.filter(status=RoomStatus.AVAILABLE).count()

    @property
    def occupied_rooms_count(self):
        return self.rooms.filter(status__in=[RoomStatus.OCCUPIED, RoomStatus.FULL]).count()

    @property
    def full_rooms_count(self):
        return self.rooms.filter(status=RoomStatus.FULL).count()

    @property
    def maintenance_rooms_count(self):
        return self.rooms.filter(status=RoomStatus.MAINTENANCE).count()

    @property
    def inactive_rooms_count(self):
        return self.rooms.filter(status=RoomStatus.INACTIVE).count()

    def save(self, *args, **kwargs):
        if not self.code:
            idx = Property.objects.count() + 1
            while Property.objects.filter(code=f'NT{idx:03d}').exists():
                idx += 1
            self.code = f'NT{idx:03d}'
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.code} - {self.name}"


# ==============================================================================
# II & III. MODULE ROOM & QUẢN LÝ TRẠNG THÁI PHÒNG
# ==============================================================================
class RoomType(models.TextChoices):
    SINGLE = 'SINGLE', 'Phòng tiêu chuẩn / Đơn'
    MEZZANINE = 'MEZZANINE', 'Phòng có gác lửng'
    STUDIO = 'STUDIO', 'Căn hộ mini Studio'
    ONE_BED = 'ONE_BED', 'Căn hộ 1 phòng ngủ'
    DORM = 'DORM', 'Ký túc xá / Giường tầng'


class RoomStatus(models.TextChoices):
    AVAILABLE = 'AVAILABLE', 'Phòng trống'
    OCCUPIED = 'OCCUPIED', 'Đang được thuê'
    FULL = 'FULL', 'Đã đủ số người'
    RESERVED = 'RESERVED', 'Đã đặt cọc'
    MAINTENANCE = 'MAINTENANCE', 'Đang bảo trì'
    INACTIVE = 'INACTIVE', 'Ngừng hoạt động'


# Các trạng thái được tính là "đang có khách thuê".
RENTED_STATUSES = (RoomStatus.OCCUPIED, RoomStatus.FULL)


class Room(models.Model):
    """
    SERVICE 2 (PROPERTY & MAINTENANCE SERVICE): Đại diện cho Phòng trọ.
    Các trạng thái chuẩn:
    1. AVAILABLE   — Phòng trống (có thể cho thuê)
    2. OCCUPIED    — Đang được thuê
    3. FULL        — Đã đủ số người tối đa
    4. RESERVED    — Đã đặt cọc giữ phòng
    5. MAINTENANCE — Đang bảo trì / sửa chữa
    6. INACTIVE    — Ngừng hoạt động (Soft delete / tạm ngưng)
    """
    code = models.CharField(max_length=40, unique=True, blank=True, verbose_name='Mã phòng')
    property = models.ForeignKey(
        Property,
        on_delete=models.CASCADE,
        related_name='rooms',
        verbose_name='Thuộc nhà trọ',
    )
    room_number = models.CharField(max_length=60, verbose_name='Tên / Số phòng')
    floor = models.IntegerField(default=1, verbose_name='Tầng')
    room_type = models.CharField(
        max_length=20,
        choices=RoomType.choices,
        default=RoomType.MEZZANINE,
        verbose_name='Loại phòng',
    )
    area = models.FloatField(default=20.0, validators=[validate_positive_area], verbose_name='Diện tích (m²)')
    rent_price = models.DecimalField(
        max_digits=12, decimal_places=0, validators=[MinValueValidator(0)], verbose_name='Giá thuê (VNĐ/tháng)',
    )
    deposit_amount = models.DecimalField(
        max_digits=12, decimal_places=0, default=0, validators=[MinValueValidator(0)], verbose_name='Tiền cọc (VNĐ)',
    )
    max_occupants = models.PositiveIntegerField(
        default=2, validators=[MinValueValidator(1)], verbose_name='Số người tối đa',
    )
    current_occupants = models.PositiveIntegerField(default=0, verbose_name='Số người đang ở')

    status = models.CharField(
        max_length=20,
        choices=RoomStatus.choices,
        default=RoomStatus.AVAILABLE,
        db_index=True,
        verbose_name='Trạng thái phòng',
    )

    tenant_name = models.CharField(max_length=150, blank=True, null=True, verbose_name='Tên khách đang thuê')
    tenant_phone = models.CharField(max_length=20, blank=True, null=True, verbose_name='SĐT liên hệ')
    amenities = models.CharField(max_length=500, blank=True, default='', verbose_name='Tiện ích phòng')
    description = models.TextField(blank=True, default='', verbose_name='Mô tả chi tiết')

    # Chỉ số công tơ ban đầu (Billing Service dùng làm chỉ số cũ cho hóa đơn đầu tiên).
    initial_electric_reading = models.FloatField(
        default=0.0, validators=[MinValueValidator(0.0)], verbose_name='Chỉ số điện ban đầu',
    )
    initial_water_reading = models.FloatField(
        default=0.0, validators=[MinValueValidator(0.0)], verbose_name='Chỉ số nước ban đầu',
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Ngày tạo')
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Phòng trọ'
        verbose_name_plural = 'Danh sách Phòng trọ'
        ordering = ['property', 'floor', 'room_number']
        constraints = [
            models.UniqueConstraint(
                fields=['property', 'room_number'],
                name='unique_room_number_per_property',
            ),
        ]

    @builtins.property
    def is_rentable(self):
        """3.3 Kiểm tra phòng có thể thuê hay không."""
        if self.property.status != PropertyStatus.ACTIVE:
            return False
        return self.status == RoomStatus.AVAILABLE

    def check_rentability(self):
        """Trả về (can_rent: bool, reason: str)."""
        if self.property.status != PropertyStatus.ACTIVE:
            return False, f'Nhà trọ "{self.property.name}" đang ở trạng thái {self.property.get_status_display()}.'
        if self.status == RoomStatus.AVAILABLE:
            return True, 'Phòng đang trống và đủ điều kiện cho thuê ngay.'
        if self.status == RoomStatus.OCCUPIED:
            remaining = max(0, self.max_occupants - self.current_occupants)
            return False, f'Phòng đang được thuê ({self.current_occupants}/{self.max_occupants} người, còn {remaining} chỗ trống).'
        if self.status == RoomStatus.FULL:
            return False, f'Phòng đã đủ số người tối đa ({self.max_occupants}/{self.max_occupants} người).'
        if self.status == RoomStatus.RESERVED:
            return False, 'Phòng đã được đặt cọc giữ chỗ.'
        if self.status == RoomStatus.MAINTENANCE:
            return False, 'Phòng đang trong quá trình bảo trì / sửa chữa, không thể sử dụng.'
        if self.status == RoomStatus.INACTIVE:
            return False, 'Phòng đang ngừng hoạt động.'
        return False, 'Không xác định.'

    def save(self, *args, **kwargs):
        if not self.code:
            prop_code = self.property.code if self.property_id else 'NT'
            clean_num = ''.join(ch for ch in str(self.room_number).upper() if ch.isalnum()) or 'P'
            base_code = f'{prop_code}-{clean_num}'
            candidate = base_code
            idx = 1
            while Room.objects.filter(code=candidate).exclude(pk=self.pk).exists():
                idx += 1
                candidate = f'{base_code}-{idx}'
            self.code = candidate
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.code} ({self.room_number})"


# ==============================================================================
# VII. MODULE MAINTENANCE — QUẢN LÝ BẢO TRÌ / SỬA CHỮA
# ==============================================================================
class MaintenanceStatus(models.TextChoices):
    PENDING = 'PENDING', 'Chờ xử lý'
    IN_PROGRESS = 'IN_PROGRESS', 'Đang sửa chữa'
    COMPLETED = 'COMPLETED', 'Đã hoàn thành'
    CANCELLED = 'CANCELLED', 'Đã hủy'


class MaintenancePriority(models.TextChoices):
    LOW = 'LOW', 'Thấp'
    MEDIUM = 'MEDIUM', 'Trung bình'
    HIGH = 'HIGH', 'Cao'
    URGENT = 'URGENT', 'Khẩn cấp'


class MaintenanceRequest(models.Model):
    """
    7.1 -> 7.7: Yêu cầu bảo trì / sửa chữa thiết bị và cơ sở vật chất phòng trọ.
    Luồng trạng thái: PENDING -> IN_PROGRESS -> COMPLETED (hoặc CANCELLED).
    """
    code = models.CharField(max_length=30, unique=True, blank=True, verbose_name='Mã yêu cầu')
    room = models.ForeignKey(
        Room,
        on_delete=models.CASCADE,
        related_name='maintenance_requests',
        verbose_name='Phòng cần bảo trì',
    )
    title = models.CharField(max_length=200, verbose_name='Tiêu đề sự cố')
    description = models.TextField(blank=True, default='', verbose_name='Mô tả chi tiết')
    repair_info = models.TextField(blank=True, default='', verbose_name='Thông tin / Nội dung sửa chữa')

    priority = models.CharField(
        max_length=15,
        choices=MaintenancePriority.choices,
        default=MaintenancePriority.MEDIUM,
        verbose_name='Mức độ ưu tiên',
    )
    status = models.CharField(
        max_length=20,
        choices=MaintenanceStatus.choices,
        default=MaintenanceStatus.PENDING,
        db_index=True,
        verbose_name='Trạng thái bảo trì',
    )

    estimated_cost = models.DecimalField(
        max_digits=12, decimal_places=0, default=0,
        validators=[MinValueValidator(0)], verbose_name='Chi phí dự kiến (VNĐ)',
    )
    actual_cost = models.DecimalField(
        max_digits=12, decimal_places=0, default=0,
        validators=[MinValueValidator(0)], verbose_name='Chi phí thực tế (VNĐ)',
    )

    reported_by = models.CharField(max_length=150, blank=True, default='Chủ trọ / Quản lý', verbose_name='Người báo cáo')
    # ID tài khoản người báo (Identity Service) — dùng để phân quyền, không phải FK chéo service.
    reported_by_id = models.IntegerField(null=True, blank=True, db_index=True,
                                         verbose_name='ID Người báo (Identity Service)')
    technician_name = models.CharField(max_length=150, blank=True, default='', verbose_name='Thợ / Đơn vị sửa chữa')
    # Trạng thái phòng trước khi khóa để bảo trì (khôi phục khi hoàn thành/hủy).
    previous_room_status = models.CharField(max_length=20, choices=RoomStatus.choices, blank=True, null=True,
                                            verbose_name='Trạng thái phòng trước bảo trì')

    requested_date = models.DateField(default=timezone.localdate, verbose_name='Ngày yêu cầu')
    started_at = models.DateTimeField(null=True, blank=True, verbose_name='Thời điểm bắt đầu xử lý')
    completed_date = models.DateField(null=True, blank=True, verbose_name='Ngày hoàn thành')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Yêu cầu bảo trì'
        verbose_name_plural = 'Danh sách Yêu cầu bảo trì'
        ordering = ['-created_at']

    @builtins.property
    def is_open(self):
        return self.status in (MaintenanceStatus.PENDING, MaintenanceStatus.IN_PROGRESS)

    def save(self, *args, **kwargs):
        if not self.code:
            idx = MaintenanceRequest.objects.count() + 1
            while MaintenanceRequest.objects.filter(code=f'BT{idx:04d}').exists():
                idx += 1
            self.code = f'BT{idx:04d}'
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.code} - {self.title}"


class MaintenanceHistory(models.Model):
    """
    7.8: Lịch sử bảo trì — Theo dõi các lần sửa chữa, ngày sửa chữa, chi phí,
    trạng thái và nội dung sửa chữa.
    """
    maintenance_request = models.ForeignKey(
        MaintenanceRequest,
        on_delete=models.CASCADE,
        related_name='histories',
        verbose_name='Yêu cầu bảo trì',
    )
    room = models.ForeignKey(
        Room,
        on_delete=models.CASCADE,
        related_name='maintenance_histories',
        verbose_name='Phòng',
    )
    action = models.CharField(max_length=120, verbose_name='Hành động / Lần cập nhật')
    previous_status = models.CharField(max_length=20, blank=True, default='', verbose_name='Trạng thái trước')
    new_status = models.CharField(max_length=20, blank=True, default='', verbose_name='Trạng thái mới')
    cost = models.DecimalField(max_digits=12, decimal_places=0, default=0, verbose_name='Chi phí (VNĐ)')
    repair_content = models.TextField(blank=True, default='', verbose_name='Nội dung sửa chữa')
    performed_by = models.CharField(max_length=150, blank=True, default='Quản lý hệ thống', verbose_name='Người thực hiện')
    repair_date = models.DateTimeField(default=timezone.now, verbose_name='Ngày giờ ghi nhận')

    class Meta:
        verbose_name = 'Lịch sử bảo trì'
        verbose_name_plural = 'Lịch sử bảo trì'
        ordering = ['-repair_date', '-id']

    def __str__(self):
        return f"{self.maintenance_request.code} - {self.action}"

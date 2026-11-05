from django.db import models
from django.conf import settings

class Property(models.Model):
    """
    SERVICE 2: Đại diện cho Nhà trọ / Tòa nhà cho thuê
    """
    landlord = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='properties',
        verbose_name='Chủ nhà trọ'
    )
    name = models.CharField(max_length=150, verbose_name='Tên nhà trọ')
    address = models.CharField(max_length=255, verbose_name='Địa chỉ số nhà, tên đường')
    ward = models.CharField(max_length=100, blank=True, null=True, verbose_name='Phường / Xã')
    district = models.CharField(max_length=100, blank=True, null=True, verbose_name='Quận / Huyện')
    city = models.CharField(max_length=100, default='Hồ Chí Minh', verbose_name='Tỉnh / Thành phố')
    total_floors = models.PositiveIntegerField(default=1, verbose_name='Số tầng')
    
    # Giá dịch vụ cơ sở
    electricity_rate = models.DecimalField(
        max_digits=12, decimal_places=2, default=3500.0, verbose_name='Đơn giá điện (VNĐ/kWh)'
    )
    water_rate = models.DecimalField(
        max_digits=12, decimal_places=2, default=20000.0, verbose_name='Đơn giá nước (VNĐ/m3)'
    )
    internet_rate = models.DecimalField(
        max_digits=12, decimal_places=2, default=100000.0, verbose_name='Phí Internet (VNĐ/phòng/tháng)'
    )

    description = models.TextField(blank=True, null=True, verbose_name='Mô tả tiện ích chung')
    rules = models.TextField(blank=True, null=True, verbose_name='Nội quy nhà trọ')
    image_url = models.URLField(blank=True, null=True, verbose_name='Ảnh đại diện nhà trọ')

    created_at = models.DateTimeField(auto_now_add=True)
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
    def total_rooms_count(self):
        return self.rooms.count()

    @property
    def available_rooms_count(self):
        return self.rooms.filter(status=RoomStatus.AVAILABLE).count()

    @property
    def occupied_rooms_count(self):
        return self.rooms.filter(status=RoomStatus.OCCUPIED).count()

    def __str__(self):
        return f"{self.name} - {self.full_address}"


class RoomStatus(models.TextChoices):
    AVAILABLE = 'AVAILABLE', 'Còn trống'
    OCCUPIED = 'OCCUPIED', 'Đang thuê'
    MAINTENANCE = 'MAINTENANCE', 'Đang bảo trì / sửa chữa'
    RESERVED = 'RESERVED', 'Đã đặt cọc'


class Room(models.Model):
    """
    SERVICE 2: Đại diện cho Phòng trọ
    """
    property = models.ForeignKey(
        Property,
        on_delete=models.CASCADE,
        related_name='rooms',
        verbose_name='Thuộc nhà trọ'
    )
    room_number = models.CharField(max_length=50, verbose_name='Số phòng / Mã phòng')
    floor = models.IntegerField(default=1, verbose_name='Tầng')
    area = models.FloatField(default=20.0, verbose_name='Diện tích (m²)')
    rent_price = models.DecimalField(
        max_digits=12, decimal_places=2, verbose_name='Giá thuê (VNĐ/tháng)'
    )
    deposit_amount = models.DecimalField(
        max_digits=12, decimal_places=2, default=0.0, verbose_name='Tiền cọc (VNĐ)'
    )
    max_occupants = models.PositiveIntegerField(default=2, verbose_name='Số người ở tối đa')
    status = models.CharField(
        max_length=20,
        choices=RoomStatus.choices,
        default=RoomStatus.AVAILABLE,
        verbose_name='Trạng thái phòng'
    )
    amenities = models.CharField(
        max_length=500,
        blank=True,
        null=True,
        verbose_name='Tiện nghi phòng',
        help_text='VD: Máy lạnh, Gác lửng, Tủ lạnh, Tủ quần áo, Nước nóng...'
    )
    description = models.TextField(blank=True, null=True, verbose_name='Ghi chú phòng')

    initial_electric_reading = models.FloatField(default=0.0, verbose_name='Chỉ số điện ban đầu')
    initial_water_reading = models.FloatField(default=0.0, verbose_name='Chỉ số nước ban đầu')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Phòng trọ'
        verbose_name_plural = 'Danh sách Phòng trọ'
        unique_together = ('property', 'room_number')
        ordering = ['floor', 'room_number']

    def __str__(self):
        return f"{self.property.name} - Phòng {self.room_number} ({self.get_status_display()})"


class MaintenancePriority(models.TextChoices):
    LOW = 'LOW', 'Thấp'
    MEDIUM = 'MEDIUM', 'Trung bình'
    HIGH = 'HIGH', 'Cao'
    URGENT = 'URGENT', 'Khẩn cấp'


class MaintenanceStatus(models.TextChoices):
    PENDING = 'PENDING', 'Chờ xử lý'
    IN_PROGRESS = 'IN_PROGRESS', 'Đang xử lý'
    RESOLVED = 'RESOLVED', 'Đã hoàn thành'
    CANCELLED = 'CANCELLED', 'Đã hủy'


class MaintenanceRequest(models.Model):
    """
    SERVICE 2: Phiếu yêu cầu sửa chữa / bảo trì cơ sở vật chất
    """
    property = models.ForeignKey(
        Property, on_delete=models.CASCADE, related_name='maintenance_requests'
    )
    room = models.ForeignKey(
        Room, on_delete=models.SET_NULL, null=True, blank=True, related_name='maintenance_requests'
    )
    reported_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='reported_maintenances'
    )
    title = models.CharField(max_length=200, verbose_name='Tiêu đề sự cố')
    description = models.TextField(verbose_name='Mô tả chi tiết sự cố')
    priority = models.CharField(
        max_length=20,
        choices=MaintenancePriority.choices,
        default=MaintenancePriority.MEDIUM
    )
    status = models.CharField(
        max_length=20,
        choices=MaintenanceStatus.choices,
        default=MaintenanceStatus.PENDING
    )
    cost = models.DecimalField(
        max_digits=12, decimal_places=2, default=0.0, verbose_name='Chi phí sửa chữa (VNĐ)'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Yêu cầu bảo trì'
        verbose_name_plural = 'Danh sách Yêu cầu bảo trì'
        ordering = ['-created_at']

    def __str__(self):
        return f"[{self.get_status_display()}] {self.title} - {self.property.name}"


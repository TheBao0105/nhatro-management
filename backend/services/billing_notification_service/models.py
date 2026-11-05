from django.db import models
from django.conf import settings
from services.property_service.models import Room
from services.contract_service.models import Contract

class InvoiceStatus(models.TextChoices):
    UNPAID = 'UNPAID', 'Chưa thanh toán'
    PAID = 'PAID', 'Đã thanh toán'
    OVERDUE = 'OVERDUE', 'Quá hạn'
    CANCELLED = 'CANCELLED', 'Đã hủy'


class Invoice(models.Model):
    """
    SERVICE 5 — BILLING SERVICE (Sẵn sàng cho Sprint 3)
    Hóa đơn tiền phòng và dịch vụ điện nước
    """
    invoice_code = models.CharField(max_length=50, unique=True, verbose_name='Mã hóa đơn')
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name='invoices')
    contract = models.ForeignKey(Contract, on_delete=models.CASCADE, related_name='invoices', null=True, blank=True)
    billing_month = models.PositiveIntegerField(verbose_name='Tháng')
    billing_year = models.PositiveIntegerField(verbose_name='Năm')

    room_fee = models.DecimalField(max_digits=12, decimal_places=2, verbose_name='Tiền phòng')
    electricity_old_num = models.FloatField(default=0.0, verbose_name='Chỉ số điện cũ')
    electricity_new_num = models.FloatField(default=0.0, verbose_name='Chỉ số điện mới')
    electricity_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0.0, verbose_name='Tiền điện')

    water_old_num = models.FloatField(default=0.0, verbose_name='Chỉ số nước cũ')
    water_new_num = models.FloatField(default=0.0, verbose_name='Chỉ số nước mới')
    water_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0.0, verbose_name='Tiền nước')

    other_service_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0.0, verbose_name='Phí dịch vụ khác')
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, verbose_name='Tổng cộng phải thanh toán')

    status = models.CharField(
        max_length=20,
        choices=InvoiceStatus.choices,
        default=InvoiceStatus.UNPAID,
        verbose_name='Trạng thái thanh toán'
    )
    due_date = models.DateField(verbose_name='Hạn thanh toán')
    paid_at = models.DateTimeField(null=True, blank=True, verbose_name='Thời điểm thanh toán')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Hóa đơn dịch vụ'
        verbose_name_plural = 'Danh sách Hóa đơn dịch vụ'
        ordering = ['-created_at']

    def __str__(self):
        return f"Hóa đơn {self.invoice_code} - Phòng {self.room.room_number} (T{self.billing_month}/{self.billing_year})"


class Notification(models.Model):
    """
    SERVICE 5 — NOTIFICATION SERVICE
    Hệ thống thông báo đẩy tới người dùng
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=200, verbose_name='Tiêu đề thông báo')
    content = models.TextField(verbose_name='Nội dung thông báo')
    is_read = models.BooleanField(default=False, verbose_name='Đã xem')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Thông báo'
        verbose_name_plural = 'Danh sách Thông báo'
        ordering = ['-created_at']

    def __str__(self):
        return f"Thông báo: {self.title} -> {self.user.username}"


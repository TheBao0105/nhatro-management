from django.db import models

class ContractStatus(models.TextChoices):
    DRAFT = 'DRAFT', 'Bản nháp'
    ACTIVE = 'ACTIVE', 'Đang hiệu lực'
    EXTENDED = 'EXTENDED', 'Đã gia hạn'
    EXPIRED = 'EXPIRED', 'Đã hết hạn'
    TERMINATED = 'TERMINATED', 'Đã kết thúc / Chấm dứt'


class Contract(models.Model):
    """
    SERVICE 4 — CONTRACT SERVICE (Lộ trình hoàn thành trong Sprint 2)
    Hợp đồng thuê trọ.
    Kiến trúc SOA: Loose coupling lưu room_id, landlord_id, tenant_id.
    """
    contract_number = models.CharField(max_length=50, unique=True, verbose_name='Mã hợp đồng')
    room_id = models.IntegerField(verbose_name='ID Phòng (Property Service)')
    landlord_id = models.IntegerField(verbose_name='ID Chủ trọ (Identity Service)')
    tenant_id = models.IntegerField(verbose_name='ID Khách thuê (Identity Service)')

    start_date = models.DateField(verbose_name='Ngày bắt đầu thuê')
    end_date = models.DateField(verbose_name='Ngày kết thúc hợp đồng')

    rental_price = models.DecimalField(max_digits=12, decimal_places=2, verbose_name='Giá thuê hàng tháng (VNĐ)')
    deposit_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.0, verbose_name='Tiền cọc giữ chỗ (VNĐ)')
    billing_day_of_month = models.PositiveIntegerField(default=5, verbose_name='Ngày thu tiền hàng tháng')

    status = models.CharField(
        max_length=20,
        choices=ContractStatus.choices,
        default=ContractStatus.ACTIVE,
        verbose_name='Trạng thái hợp đồng'
    )
    terms_and_conditions = models.TextField(blank=True, null=True, verbose_name='Điều khoản hợp đồng')
    contract_file_url = models.URLField(blank=True, null=True, verbose_name='File hợp đồng scan/PDF')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Hợp đồng thuê'
        verbose_name_plural = 'Danh sách Hợp đồng thuê'
        ordering = ['-created_at']

    def __str__(self):
        return f"HĐ {self.contract_number} (Phòng ID #{self.room_id})"

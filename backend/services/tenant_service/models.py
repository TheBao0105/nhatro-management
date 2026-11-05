from django.db import models
from django.conf import settings
from services.property_service.models import Room

class TenantProfile(models.Model):
    """
    SERVICE 3 — TENANT SERVICE (Sẵn sàng cho Sprint 2)
    Hồ sơ chi tiết của khách thuê trọ
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='tenant_profile',
        verbose_name='Tài khoản người dùng'
    )
    current_room = models.ForeignKey(
        Room,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='current_tenants',
        verbose_name='Phòng đang ở'
    )
    birth_date = models.DateField(null=True, blank=True, verbose_name='Ngày sinh')
    gender = models.CharField(max_length=10, blank=True, null=True, verbose_name='Giới tính')
    hometown = models.CharField(max_length=150, blank=True, null=True, verbose_name='Quê quán')
    occupation = models.CharField(max_length=150, blank=True, null=True, verbose_name='Nghề nghiệp / Đơn vị công tác')
    emergency_contact_name = models.CharField(max_length=100, blank=True, null=True, verbose_name='Người liên hệ khẩn cấp')
    emergency_contact_phone = models.CharField(max_length=20, blank=True, null=True, verbose_name='SĐT khẩn cấp')
    temporary_residence_registered = models.BooleanField(default=False, verbose_name='Đã đăng ký tạm trú')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Hồ sơ người thuê'
        verbose_name_plural = 'Danh sách Hồ sơ người thuê'

    def __str__(self):
        return f"Khách thuê: {self.user.full_name} ({self.user.phone_number})"


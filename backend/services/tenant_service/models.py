from django.db import models

class TenantProfile(models.Model):
    """
    SERVICE 3 — TENANT SERVICE (Lộ trình hoàn thành trong Sprint 2)
    Hồ sơ chi tiết của khách thuê trọ.
    Kiến trúc SOA: Lưu user_id và room_id dạng số nguyên, không dùng Foreign Key chéo service.
    """
    user_id = models.IntegerField(unique=True, verbose_name='ID Tài khoản (Identity Service)')
    room_id = models.IntegerField(null=True, blank=True, verbose_name='ID Phòng (Property Service)')
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
        return f"Hồ sơ khách thuê User ID #{self.user_id}"

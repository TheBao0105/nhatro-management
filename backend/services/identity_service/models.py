from django.contrib.auth.models import AbstractUser
from django.db import models

class UserRole(models.TextChoices):
    ADMIN = 'ADMIN', 'Quản trị viên'
    LANDLORD = 'LANDLORD', 'Chủ nhà trọ'
    STAFF = 'STAFF', 'Quản lý / Nhân viên'
    TENANT = 'TENANT', 'Khách thuê'

class User(AbstractUser):
    role = models.CharField(
        max_length=20,
        choices=UserRole.choices,
        default=UserRole.LANDLORD,
        help_text='Phân quyền tài khoản trong hệ thống'
    )
    phone_number = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        verbose_name='Số điện thoại'
    )
    identity_card = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        verbose_name='Số CCCD / CMND'
    )
    address = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name='Địa chỉ thường trú'
    )
    avatar_url = models.URLField(
        blank=True,
        null=True,
        verbose_name='Ảnh đại diện'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Người dùng'
        verbose_name_plural = 'Danh sách Người dùng'
        ordering = ['-date_joined']

    @property
    def full_name(self):
        full = f"{self.first_name} {self.last_name}".strip()
        return full if full else self.username

    @property
    def is_admin_role(self):
        return self.role == UserRole.ADMIN or self.is_superuser

    @property
    def is_landlord_role(self):
        return self.role == UserRole.LANDLORD

    @property
    def is_staff_role(self):
        return self.role == UserRole.STAFF

    @property
    def is_tenant_role(self):
        return self.role == UserRole.TENANT

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"


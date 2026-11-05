from rest_framework import permissions
from .models import UserRole

class IsAdminUserRole(permissions.BasePermission):
    """
    Cho phép chỉ Quản trị viên (ADMIN hoặc superuser) truy cập.
    """
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and (request.user.role == UserRole.ADMIN or request.user.is_superuser))

class IsLandlordOrAdmin(permissions.BasePermission):
    """
    Cho phép Chủ nhà trọ (LANDLORD) hoặc Quản trị viên (ADMIN) truy cập.
    """
    def has_permission(self, request, view):
        return bool(
            request.user and 
            request.user.is_authenticated and 
            (request.user.role in [UserRole.ADMIN, UserRole.LANDLORD] or request.user.is_superuser)
        )

class IsStaffOrLandlordOrAdmin(permissions.BasePermission):
    """
    Cho phép Nhân viên, Chủ trọ hoặc Admin.
    """
    def has_permission(self, request, view):
        return bool(
            request.user and 
            request.user.is_authenticated and 
            (request.user.role in [UserRole.ADMIN, UserRole.LANDLORD, UserRole.STAFF] or request.user.is_superuser)
        )


from rest_framework import generics, viewsets, permissions, status
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView
from django.contrib.auth import get_user_model
from .models import UserRole
from .serializers import (
    UserSerializer,
    RegisterSerializer,
    CustomTokenObtainPairSerializer,
)
from .permissions import IsAdminUserRole, IsLandlordOrAdmin

User = get_user_model()

class CustomLoginView(TokenObtainPairView):
    """
    SERVICE 1 — IDENTITY: Đăng nhập hệ thống trả về JWT Token và thông tin phân quyền
    """
    serializer_class = CustomTokenObtainPairSerializer

class RegisterView(generics.CreateAPIView):
    """
    SERVICE 1 — IDENTITY: Đăng ký tài khoản (mặc định là LANDLORD)
    """
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]

class CurrentUserView(generics.RetrieveUpdateAPIView):
    """
    SERVICE 1 — IDENTITY: Lấy & cập nhật thông tin cá nhân của người dùng hiện tại
    """
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user

class UserViewSet(viewsets.ModelViewSet):
    """
    SERVICE 1 — IDENTITY: Quản lý danh sách người dùng và phân quyền (ADMIN / LANDLORD)
    """
    serializer_class = UserSerializer
    permission_classes = [IsLandlordOrAdmin]

    def get_queryset(self):
        user = self.request.user
        role_filter = self.request.query_params.get('role')
        queryset = User.objects.all()

        if role_filter:
            queryset = queryset.filter(role=role_filter)

        # Nếu là Landlord thông thường, chỉ xem danh sách khách thuê (TENANT) hoặc chính mình
        if user.role == UserRole.LANDLORD and not user.is_superuser:
            queryset = queryset.filter(role=UserRole.TENANT) | User.objects.filter(id=user.id)

        return queryset


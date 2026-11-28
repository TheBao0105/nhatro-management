from rest_framework import generics, viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.http import Http404

from common import service_client
from .models import UserRole
from .serializers import (
    UserSerializer,
    ProfileSerializer,
    RegisterSerializer,
    CustomTokenObtainPairSerializer,
    CustomTokenRefreshSerializer,
    ChangePasswordSerializer,
    LogoutSerializer,
)
from .permissions import IsAdminUserRole, IsLandlordOrAdmin

User = get_user_model()

class CustomLoginView(TokenObtainPairView):
    """
    SERVICE 1 — IDENTITY: Đăng nhập hệ thống trả về JWT Token và thông tin phân quyền
    """
    serializer_class = CustomTokenObtainPairSerializer


class CustomTokenRefreshView(TokenRefreshView):
    """
    SERVICE 1 — IDENTITY: Làm mới JWT Access/Refresh Token và đồng bộ lại claims từ DB
    """
    serializer_class = CustomTokenRefreshSerializer

class RegisterView(generics.CreateAPIView):
    """
    SERVICE 1 — IDENTITY: Đăng ký tài khoản (mặc định là LANDLORD)
    """
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]

class CurrentUserView(generics.RetrieveUpdateAPIView):
    """
    SERVICE 1 — IDENTITY: Lấy & cập nhật thông tin cá nhân của người dùng hiện tại.
    Dùng ProfileSerializer: không cho tự đổi role / is_active / username.
    """
    serializer_class = ProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        if isinstance(self.request.user, User):
            return self.request.user
        return User.objects.get(pk=self.request.user.id)

class LogoutView(APIView):
    """
    SERVICE 1 — IDENTITY: Đăng xuất — thu hồi (blacklist) refresh token.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = LogoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            token = RefreshToken(serializer.validated_data['refresh'])
            if str(token.get('user_id')) != str(request.user.id):
                return Response({'error': 'Refresh token không thuộc về người dùng hiện tại.'},
                                status=status.HTTP_400_BAD_REQUEST)
            token.blacklist()
        except TokenError as exc:
            return Response({'error': str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'detail': 'Đăng xuất thành công.'}, status=status.HTTP_200_OK)


class ChangePasswordView(APIView):
    """
    SERVICE 1 — IDENTITY: Đổi mật khẩu người dùng hiện tại và thu hồi các refresh token cũ.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        user = request.user if isinstance(request.user, User) else User.objects.get(pk=request.user.id)
        user.set_password(serializer.validated_data['new_password'])
        user.save(update_fields=['password'])
        for outstanding in OutstandingToken.objects.filter(user=user):
            BlacklistedToken.objects.get_or_create(token=outstanding)
        return Response({'detail': 'Đổi mật khẩu thành công.'}, status=status.HTTP_200_OK)


class UserViewSet(viewsets.ModelViewSet):
    """
    SERVICE 1 — IDENTITY: Quản lý danh sách người dùng và phân quyền (ADMIN / LANDLORD)
    - ADMIN    : toàn quyền (tạo/sửa/xóa, đổi role, khóa tài khoản)
    - LANDLORD : chỉ xem/sửa thông tin liên hệ của TENANT thuộc phạm vi nhà trọ của mình
                 (tài khoản có hồ sơ người thuê do mình quản lý ở Tenant Service, chưa chuyển đi)
                 + chính mình; tạo tài khoản TENANT; không được đổi role/is_active, không được xóa.
    - STAFF (legacy) / TENANT: không truy cập.
    """
    serializer_class = UserSerializer
    permission_classes = [IsLandlordOrAdmin]

    def get_permissions(self):
        if self.action == 'destroy':
            return [IsAdminUserRole()]
        return super().get_permissions()

    def perform_destroy(self, instance):
        if instance.pk == self.request.user.pk:
            from rest_framework.exceptions import ValidationError
            raise ValidationError({'detail': 'Không thể tự xóa tài khoản của chính mình.'})
        instance.delete()

    def _landlord_tenant_user_ids(self):
        """
        user_id các TENANT thuộc phạm vi chủ trọ: lấy từ Tenant Service (/api/tenants/links/) bằng JWT
        của chính chủ trọ -> Tenant Service chỉ trả hồ sơ có landlord_id = chủ trọ này.
        Tenant Service lỗi -> 503 (không mặc định cho phép).
        """
        links = service_client.fetch_tenant_links(service_client.auth_header_from_request(self.request))
        return {int(link['user_id']) for link in links
                if link.get('user_id') and link.get('status') != service_client.MOVED_OUT_STATUS}

    @action(detail=True, methods=['get'], url_path='tenant-link-eligibility')
    def tenant_link_eligibility(self, request, pk=None):
        """
        Tenant Service gọi (bằng JWT của ADMIN/LANDLORD) trước khi gắn user_id vào hồ sơ người thuê.
        Chỉ trả về một giá trị boolean — không lộ username/role/thông tin cá nhân của tài khoản ngoài phạm vi.
        eligible = tài khoản tồn tại, role TENANT, đang hoạt động, không phải superuser.
        ADMIN / LANDLORD / STAFF (legacy) không bao giờ được liên kết thành hồ sơ người thuê.
        """
        try:
            user_id = int(pk)
        except (TypeError, ValueError):
            raise Http404
        account = User.objects.filter(pk=user_id).first()
        eligible = bool(account and account.role == UserRole.TENANT and account.is_active
                        and not account.is_superuser)
        return Response({'user_id': user_id, 'eligible': eligible})

    def get_queryset(self):
        user = self.request.user
        role_filter = self.request.query_params.get('role')
        queryset = User.objects.all()

        if not (user.is_superuser or user.role == UserRole.ADMIN):
            # LANDLORD: chỉ TENANT trong phạm vi nhà trọ của mình + chính mình.
            queryset = queryset.filter(
                Q(role=UserRole.TENANT, id__in=self._landlord_tenant_user_ids()) | Q(id=user.id))

        if role_filter and role_filter != 'ALL':
            queryset = queryset.filter(role=role_filter.upper())

        return queryset


class TestAccountsView(generics.GenericAPIView):
    """
    DEV ONLY: danh sách tài khoản mẫu (do seed_data.py tạo) để đăng nhập nhanh khi phát triển.
    - Chỉ bật khi DEBUG=True (hoặc EXPOSE_TEST_ACCOUNTS=True); production trả 404.
    - Không bao giờ công bố tài khoản ADMIN.
    """
    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    def get(self, request):
        if not getattr(settings, 'EXPOSE_TEST_ACCOUNTS', settings.DEBUG):
            raise Http404
        return Response({
            'message': 'Tài khoản mẫu cho môi trường phát triển (seed_data.py). Không dùng ở production.',
            'test_accounts': [
                {'username': 'chutro1', 'password': 'chutropassword123', 'role': 'LANDLORD', 'name': 'Chủ trọ Nguyễn Văn An'},
                {'username': 'khach1', 'password': 'khachpassword123', 'role': 'TENANT', 'name': 'Khách thuê Trần Thị Mai'},
            ]
        })


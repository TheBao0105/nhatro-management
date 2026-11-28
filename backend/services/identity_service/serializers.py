from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer, TokenRefreshSerializer
from rest_framework_simplejwt.settings import api_settings

from .models import UserRole

User = get_user_model()

USER_FIELDS = [
    'id',
    'username',
    'email',
    'first_name',
    'last_name',
    'full_name',
    'role',
    'role_display',
    'phone_number',
    'identity_card',
    'address',
    'avatar_url',
    'is_active',
    'created_at',
    'updated_at',
]


def _is_admin(user):
    return bool(user and user.is_authenticated and (user.is_superuser or user.role == UserRole.ADMIN))


class UserSerializer(serializers.ModelSerializer):
    """
    Quản lý tài khoản (/api/users/) — chỉ ADMIN hoặc LANDLORD truy cập (xem UserViewSet).

    Chính sách phân quyền (kiểm tra ở backend, không tin dữ liệu client):
    - ADMIN    : tạo/sửa mọi tài khoản, được đổi `role` và `is_active`.
    - LANDLORD : chỉ được tạo tài khoản TENANT; không được đổi `role`/`is_active`
                 của bất kỳ ai (kể cả chính mình).
    """
    role_display = serializers.CharField(source='get_role_display', read_only=True)
    full_name = serializers.CharField(read_only=True)
    password = serializers.CharField(write_only=True, required=False, min_length=6,
                                     style={'input_type': 'password'})

    class Meta:
        model = User
        fields = USER_FIELDS + ['password']
        read_only_fields = ['id', 'created_at', 'updated_at']

    def _requester(self):
        request = self.context.get('request')
        return getattr(request, 'user', None)

    def validate_password(self, value):
        validate_password(value)
        return value

    def validate_email(self, value):
        value = (value or '').strip()
        if value:
            dup_qs = User.objects.filter(email__iexact=value)
            if self.instance is not None:
                dup_qs = dup_qs.exclude(pk=self.instance.pk)
            if dup_qs.exists():
                raise serializers.ValidationError('Email đã được sử dụng.')
        return value

    def validate(self, attrs):
        requester = self._requester()
        # STAFF chỉ còn để tương thích dữ liệu cũ: không ai được cấp mới vai trò này.
        new_role = attrs.get('role')
        if new_role == UserRole.STAFF and (self.instance is None or self.instance.role != UserRole.STAFF):
            raise serializers.ValidationError(
                {'role': 'Vai trò STAFF đã ngừng sử dụng. Chọn ADMIN, LANDLORD hoặc TENANT.'})
        if _is_admin(requester):
            if self.instance is None and not attrs.get('password'):
                raise serializers.ValidationError({'password': 'Cần đặt mật khẩu cho tài khoản mới.'})
            if self.instance is not None and requester and self.instance.pk == requester.pk:
                if 'is_active' in attrs and attrs['is_active'] is False:
                    raise serializers.ValidationError({'is_active': 'Không thể tự khóa tài khoản của chính mình.'})
                if 'role' in attrs and attrs['role'] != self.instance.role:
                    raise serializers.ValidationError({'role': 'Không thể tự hạ quyền tài khoản của chính mình.'})
            return attrs

        if self.instance is None:
            # LANDLORD tạo tài khoản: chỉ TENANT, luôn active.
            role = attrs.get('role', UserRole.TENANT)
            if role != UserRole.TENANT:
                raise serializers.ValidationError({'role': 'Chủ trọ chỉ được tạo tài khoản Khách thuê (TENANT).'})
            attrs['role'] = UserRole.TENANT
            if attrs.get('is_active') is False:
                raise serializers.ValidationError({'is_active': 'Chỉ Quản trị viên được khóa tài khoản.'})
            attrs.pop('is_active', None)
            if not attrs.get('password'):
                raise serializers.ValidationError({'password': 'Cần đặt mật khẩu cho tài khoản mới.'})
        else:
            if 'role' in attrs and attrs['role'] != self.instance.role:
                raise serializers.ValidationError({'role': 'Chỉ Quản trị viên được thay đổi vai trò.'})
            if 'is_active' in attrs and attrs['is_active'] != self.instance.is_active:
                raise serializers.ValidationError({'is_active': 'Chỉ Quản trị viên được khóa/mở khóa tài khoản.'})
            if 'password' in attrs:
                raise serializers.ValidationError(
                    {'password': 'Không thể đặt mật khẩu cho tài khoản khác. Dùng chức năng đổi mật khẩu.'})
        return attrs

    def create(self, validated_data):
        password = validated_data.pop('password')
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user

    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        instance = super().update(instance, validated_data)
        if password:
            instance.set_password(password)
            instance.save(update_fields=['password'])
        return instance


class ProfileSerializer(serializers.ModelSerializer):
    """
    Hồ sơ của chính người dùng (/api/auth/me/).
    Người dùng KHÔNG được tự đổi username, role (tự nâng quyền) hay is_active.
    """
    role_display = serializers.CharField(source='get_role_display', read_only=True)
    full_name = serializers.CharField(read_only=True)

    class Meta:
        model = User
        fields = USER_FIELDS
        read_only_fields = ['id', 'username', 'role', 'is_active', 'created_at', 'updated_at']

    def validate_email(self, value):
        value = (value or '').strip()
        if value:
            dup_qs = User.objects.filter(email__iexact=value)
            if self.instance is not None:
                dup_qs = dup_qs.exclude(pk=self.instance.pk)
            if dup_qs.exists():
                raise serializers.ValidationError('Email đã được sử dụng.')
        return value


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6)

    class Meta:
        model = User
        fields = [
            'username',
            'password',
            'email',
            'first_name',
            'last_name',
            'role',
            'phone_number',
            'identity_card',
            'address',
        ]

    # Đăng ký công khai không được tự cấp quyền ADMIN/STAFF.
    PUBLIC_ROLES = (UserRole.LANDLORD, UserRole.TENANT)

    def validate_role(self, value):
        if value and value not in self.PUBLIC_ROLES:
            raise serializers.ValidationError('Chỉ được đăng ký vai trò LANDLORD hoặc TENANT.')
        return value

    def validate_password(self, value):
        validate_password(value)
        return value

    def validate_email(self, value):
        # Email không bắt buộc; nếu có thì không được trùng (không phân biệt hoa/thường).
        value = (value or '').strip()
        if not value:
            return value
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError('Email đã được sử dụng.')
        return value

    def create(self, validated_data):
        password = validated_data.pop('password')
        # Mặc định người dùng đăng ký ngoài là LANDLORD nếu không chọn
        if not validated_data.get('role'):
            validated_data['role'] = UserRole.LANDLORD
        # Không bao giờ cấp quyền quản trị qua đăng ký công khai.
        validated_data['is_staff'] = False
        validated_data['is_superuser'] = False

        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Kèm thông tin User và Phân quyền trực tiếp trong response Login.
    Đồng thời nhúng claims (username, role, full_name, is_superuser) vào JWT để các service
    khác xác thực STATELESS mà không cần truy cập database của Identity Service.
    """
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['username'] = user.username
        token['role'] = user.role
        token['is_superuser'] = bool(user.is_superuser)
        token['is_staff'] = bool(user.is_staff)
        token['full_name'] = user.full_name
        return token

    def validate(self, attrs):
        data = super().validate(attrs)
        user = self.user
        data['user'] = {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'full_name': user.full_name,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'role': user.role,
            'role_display': user.get_role_display(),
            'phone_number': user.phone_number,
            'identity_card': user.identity_card,
            'address': user.address,
            'avatar_url': user.avatar_url,
        }
        return data


class CustomTokenRefreshSerializer(TokenRefreshSerializer):
    """
    Làm mới JWT (/api/auth/refresh/):
    - Xử lý an toàn User.DoesNotExist thành AuthenticationFailed (401) thay vì 500 khi tài khoản đã bị xóa
      hoặc thiếu claim user_id.
    - Đồng bộ lại claims (username, role, is_superuser, is_staff, full_name) từ DB hiện tại vào token mới
      để các service stateless (Service 2–5) luôn nhận đúng quyền mới nhất.
    """
    def validate(self, attrs):
        refresh = self.token_class(attrs['refresh'])
        user_id = refresh.payload.get(api_settings.USER_ID_CLAIM, None)
        user = User.objects.filter(**{api_settings.USER_ID_FIELD: user_id}).first() if user_id is not None else None
        if user is None or not api_settings.USER_AUTHENTICATION_RULE(user):
            raise AuthenticationFailed(
                self.error_messages['no_active_account'],
                'no_active_account',
            )
        refresh['username'] = user.username
        refresh['role'] = user.role
        refresh['is_superuser'] = bool(user.is_superuser)
        refresh['is_staff'] = bool(user.is_staff)
        refresh['full_name'] = user.full_name
        return super().validate({'refresh': str(refresh)})


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, min_length=6)

    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError('Mật khẩu hiện tại không đúng.')
        return value

    def validate(self, attrs):
        if attrs['old_password'] == attrs['new_password']:
            raise serializers.ValidationError({'new_password': 'Mật khẩu mới phải khác mật khẩu hiện tại.'})
        validate_password(attrs['new_password'], self.context['request'].user)
        return attrs


class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField()

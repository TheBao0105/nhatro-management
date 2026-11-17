from django.contrib.auth import get_user_model, password_validation
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer, TokenRefreshSerializer
from rest_framework_simplejwt.settings import api_settings
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.utils import get_md5_hash_password

from .models import UserRole

User = get_user_model()


def validate_new_password(password, user):
    try:
        password_validation.validate_password(password, user)
    except DjangoValidationError as exc:
        raise serializers.ValidationError(list(exc.messages)) from exc


class UserSerializer(serializers.ModelSerializer):
    role_display = serializers.CharField(source='get_role_display', read_only=True)
    full_name = serializers.CharField(read_only=True)

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name', 'full_name',
            'role', 'role_display', 'phone_number', 'identity_card', 'address',
            'avatar_url', 'is_active', 'is_admin_role', 'created_at', 'updated_at',
        ]
        read_only_fields = fields


class ProfileSerializer(UserSerializer):
    class Meta(UserSerializer.Meta):
        read_only_fields = [
            'id', 'username', 'role', 'role_display', 'full_name', 'is_active', 'is_admin_role',
            'created_at', 'updated_at',
        ]

    def validate(self, attrs):
        forbidden = {'role', 'is_active', 'is_superuser', 'is_staff', 'password', 'username'}
        errors = {key: 'Không được thay đổi trường này qua hồ sơ cá nhân.'
                  for key in forbidden.intersection(self.initial_data)}
        if errors:
            raise serializers.ValidationError(errors)
        return attrs


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, trim_whitespace=False)
    password_confirm = serializers.CharField(write_only=True, trim_whitespace=False)

    class Meta:
        model = User
        fields = ['username', 'password', 'password_confirm', 'email', 'first_name',
                  'last_name', 'phone_number', 'identity_card', 'address']

    def validate(self, attrs):
        if self.initial_data.get('role', UserRole.LANDLORD) != UserRole.LANDLORD:
            raise serializers.ValidationError({'role': 'Đăng ký công khai chỉ tạo tài khoản chủ trọ.'})
        if any(key in self.initial_data for key in ('is_staff', 'is_superuser', 'is_active')):
            raise serializers.ValidationError('Không được tự gán quyền tài khoản.')
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({'password_confirm': 'Mật khẩu xác nhận không khớp.'})
        try:
            validate_new_password(attrs['password'], User(**{
                key: value for key, value in attrs.items()
                if key not in ('password', 'password_confirm')
            }))
        except serializers.ValidationError as exc:
            raise serializers.ValidationError({'password': exc.detail}) from exc
        return attrs

    def create(self, validated_data):
        validated_data.pop('password_confirm')
        return User.objects.create_user(role=UserRole.LANDLORD, **validated_data)


class AdminUserSerializer(UserSerializer):
    password = serializers.CharField(write_only=True, required=False, trim_whitespace=False)

    class Meta(UserSerializer.Meta):
        fields = UserSerializer.Meta.fields + ['password']
        read_only_fields = ['id', 'role_display', 'full_name', 'is_admin_role', 'created_at', 'updated_at']

    def validate(self, attrs):
        if self.instance is None and not attrs.get('password'):
            raise serializers.ValidationError({'password': 'Cần mật khẩu để tạo tài khoản.'})
        if attrs.get('password') is not None:
            candidate = User(**{key: attrs.get(key, getattr(self.instance, key, ''))
                                for key in ('username', 'email', 'first_name', 'last_name')})
            try:
                validate_new_password(attrs['password'], candidate)
            except serializers.ValidationError as exc:
                raise serializers.ValidationError({'password': exc.detail}) from exc
        if self.instance:
            request = self.context['request']
            protected = self.instance.is_superuser or self.instance.pk == request.user.pk
            if protected and (attrs.get('is_active') is False or
                              attrs.get('role', self.instance.role) != self.instance.role):
                raise serializers.ValidationError('Không thể tự khóa/đổi quyền của mình hoặc tài khoản superuser.')
        return attrs

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)

    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        for key, value in validated_data.items():
            setattr(instance, key, value)
        if password is not None:
            instance.set_password(password)
        instance.save()
        return instance


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True, trim_whitespace=False)
    new_password = serializers.CharField(write_only=True, trim_whitespace=False)
    password_confirm = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate(self, attrs):
        user = self.context['request'].user
        if not user.check_password(attrs['old_password']):
            raise serializers.ValidationError({'old_password': 'Mật khẩu hiện tại không đúng.'})
        if attrs['new_password'] != attrs['password_confirm']:
            raise serializers.ValidationError({'password_confirm': 'Mật khẩu xác nhận không khớp.'})
        if attrs['old_password'] == attrs['new_password']:
            raise serializers.ValidationError({'new_password': 'Mật khẩu mới phải khác mật khẩu hiện tại.'})
        try:
            validate_new_password(attrs['new_password'], user)
        except serializers.ValidationError as exc:
            raise serializers.ValidationError({'new_password': exc.detail}) from exc
        return attrs


class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField(write_only=True, trim_whitespace=False)


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)
        data['user'] = UserSerializer(self.user).data
        return data


class CustomTokenRefreshSerializer(TokenRefreshSerializer):
    def validate(self, attrs):
        token = RefreshToken(attrs['refresh'])
        user = User.objects.filter(pk=token.get(api_settings.USER_ID_CLAIM)).first()
        if user is None or not user.is_active:
            raise AuthenticationFailed('Tài khoản không còn hoạt động.')
        if api_settings.CHECK_REVOKE_TOKEN and token.get(api_settings.REVOKE_TOKEN_CLAIM) != get_md5_hash_password(user.password):
            raise AuthenticationFailed('Mật khẩu đã thay đổi. Vui lòng đăng nhập lại.')
        return super().validate(attrs)

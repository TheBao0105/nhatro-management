from unittest import mock

import requests
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from rest_framework_simplejwt.tokens import AccessToken
from common.testing import fake_http_response, tenant_link
from services.identity_service.models import UserRole
from services.identity_service.serializers import CustomTokenObtainPairSerializer

User = get_user_model()

class IdentityServiceTests(TestCase):
    databases = {'default'}

    def setUp(self):
        self.client = APIClient()
        self.landlord = User.objects.create_user(
            username='testlandlord',
            password='testpassword123',
            email='landlord@test.com',
            role=UserRole.LANDLORD,
            first_name='An',
            last_name='Nguyen'
        )

    def test_login_success(self):
        """SPRINT 1: Test Login API & JWT Authentication"""
        response = self.client.post('/api/auth/login/', {
            'username': 'testlandlord',
            'password': 'testpassword123'
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)
        self.assertIn('user', response.data)
        self.assertEqual(response.data['user']['role'], UserRole.LANDLORD)

    def test_login_invalid_credentials(self):
        """SPRINT 1: Test Login thất bại khi sai mật khẩu"""
        response = self.client.post('/api/auth/login/', {
            'username': 'testlandlord',
            'password': 'wrongpassword'
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_role_authorization_and_me(self):
        """SPRINT 1: Test Role Authorization & Me endpoint"""
        self.client.force_authenticate(user=self.landlord)
        response = self.client.get('/api/auth/me/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['username'], 'testlandlord')
        self.assertEqual(response.data['role'], UserRole.LANDLORD)

    def _login(self):
        return self.client.post('/api/auth/login/', {
            'username': 'testlandlord', 'password': 'testpassword123'}, format='json').data

    def test_jwt_contains_role_claims_for_stateless_services(self):
        """Token phải mang role để service khác phân quyền không cần DB Identity"""
        token = AccessToken(self._login()['access'])
        self.assertEqual(token['role'], UserRole.LANDLORD)
        self.assertEqual(token['username'], 'testlandlord')
        self.assertFalse(token['is_superuser'])

    def test_logout_blacklists_refresh_token(self):
        data = self._login()
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {data['access']}")
        res = self.client.post('/api/auth/logout/', {'refresh': data['refresh']}, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        res = self.client.post('/api/auth/refresh/', {'refresh': data['refresh']}, format='json')
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_change_password(self):
        self.client.force_authenticate(user=self.landlord)
        res = self.client.post('/api/auth/change-password/', {
            'old_password': 'wrong', 'new_password': 'newpass123'}, format='json')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        res = self.client.post('/api/auth/change-password/', {
            'old_password': 'testpassword123', 'new_password': 'newpass123'}, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.landlord.refresh_from_db()
        self.assertTrue(self.landlord.check_password('newpass123'))

    def test_public_register_cannot_create_admin(self):
        res = self.client.post('/api/auth/register/', {
            'username': 'hacker', 'password': 'abcdef12', 'role': UserRole.ADMIN}, format='json')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_health(self):
        res = self.client.get('/health/')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['status'], 'UP')
        self.assertEqual(res.data['port'], 8001)


class IdentityPermissionPolicyTests(TestCase):
    """Chống leo quyền: role / is_active chỉ ADMIN được thay đổi."""
    databases = {'default'}

    def setUp(self):
        self.admin = User.objects.create_user(username='admin_t', password='adminpass123', role=UserRole.ADMIN)
        self.landlord = User.objects.create_user(username='landlord_t', password='landlordpass123',
                                                 role=UserRole.LANDLORD)
        self.tenant = User.objects.create_user(username='tenant_t', password='tenantpass123', role=UserRole.TENANT)
        self.client = APIClient()
        # Tenant Service (giả lập): tenant_t là người thuê thuộc phạm vi của landlord_t.
        patcher = mock.patch('common.service_client.fetch_tenant_links',
                             return_value=[tenant_link(1, self.tenant.id, room_id=1, landlord_id=self.landlord.id)])
        patcher.start()
        self.addCleanup(patcher.stop)

    def as_user(self, user):
        self.client.force_authenticate(user=user)
        return self.client

    def test_user_cannot_escalate_own_role_or_activate_flag_via_me(self):
        client = self.as_user(self.tenant)
        res = client.patch('/api/auth/me/', {'role': UserRole.ADMIN, 'is_active': False,
                                             'username': 'renamed', 'phone_number': '0909'}, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.tenant.refresh_from_db()
        self.assertEqual(self.tenant.role, UserRole.TENANT)
        self.assertTrue(self.tenant.is_active)
        self.assertEqual(self.tenant.username, 'tenant_t')
        self.assertEqual(self.tenant.phone_number, '0909')

    def test_tenant_cannot_access_user_management(self):
        client = self.as_user(self.tenant)
        self.assertEqual(client.get('/api/users/').status_code, status.HTTP_403_FORBIDDEN)
        res = client.post('/api/users/', {'username': 'x', 'password': 'abcdef12', 'role': UserRole.ADMIN},
                          format='json')
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_landlord_can_only_create_tenant(self):
        client = self.as_user(self.landlord)
        res = client.post('/api/users/', {'username': 'evil', 'password': 'abcdef12', 'role': UserRole.ADMIN},
                          format='json')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(User.objects.filter(username='evil').exists())
        res = client.post('/api/users/', {'username': 'newtenant', 'password': 'abcdef12'}, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED, res.data)
        created = User.objects.get(username='newtenant')
        self.assertEqual(created.role, UserRole.TENANT)
        self.assertTrue(created.check_password('abcdef12'))
        self.assertNotIn('password', res.data)

    def test_landlord_cannot_change_role_or_deactivate(self):
        client = self.as_user(self.landlord)
        res = client.patch(f'/api/users/{self.tenant.id}/', {'role': UserRole.ADMIN}, format='json')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        res = client.patch(f'/api/users/{self.tenant.id}/', {'is_active': False}, format='json')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        res = client.patch(f'/api/users/{self.landlord.id}/', {'role': UserRole.ADMIN}, format='json')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        # Không thấy / không sửa được tài khoản ADMIN
        res = client.patch(f'/api/users/{self.admin.id}/', {'first_name': 'x'}, format='json')
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(client.delete(f'/api/users/{self.tenant.id}/').status_code, status.HTTP_403_FORBIDDEN)
        self.tenant.refresh_from_db()
        self.assertEqual(self.tenant.role, UserRole.TENANT)
        self.assertTrue(self.tenant.is_active)

    def test_admin_can_change_role_and_deactivate(self):
        client = self.as_user(self.admin)
        res = client.patch(f'/api/users/{self.tenant.id}/', {'role': UserRole.LANDLORD, 'is_active': False},
                           format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK, res.data)
        self.tenant.refresh_from_db()
        self.assertEqual(self.tenant.role, UserRole.LANDLORD)
        self.assertFalse(self.tenant.is_active)
        self.assertEqual(client.delete(f'/api/users/{self.admin.id}/').status_code, status.HTTP_400_BAD_REQUEST)

    def test_public_register_cannot_create_staff_or_superuser(self):
        anon = APIClient()
        for role in (UserRole.ADMIN, UserRole.STAFF):
            res = anon.post('/api/auth/register/', {'username': f'r_{role}', 'password': 'abcdef12', 'role': role},
                            format='json')
            self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        res = anon.post('/api/auth/register/', {'username': 'r_ok', 'password': 'abcdef12',
                                                'is_superuser': True, 'is_staff': True}, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        user = User.objects.get(username='r_ok')
        self.assertFalse(user.is_superuser)
        self.assertFalse(user.is_staff)
        self.assertEqual(user.role, UserRole.LANDLORD)

    def test_test_accounts_endpoint_hidden_when_not_debug(self):
        from django.test import override_settings
        with override_settings(EXPOSE_TEST_ACCOUNTS=False):
            self.assertEqual(APIClient().get('/api/auth/test-users/').status_code, status.HTTP_404_NOT_FOUND)
        with override_settings(EXPOSE_TEST_ACCOUNTS=True):
            res = APIClient().get('/api/auth/test-users/')
            self.assertEqual(res.status_code, status.HTTP_200_OK)
            self.assertNotIn('ADMIN', [a['role'] for a in res.data['test_accounts']])


class PublicRegisterTests(TestCase):
    """Chặng 3 — Đăng ký công khai POST /api/auth/register/ (màn hình RegisterPage)."""
    databases = {'default'}
    URL = '/api/auth/register/'

    def setUp(self):
        self.client = APIClient()
        User.objects.create_user(username='dangco', password='abcdef12', email='dangco@test.vn')

    def _post(self, **data):
        return self.client.post(self.URL, data, format='json')

    def test_register_landlord_success_hashes_password(self):
        res = self._post(username='chumoi', password='abcdef12', email='chumoi@test.vn', first_name='Nguyễn Văn',
                         last_name='B', phone_number='0901234567', role=UserRole.LANDLORD)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED, res.data)
        self.assertNotIn('password', res.data)
        user = User.objects.get(username='chumoi')
        self.assertEqual(user.role, UserRole.LANDLORD)
        self.assertNotEqual(user.password, 'abcdef12')
        self.assertTrue(user.check_password('abcdef12'))
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertEqual(user.phone_number, '0901234567')

    def test_register_tenant_success_and_can_login(self):
        res = self._post(username='khachmoi', password='abcdef12', role=UserRole.TENANT)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED, res.data)
        self.assertEqual(User.objects.get(username='khachmoi').role, UserRole.TENANT)
        login = self.client.post('/api/auth/login/', {'username': 'khachmoi', 'password': 'abcdef12'}, format='json')
        self.assertEqual(login.status_code, status.HTTP_200_OK)
        self.assertEqual(login.data['user']['role'], UserRole.TENANT)

    def test_register_duplicate_username(self):
        res = self._post(username='dangco', password='abcdef12')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('username', res.data)
        self.assertEqual(User.objects.filter(username='dangco').count(), 1)

    def test_register_duplicate_email_case_insensitive(self):
        res = self._post(username='nguoikhac', password='abcdef12', email='DangCo@Test.vn')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('email', res.data)
        self.assertFalse(User.objects.filter(username='nguoikhac').exists())

    def test_register_without_email_allowed_multiple_times(self):
        for name in ('khongmail1', 'khongmail2'):
            self.assertEqual(self._post(username=name, password='abcdef12').status_code, status.HTTP_201_CREATED)

    def test_register_invalid_password_and_email(self):
        res = self._post(username='ngan', password='abc')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('password', res.data)
        res = self._post(username='saimail', password='abcdef12', email='khong-phai-email')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('email', res.data)
        self.assertFalse(User.objects.filter(username__in=['ngan', 'saimail']).exists())

    def test_register_admin_staff_rejected(self):
        for role in (UserRole.ADMIN, UserRole.STAFF):
            res = self._post(username=f'tu_{role.lower()}', password='abcdef12', role=role)
            self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertIn('role', res.data)
        self.assertFalse(User.objects.filter(username__startswith='tu_').exists())


class IdentityRoleScopeTests(TestCase):
    """W1 (STAFF) + W2 (LANDLORD chỉ quản lý TENANT thuộc phạm vi nhà trọ của mình)."""
    databases = {'default'}

    def setUp(self):
        self.admin = User.objects.create_user(username='a1', password='adminpass123', role=UserRole.ADMIN)
        self.landlord = User.objects.create_user(username='l1', password='landlordpass1', role=UserRole.LANDLORD)
        self.other_landlord = User.objects.create_user(username='l2', password='landlordpass2', role=UserRole.LANDLORD)
        self.my_tenant = User.objects.create_user(username='t_mine', password='tenantpass1', role=UserRole.TENANT)
        self.other_tenant = User.objects.create_user(username='t_other', password='tenantpass2', role=UserRole.TENANT)
        self.moved_tenant = User.objects.create_user(username='t_moved', password='tenantpass3', role=UserRole.TENANT)
        self.staff = User.objects.create_user(username='s1', password='staffpass123', role=UserRole.STAFF)
        # Liên kết do Tenant Service trả về cho chủ trọ l1 (đã lọc theo landlord_id ở Tenant Service).
        self.links = [
            tenant_link(10, self.my_tenant.id, room_id=1, landlord_id=self.landlord.id),
            tenant_link(11, self.moved_tenant.id, room_id=2, landlord_id=self.landlord.id, status='MOVED_OUT'),
            # user_id trỏ tới LANDLORD khác: không bao giờ được coi là TENANT trong phạm vi.
            tenant_link(12, self.other_landlord.id, room_id=3, landlord_id=self.landlord.id),
        ]

    def bearer(self, user):
        client = APIClient()
        token = CustomTokenObtainPairSerializer.get_token(user).access_token
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        return client

    def test_landlord_lists_only_own_tenants_and_self(self):
        with mock.patch('common.service_client.requests.get',
                        return_value=fake_http_response(200, self.links)) as fake:
            res = self.bearer(self.landlord).get('/api/users/')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(sorted(u['username'] for u in res.data), ['l1', 't_mine'])
        # Gọi đúng Tenant Service bằng JWT của chính chủ trọ (không dùng ID từ client).
        self.assertEqual(fake.call_args.args[0], 'http://127.0.0.1:8003/api/tenants/links/')
        self.assertTrue(fake.call_args.kwargs['headers']['Authorization'].startswith('Bearer '))

    def test_landlord_cannot_read_or_edit_tenant_out_of_scope(self):
        with mock.patch('common.service_client.requests.get', return_value=fake_http_response(200, self.links)):
            client = self.bearer(self.landlord)
            for user in (self.other_tenant, self.moved_tenant, self.other_landlord, self.admin, self.staff):
                self.assertEqual(client.get(f'/api/users/{user.id}/').status_code, status.HTTP_404_NOT_FOUND)
                res = client.patch(f'/api/users/{user.id}/', {'first_name': 'Hack'}, format='json')
                self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)
            res = client.patch(f'/api/users/{self.my_tenant.id}/', {'phone_number': '0911'}, format='json')
            self.assertEqual(res.status_code, status.HTTP_200_OK, res.data)
        self.other_tenant.refresh_from_db()
        self.assertEqual(self.other_tenant.first_name, '')

    def test_tenant_service_down_fails_closed_503(self):
        with mock.patch('common.service_client.requests.get', side_effect=requests.exceptions.ConnectionError()):
            res = self.bearer(self.landlord).get('/api/users/')
        self.assertEqual(res.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
        with mock.patch('common.service_client.requests.get', return_value=fake_http_response(500, None)):
            res = self.bearer(self.landlord).get(f'/api/users/{self.my_tenant.id}/')
        self.assertEqual(res.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)

    def test_admin_sees_whole_system_without_tenant_lookup(self):
        with mock.patch('common.service_client.requests.get') as fake:
            res = self.bearer(self.admin).get('/api/users/')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), User.objects.count())
        fake.assert_not_called()

    def test_staff_has_no_admin_or_manager_rights(self):
        client = self.bearer(self.staff)
        self.assertEqual(client.get('/api/users/').status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(client.get(f'/api/users/{self.my_tenant.id}/').status_code, status.HTTP_403_FORBIDDEN)
        res = client.post('/api/users/', {'username': 'x', 'password': 'abcdef12', 'role': 'ADMIN'}, format='json')
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(client.delete(f'/api/users/{self.my_tenant.id}/').status_code, status.HTTP_403_FORBIDDEN)
        # Không tự nâng quyền qua hồ sơ cá nhân.
        client.patch('/api/auth/me/', {'role': 'ADMIN', 'is_active': True}, format='json')
        self.staff.refresh_from_db()
        self.assertEqual(self.staff.role, UserRole.STAFF)

    def test_staff_role_cannot_be_newly_assigned(self):
        client = self.bearer(self.admin)
        res = client.post('/api/users/', {'username': 'new_s', 'password': 'abcdef12', 'role': 'STAFF'}, format='json')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        res = client.patch(f'/api/users/{self.my_tenant.id}/', {'role': 'STAFF'}, format='json')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        # Dữ liệu STAFF cũ vẫn giữ nguyên; ADMIN chuyển được STAFF sang vai trò chính thức.
        res = client.patch(f'/api/users/{self.staff.id}/', {'role': 'LANDLORD'}, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK, res.data)

    def test_unauthenticated_401(self):
        self.assertEqual(APIClient().get('/api/users/').status_code, status.HTTP_401_UNAUTHORIZED)

    def test_tenant_link_eligibility_only_boolean_for_active_tenant(self):
        inactive = User.objects.create_user(username='t_off', password='tenantpass4', role=UserRole.TENANT,
                                            is_active=False)
        expected = {self.other_tenant.id: True, self.my_tenant.id: True, inactive.id: False,
                    self.admin.id: False, self.landlord.id: False, self.other_landlord.id: False,
                    self.staff.id: False, 999999: False}
        for caller in (self.admin, self.landlord):
            client = self.bearer(caller)
            with mock.patch('common.service_client.requests.get') as fake:
                for uid, ok in expected.items():
                    res = client.get(f'/api/users/{uid}/tenant-link-eligibility/')
                    self.assertEqual(res.status_code, status.HTTP_200_OK)
                    self.assertEqual(res.data, {'user_id': uid, 'eligible': ok})  # không lộ username/role
            fake.assert_not_called()
        for caller in (self.my_tenant, self.staff):
            res = self.bearer(caller).get(f'/api/users/{self.other_tenant.id}/tenant-link-eligibility/')
            self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
        res = APIClient().get(f'/api/users/{self.other_tenant.id}/tenant-link-eligibility/')
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(self.bearer(self.admin).get('/api/users/not-an-int/tenant-link-eligibility/').status_code,
                         status.HTTP_404_NOT_FOUND)


class IdentityUnitTests(TestCase):
    """[PURE UNIT TEST] Kiểm thử trực tiếp Model User, Permissions và Serializers của Service 1 (không qua HTTP)."""
    databases = {'default'}

    def setUp(self):
        self.admin = User.objects.create_user(
            username='u_admin', password='adminpass123', email='admin@unit.vn',
            role=UserRole.ADMIN, first_name='Quản', last_name='Trị',
        )
        self.landlord = User.objects.create_user(
            username='u_landlord', password='landlordpass123', email='landlord@unit.vn',
            role=UserRole.LANDLORD,
        )
        self.tenant = User.objects.create_user(
            username='u_tenant', password='tenantpass123', email='tenant@unit.vn',
            role=UserRole.TENANT,
        )
        self.staff = User.objects.create_user(
            username='u_staff', password='staffpass123', role=UserRole.STAFF,
        )

    def _ctx(self, user):
        from types import SimpleNamespace
        return {'request': SimpleNamespace(user=user)}

    def test_user_model_properties_and_str(self):
        """S1-UNIT-001 | Model User: full_name (có/không họ tên), is_admin_role, is_landlord_role, is_staff_role, is_tenant_role và __str__"""
        self.assertEqual(self.admin.full_name, 'Quản Trị')
        self.assertEqual(self.landlord.full_name, 'u_landlord')
        self.assertTrue(self.admin.is_admin_role)
        self.assertFalse(self.landlord.is_admin_role)
        self.assertTrue(self.landlord.is_landlord_role)
        self.assertTrue(self.staff.is_staff_role)
        self.assertTrue(self.tenant.is_tenant_role)
        self.assertEqual(str(self.admin), 'u_admin (Quản trị viên)')

    def test_permission_classes_unit_logic(self):
        """S1-UNIT-002 | IsAdminUserRole và IsLandlordOrAdmin kiểm tra trực tiếp has_permission cho ADMIN, LANDLORD, TENANT, STAFF và anonymous"""
        from types import SimpleNamespace
        from services.identity_service.permissions import IsAdminUserRole, IsLandlordOrAdmin

        anon = SimpleNamespace(is_authenticated=False, role=None, is_superuser=False)
        admin_perm = IsAdminUserRole()
        mgr_perm = IsLandlordOrAdmin()

        self.assertTrue(admin_perm.has_permission(SimpleNamespace(user=self.admin), None))
        self.assertFalse(admin_perm.has_permission(SimpleNamespace(user=self.landlord), None))
        self.assertFalse(admin_perm.has_permission(SimpleNamespace(user=self.tenant), None))
        self.assertFalse(admin_perm.has_permission(SimpleNamespace(user=anon), None))

        self.assertTrue(mgr_perm.has_permission(SimpleNamespace(user=self.admin), None))
        self.assertTrue(mgr_perm.has_permission(SimpleNamespace(user=self.landlord), None))
        self.assertFalse(mgr_perm.has_permission(SimpleNamespace(user=self.tenant), None))
        self.assertFalse(mgr_perm.has_permission(SimpleNamespace(user=self.staff), None))
        self.assertFalse(mgr_perm.has_permission(SimpleNamespace(user=anon), None))

    def test_user_and_profile_serializers_reject_duplicate_email_case_insensitive(self):
        """S1-UNIT-003 | [ID-BUG-01] UserSerializer và ProfileSerializer chặn trùng email (không phân biệt hoa/thường) khi tạo mới/cập nhật nhưng cho phép giữ nguyên email của chính mình"""
        from services.identity_service.serializers import ProfileSerializer, UserSerializer

        dup_create = UserSerializer(
            data={'username': 'new1', 'password': 'abcdef12', 'email': ' LANDLORD@unit.vn ', 'role': UserRole.TENANT},
            context=self._ctx(self.admin),
        )
        self.assertFalse(dup_create.is_valid())
        self.assertIn('email', dup_create.errors)

        dup_update = UserSerializer(
            self.tenant, data={'email': 'LANDLORD@unit.vn'}, partial=True, context=self._ctx(self.admin),
        )
        self.assertFalse(dup_update.is_valid())
        self.assertIn('email', dup_update.errors)

        dup_profile = ProfileSerializer(
            self.tenant, data={'email': 'Admin@Unit.vn'}, partial=True, context=self._ctx(self.tenant),
        )
        self.assertFalse(dup_profile.is_valid())
        self.assertIn('email', dup_profile.errors)

        self_profile = ProfileSerializer(
            self.tenant, data={'email': 'TENANT@unit.vn', 'first_name': 'Hợp lệ'}, partial=True,
            context=self._ctx(self.tenant),
        )
        self.assertTrue(self_profile.is_valid(), self_profile.errors)

        empty_user_email = UserSerializer(
            self.tenant, data={'email': ''}, partial=True, context=self._ctx(self.admin),
        )
        self.assertTrue(empty_user_email.is_valid(), empty_user_email.errors)

        valid_user_email = UserSerializer(
            self.tenant, data={'email': 'tenant@unit.vn'}, partial=True, context=self._ctx(self.admin),
        )
        self.assertTrue(valid_user_email.is_valid(), valid_user_email.errors)

        empty_email_profile = ProfileSerializer(
            self.tenant, data={'email': ''}, partial=True, context=self._ctx(self.tenant),
        )
        self.assertTrue(empty_email_profile.is_valid(), empty_email_profile.errors)

        new_profile_ser = ProfileSerializer(
            data={'email': 'unique_new@unit.vn'}, partial=True, context=self._ctx(self.tenant),
        )
        self.assertTrue(new_profile_ser.is_valid(), new_profile_ser.errors)

    def test_user_serializer_requires_password_for_admin_create_and_prevents_self_lockout(self):
        """S1-UNIT-004 | [ID-BUG-02, ID-BUG-03] UserSerializer bắt buộc password khi ADMIN tạo tài khoản mới và chặn ADMIN tự khóa (is_active=False) hoặc tự hạ quyền (role!=ADMIN) tài khoản của chính mình"""
        from services.identity_service.serializers import UserSerializer

        no_pw = UserSerializer(
            data={'username': 'nopass_u', 'role': UserRole.LANDLORD},
            context=self._ctx(self.admin),
        )
        self.assertFalse(no_pw.is_valid())
        self.assertIn('password', no_pw.errors)

        self_lock = UserSerializer(
            self.admin, data={'is_active': False}, partial=True, context=self._ctx(self.admin),
        )
        self.assertFalse(self_lock.is_valid())
        self.assertIn('is_active', self_lock.errors)

        self_demote = UserSerializer(
            self.admin, data={'role': UserRole.TENANT}, partial=True, context=self._ctx(self.admin),
        )
        self.assertFalse(self_demote.is_valid())
        self.assertIn('role', self_demote.errors)

        self_keep = UserSerializer(
            self.admin, data={'is_active': True, 'role': UserRole.ADMIN, 'first_name': 'Giữ'},
            partial=True, context=self._ctx(self.admin),
        )
        self.assertTrue(self_keep.is_valid(), self_keep.errors)

        admin_pw_reset = UserSerializer(
            self.tenant, data={'password': 'newtenantpass1'}, partial=True, context=self._ctx(self.admin),
        )
        self.assertTrue(admin_pw_reset.is_valid(), admin_pw_reset.errors)
        updated = admin_pw_reset.save()
        self.assertTrue(updated.check_password('newtenantpass1'))

    def test_user_serializer_landlord_restrictions_on_create_and_update(self):
        """S1-UNIT-005 | [QLNT-218] UserSerializer chặn LANDLORD tạo ADMIN/LANDLORD, chặn thiếu password hoặc is_active=False, chặn đổi role/is_active/password khi update, và chặn gán mới role STAFF"""
        from services.identity_service.serializers import UserSerializer

        for forbidden_role in (UserRole.ADMIN, UserRole.LANDLORD, UserRole.STAFF):
            bad_role = UserSerializer(
                data={'username': f'bad_{forbidden_role}', 'password': 'abcdef12', 'role': forbidden_role},
                context=self._ctx(self.landlord),
            )
            self.assertFalse(bad_role.is_valid())
            self.assertIn('role', bad_role.errors)

        staff_by_admin = UserSerializer(
            data={'username': 'staff_new', 'password': 'abcdef12', 'role': UserRole.STAFF},
            context=self._ctx(self.admin),
        )
        self.assertFalse(staff_by_admin.is_valid())
        self.assertIn('role', staff_by_admin.errors)

        inactive_create = UserSerializer(
            data={'username': 't_inact', 'password': 'abcdef12', 'is_active': False},
            context=self._ctx(self.landlord),
        )
        self.assertFalse(inactive_create.is_valid())
        self.assertIn('is_active', inactive_create.errors)

        no_pw_create = UserSerializer(
            data={'username': 't_nopw'},
            context=self._ctx(self.landlord),
        )
        self.assertFalse(no_pw_create.is_valid())
        self.assertIn('password', no_pw_create.errors)

        role_update = UserSerializer(
            self.tenant, data={'role': UserRole.LANDLORD}, partial=True, context=self._ctx(self.landlord),
        )
        self.assertFalse(role_update.is_valid())
        self.assertIn('role', role_update.errors)

        active_update = UserSerializer(
            self.tenant, data={'is_active': False}, partial=True, context=self._ctx(self.landlord),
        )
        self.assertFalse(active_update.is_valid())
        self.assertIn('is_active', active_update.errors)

        pw_update = UserSerializer(
            self.tenant, data={'password': 'hackedpass123'}, partial=True, context=self._ctx(self.landlord),
        )
        self.assertFalse(pw_update.is_valid())
        self.assertIn('password', pw_update.errors)

        ok_create = UserSerializer(
            data={'username': 't_created_by_ll', 'password': 'abcdef12'},
            context=self._ctx(self.landlord),
        )
        self.assertTrue(ok_create.is_valid(), ok_create.errors)
        created_u = ok_create.save()
        self.assertEqual(created_u.role, UserRole.TENANT)
        self.assertTrue(created_u.check_password('abcdef12'))

    def test_change_password_serializer_rejects_same_or_weak_password(self):
        """S1-UNIT-006 | [QLNT-217] ChangePasswordSerializer chặn mật khẩu cũ sai, mật khẩu mới trùng mật khẩu cũ, mật khẩu mới quá ngắn (< 6 ký tự), và thiếu trường bắt buộc"""
        from services.identity_service.serializers import ChangePasswordSerializer

        missing = ChangePasswordSerializer(data={}, context=self._ctx(self.tenant))
        self.assertFalse(missing.is_valid())
        self.assertTrue({'old_password', 'new_password'} <= set(missing.errors))

        wrong_old = ChangePasswordSerializer(
            data={'old_password': 'wrongpass', 'new_password': 'newvalidpass123'},
            context=self._ctx(self.tenant),
        )
        self.assertFalse(wrong_old.is_valid())
        self.assertIn('old_password', wrong_old.errors)

        weak_new = ChangePasswordSerializer(
            data={'old_password': 'tenantpass123', 'new_password': '123'},
            context=self._ctx(self.tenant),
        )
        self.assertFalse(weak_new.is_valid())
        self.assertIn('new_password', weak_new.errors)

        same_pw = ChangePasswordSerializer(
            data={'old_password': 'tenantpass123', 'new_password': 'tenantpass123'},
            context=self._ctx(self.tenant),
        )
        self.assertFalse(same_pw.is_valid())
        self.assertIn('new_password', same_pw.errors)

        ok_pw = ChangePasswordSerializer(
            data={'old_password': 'tenantpass123', 'new_password': 'newvalidpass123'},
            context=self._ctx(self.tenant),
        )
        self.assertTrue(ok_pw.is_valid(), ok_pw.errors)

    def test_custom_token_refresh_serializer_syncs_claims_and_handles_deleted_user(self):
        """S1-UNIT-007 | [QLNT-214, ID-BUG-04] CustomTokenRefreshSerializer đồng bộ lại claims (role, full_name, username, is_superuser, is_staff) từ DB và ném AuthenticationFailed khi user bị xóa, bị khóa hoặc thiếu user_id"""
        from rest_framework.exceptions import AuthenticationFailed
        from services.identity_service.serializers import CustomTokenRefreshSerializer

        refresh = CustomTokenObtainPairSerializer.get_token(self.tenant)
        self.tenant.role = UserRole.LANDLORD
        self.tenant.first_name = 'Mới'
        self.tenant.save()

        ser = CustomTokenRefreshSerializer(data={'refresh': str(refresh)})
        self.assertTrue(ser.is_valid(), ser.errors)
        new_access = AccessToken(ser.validated_data['access'])
        self.assertEqual(new_access['role'], UserRole.LANDLORD)
        self.assertEqual(new_access['full_name'], 'Mới')
        self.assertEqual(new_access['username'], 'u_tenant')

        locked_user = User.objects.create_user(
            username='locked_u', password='abcdef12', role=UserRole.TENANT, is_active=True,
        )
        locked_refresh = str(CustomTokenObtainPairSerializer.get_token(locked_user))
        locked_user.is_active = False
        locked_user.save(update_fields=['is_active'])
        with self.assertRaises(AuthenticationFailed):
            CustomTokenRefreshSerializer(data={'refresh': locked_refresh}).is_valid(raise_exception=True)

        temp_user = User.objects.create_user(username='to_delete', password='abcdef12', role=UserRole.TENANT)
        orphan_refresh = str(CustomTokenObtainPairSerializer.get_token(temp_user))
        temp_user.delete()
        with self.assertRaises(AuthenticationFailed):
            CustomTokenRefreshSerializer(data={'refresh': orphan_refresh}).is_valid(raise_exception=True)

        no_uid_tok = CustomTokenObtainPairSerializer.get_token(self.landlord)
        del no_uid_tok.payload['user_id']
        with self.assertRaises(AuthenticationFailed):
            CustomTokenRefreshSerializer(data={'refresh': str(no_uid_tok)}).is_valid(raise_exception=True)

    def test_register_serializer_creates_landlord_by_default_and_tenant_with_hashed_password(self):
        """S1-UNIT-008 | [QLNT-211] RegisterSerializer tạo tài khoản thành công với role mặc định LANDLORD và TENANT, băm mật khẩu và luôn ép is_staff=False, is_superuser=False"""
        from services.identity_service.serializers import RegisterSerializer

        s_default = RegisterSerializer(data={
            'username': 'reg_ll_default',
            'password': 'validpass123',
            'email': 'reg_ll@unit.vn',
            'first_name': 'Chủ',
            'last_name': 'Mới',
            'phone_number': '0901112222',
        })
        self.assertTrue(s_default.is_valid(), s_default.errors)
        u_ll = s_default.save()
        self.assertEqual(u_ll.role, UserRole.LANDLORD)
        self.assertTrue(u_ll.check_password('validpass123'))
        self.assertNotEqual(u_ll.password, 'validpass123')
        self.assertFalse(u_ll.is_staff)
        self.assertFalse(u_ll.is_superuser)
        self.assertEqual(u_ll.full_name, 'Chủ Mới')

        s_tenant = RegisterSerializer(data={
            'username': 'reg_tenant_u',
            'password': 'validpass123',
            'role': UserRole.TENANT,
        })
        self.assertTrue(s_tenant.is_valid(), s_tenant.errors)
        u_ten = s_tenant.save()
        self.assertEqual(u_ten.role, UserRole.TENANT)
        self.assertTrue(u_ten.check_password('validpass123'))

    def test_register_serializer_rejects_duplicate_or_invalid_email_and_trims_whitespace(self):
        """S1-UNIT-009 | [QLNT-211] RegisterSerializer chặn email trùng (chính xác & không phân biệt hoa/thường), cắt khoảng trắng đầu/cuối, chặn email sai định dạng và cho phép email rỗng"""
        from services.identity_service.serializers import RegisterSerializer

        for dup_mail in ('landlord@unit.vn', 'LANDLORD@UNIT.VN', '  Landlord@Unit.vn  '):
            with self.subTest(email=dup_mail):
                s_dup = RegisterSerializer(data={
                    'username': 'dup_mail_user', 'password': 'validpass123', 'email': dup_mail,
                })
                self.assertFalse(s_dup.is_valid())
                self.assertIn('email', s_dup.errors)

        s_bad_fmt = RegisterSerializer(data={
            'username': 'bad_mail_fmt', 'password': 'validpass123', 'email': 'not-an-email',
        })
        self.assertFalse(s_bad_fmt.is_valid())
        self.assertIn('email', s_bad_fmt.errors)

        s_trimmed = RegisterSerializer(data={
            'username': 'trim_mail_u', 'password': 'validpass123', 'email': '  fresh_mail@unit.vn  ',
        })
        self.assertTrue(s_trimmed.is_valid(), s_trimmed.errors)
        self.assertEqual(s_trimmed.validated_data['email'], 'fresh_mail@unit.vn')

        for idx in (1, 2):
            s_empty = RegisterSerializer(data={'username': f'no_mail_{idx}', 'password': 'validpass123', 'email': ''})
            self.assertTrue(s_empty.is_valid(), s_empty.errors)
            s_empty.save()

    def test_register_serializer_rejects_missing_fields_weak_password_and_privileged_roles(self):
        """S1-UNIT-010 | [QLNT-211] RegisterSerializer chặn thiếu trường bắt buộc (username, password), mật khẩu < 6 ký tự, biên username > 150 ký tự và chặn role ADMIN/STAFF"""
        from services.identity_service.serializers import RegisterSerializer

        s_empty = RegisterSerializer(data={})
        self.assertFalse(s_empty.is_valid())
        self.assertTrue({'username', 'password'} <= set(s_empty.errors))

        s_short_pw = RegisterSerializer(data={'username': 'short_pw_u', 'password': '12345'})
        self.assertFalse(s_short_pw.is_valid())
        self.assertIn('password', s_short_pw.errors)

        s_long_user = RegisterSerializer(data={'username': 'u' * 151, 'password': 'validpass123'})
        self.assertFalse(s_long_user.is_valid())
        self.assertIn('username', s_long_user.errors)

        s_boundary_ok = RegisterSerializer(data={'username': 'u' * 150, 'password': '123456'})
        self.assertTrue(s_boundary_ok.is_valid(), s_boundary_ok.errors)

        for bad_role in (UserRole.ADMIN, UserRole.STAFF, 'SUPERADMIN'):
            s_role = RegisterSerializer(data={'username': f'r_{bad_role}', 'password': 'validpass123', 'role': bad_role})
            self.assertFalse(s_role.is_valid())
            self.assertIn('role', s_role.errors)

    def test_login_serializer_embeds_stateless_jwt_claims_and_returns_user_profile(self):
        """S1-UNIT-011 | [QLNT-212] CustomTokenObtainPairSerializer cấp access/refresh token hợp lệ, nhúng claims stateless (username, role, full_name, is_superuser, is_staff) và trả thông tin user"""
        ser = CustomTokenObtainPairSerializer(data={'username': 'u_admin', 'password': 'adminpass123'})
        self.assertTrue(ser.is_valid(), ser.errors)
        data = ser.validated_data
        self.assertIn('access', data)
        self.assertIn('refresh', data)
        self.assertEqual(data['user']['username'], 'u_admin')
        self.assertEqual(data['user']['role'], UserRole.ADMIN)
        self.assertEqual(data['user']['full_name'], 'Quản Trị')

        access = AccessToken(data['access'])
        self.assertEqual(int(access['user_id']), self.admin.id)
        self.assertEqual(access['username'], 'u_admin')
        self.assertEqual(access['role'], UserRole.ADMIN)
        self.assertEqual(access['full_name'], 'Quản Trị')
        self.assertFalse(access['is_superuser'])
        self.assertFalse(access['is_staff'])

    def test_login_serializer_rejects_wrong_username_wrong_password_inactive_user_and_missing_fields(self):
        """S1-UNIT-012 | [QLNT-212] CustomTokenObtainPairSerializer từ chối sai tài khoản, sai mật khẩu, tài khoản bị khóa (is_active=False) và thiếu thông tin đăng nhập"""
        from rest_framework.exceptions import AuthenticationFailed

        s_missing = CustomTokenObtainPairSerializer(data={})
        self.assertFalse(s_missing.is_valid())
        self.assertTrue({'username', 'password'} <= set(s_missing.errors))

        with self.assertRaises(AuthenticationFailed):
            CustomTokenObtainPairSerializer(
                data={'username': 'nonexistent_user', 'password': 'adminpass123'}
            ).is_valid(raise_exception=True)

        with self.assertRaises(AuthenticationFailed):
            CustomTokenObtainPairSerializer(
                data={'username': 'u_admin', 'password': 'wrongpassword'}
            ).is_valid(raise_exception=True)

        self.tenant.is_active = False
        self.tenant.save(update_fields=['is_active'])
        with self.assertRaises(AuthenticationFailed):
            CustomTokenObtainPairSerializer(
                data={'username': 'u_tenant', 'password': 'tenantpass123'}
            ).is_valid(raise_exception=True)

    def test_logout_serializer_and_view_unit_blacklist_own_refresh_token(self):
        """S1-UNIT-013 | [QLNT-213] LogoutSerializer bắt buộc trường refresh và LogoutView.post() thu hồi (blacklist) thành công refresh token của chính người dùng"""
        from types import SimpleNamespace
        from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken
        from services.identity_service.serializers import LogoutSerializer
        from services.identity_service.views import LogoutView

        self.assertFalse(LogoutSerializer(data={}).is_valid())
        self.assertFalse(LogoutSerializer(data={'refresh': ''}).is_valid())

        refresh = CustomTokenObtainPairSerializer.get_token(self.landlord)
        jti = refresh['jti']
        req = SimpleNamespace(user=self.landlord, data={'refresh': str(refresh)})
        res = LogoutView().post(req)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertTrue(BlacklistedToken.objects.filter(token__jti=jti).exists())

    def test_logout_view_unit_rejects_foreign_invalid_or_already_blacklisted_token(self):
        """S1-UNIT-014 | [QLNT-213] LogoutView.post() từ chối refresh token của người khác (400), token sai định dạng (400), đã bị blacklist (400) hoặc không cung cấp token"""
        from types import SimpleNamespace
        from rest_framework.exceptions import ValidationError
        from services.identity_service.views import LogoutView

        view = LogoutView()
        with self.assertRaises(ValidationError):
            view.post(SimpleNamespace(user=self.tenant, data={}))

        landlord_refresh = CustomTokenObtainPairSerializer.get_token(self.landlord)
        res_foreign = view.post(SimpleNamespace(user=self.tenant, data={'refresh': str(landlord_refresh)}))
        self.assertEqual(res_foreign.status_code, status.HTTP_400_BAD_REQUEST)

        res_invalid = view.post(SimpleNamespace(user=self.landlord, data={'refresh': 'not-a-valid-jwt'}))
        self.assertEqual(res_invalid.status_code, status.HTTP_400_BAD_REQUEST)

        res_ok = view.post(SimpleNamespace(user=self.landlord, data={'refresh': str(landlord_refresh)}))
        self.assertEqual(res_ok.status_code, status.HTTP_200_OK)
        res_again = view.post(SimpleNamespace(user=self.landlord, data={'refresh': str(landlord_refresh)}))
        self.assertEqual(res_again.status_code, status.HTTP_400_BAD_REQUEST)

    def test_change_password_view_unit_hashes_new_password_and_blacklists_only_user_tokens(self):
        """S1-UNIT-015 | [QLNT-217, ID-BUG-05] ChangePasswordView.post() băm mật khẩu mới, thu hồi toàn bộ OutstandingToken của user hiện tại nhưng không ảnh hưởng token của user khác"""
        from types import SimpleNamespace
        from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken
        from services.identity_service.views import ChangePasswordView

        tok_tenant = CustomTokenObtainPairSerializer.get_token(self.tenant)
        tok_landlord = CustomTokenObtainPairSerializer.get_token(self.landlord)

        view = ChangePasswordView()
        req = SimpleNamespace(
            user=SimpleNamespace(id=self.tenant.id, check_password=self.tenant.check_password),
            data={'old_password': 'tenantpass123', 'new_password': 'newtenantpass999'},
        )
        res = view.post(req)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.tenant.refresh_from_db()
        self.assertTrue(self.tenant.check_password('newtenantpass999'))
        self.assertNotEqual(self.tenant.password, 'newtenantpass999')
        self.assertTrue(BlacklistedToken.objects.filter(token__jti=tok_tenant['jti']).exists())
        self.assertFalse(BlacklistedToken.objects.filter(token__jti=tok_landlord['jti']).exists())

    def test_profile_serializer_and_current_user_view_prevent_privilege_escalation(self):
        """S1-UNIT-016 | [QLNT-218] ProfileSerializer khóa read-only role/is_active/username chống tự nâng quyền và CurrentUserView.get_object() hỗ trợ cả User lẫn TokenUser"""
        from types import SimpleNamespace
        from services.identity_service.serializers import ProfileSerializer
        from services.identity_service.views import CurrentUserView

        ser = ProfileSerializer(
            self.tenant,
            data={'role': UserRole.ADMIN, 'is_active': False, 'username': 'hacked_name', 'phone_number': '0988776655'},
            partial=True,
            context=self._ctx(self.tenant),
        )
        self.assertTrue(ser.is_valid(), ser.errors)
        saved = ser.save()
        self.assertEqual(saved.role, UserRole.TENANT)
        self.assertTrue(saved.is_active)
        self.assertEqual(saved.username, 'u_tenant')
        self.assertEqual(saved.phone_number, '0988776655')

        v_direct = CurrentUserView()
        v_direct.request = SimpleNamespace(user=self.tenant)
        self.assertEqual(v_direct.get_object(), self.tenant)

        v_proxy = CurrentUserView()
        v_proxy.request = SimpleNamespace(user=SimpleNamespace(id=self.tenant.id))
        self.assertEqual(v_proxy.get_object().id, self.tenant.id)

    def test_user_viewset_unit_permissions_destroy_self_protection_queryset_scope_and_eligibility(self):
        """S1-UNIT-017 | [QLNT-218, ID-BUG-06] UserViewSet: get_permissions, perform_destroy chặn tự xóa, get_queryset lọc phạm vi ADMIN/LANDLORD + role hoa/thường/ALL, và tenant_link_eligibility"""
        from types import SimpleNamespace
        from django.http import Http404
        from rest_framework.exceptions import ValidationError
        from services.identity_service.permissions import IsAdminUserRole, IsLandlordOrAdmin
        from services.identity_service.views import UserViewSet

        view = UserViewSet()
        view.action = 'destroy'
        self.assertIsInstance(view.get_permissions()[0], IsAdminUserRole)
        view.action = 'list'
        self.assertIsInstance(view.get_permissions()[0], IsLandlordOrAdmin)

        view.request = SimpleNamespace(user=self.admin, query_params={}, META={})
        with self.assertRaises(ValidationError):
            view.perform_destroy(self.admin)

        view.request = SimpleNamespace(user=self.admin, query_params={'role': 'tenant'}, META={})
        self.assertEqual([u.username for u in view.get_queryset()], ['u_tenant'])

        view.request = SimpleNamespace(user=self.admin, query_params={'role': 'ALL'}, META={})
        self.assertEqual(view.get_queryset().count(), 4)

        with mock.patch('common.service_client.fetch_tenant_links',
                        return_value=[tenant_link(1, self.tenant.id, room_id=1, landlord_id=self.landlord.id)]):
            view.request = SimpleNamespace(
                user=self.landlord, query_params={}, META={'HTTP_AUTHORIZATION': 'Bearer tok'},
            )
            self.assertEqual(sorted(u.username for u in view.get_queryset()), ['u_landlord', 'u_tenant'])

        self.assertTrue(view.tenant_link_eligibility(view.request, pk=str(self.tenant.id)).data['eligible'])
        self.assertFalse(view.tenant_link_eligibility(view.request, pk=str(self.admin.id)).data['eligible'])
        with self.assertRaises(Http404):
            view.tenant_link_eligibility(view.request, pk='invalid-pk')

    def test_custom_token_refresh_serializer_rejects_expired_bad_signature_and_blacklisted_tokens(self):
        """S1-UNIT-018 | [QLNT-214] CustomTokenRefreshSerializer từ chối refresh token hết hạn, sai chữ ký và đã bị blacklist (bao gồm token cũ sau khi rotation)"""
        from datetime import timedelta
        import jwt as pyjwt
        from rest_framework_simplejwt.exceptions import TokenError
        from services.identity_service.serializers import CustomTokenRefreshSerializer

        expired = CustomTokenObtainPairSerializer.get_token(self.tenant)
        expired.set_exp(lifetime=-timedelta(seconds=30))
        with self.assertRaises(TokenError):
            CustomTokenRefreshSerializer(data={'refresh': str(expired)}).is_valid(raise_exception=True)

        forged = pyjwt.encode(
            {'token_type': 'refresh', 'user_id': self.tenant.id, 'jti': 'forged', 'exp': 4102444800},
            'wrong-secret-key-not-matching-1234567890',
            algorithm='HS256',
        )
        with self.assertRaises(TokenError):
            CustomTokenRefreshSerializer(data={'refresh': forged}).is_valid(raise_exception=True)

        valid_refresh = CustomTokenObtainPairSerializer.get_token(self.tenant)
        first_run = CustomTokenRefreshSerializer(data={'refresh': str(valid_refresh)})
        self.assertTrue(first_run.is_valid(), first_run.errors)
        with self.assertRaises(TokenError):
            CustomTokenRefreshSerializer(data={'refresh': str(valid_refresh)}).is_valid(raise_exception=True)


class IdentityBugVerificationApiTests(TestCase):
    """[API/HTTP TEST] Kiểm thử xác nhận các bug nghiệp vụ & bảo mật đã sửa của Service 1 (ID-BUG-01..ID-BUG-06)."""
    databases = {'default'}

    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_user(
            username='api_admin', password='adminpass123', email='admin@api.vn', role=UserRole.ADMIN,
        )
        self.landlord = User.objects.create_user(
            username='api_landlord', password='landlordpass123', email='landlord@api.vn', role=UserRole.LANDLORD,
        )
        self.tenant = User.objects.create_user(
            username='api_tenant', password='tenantpass123', email='tenant@api.vn', role=UserRole.TENANT,
        )
        patcher = mock.patch('common.service_client.fetch_tenant_links',
                             return_value=[tenant_link(1, self.tenant.id, room_id=1, landlord_id=self.landlord.id)])
        patcher.start()
        self.addCleanup(patcher.stop)

    def _bearer(self, user):
        c = APIClient()
        token = CustomTokenObtainPairSerializer.get_token(user).access_token
        c.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        return c

    def test_duplicate_email_blocked_on_user_management_and_profile_me_api(self):
        """S1-API-031 | [ID-BUG-01] POST/PATCH /api/users/ và PATCH /api/auth/me/ chặn trùng email (không phân biệt hoa/thường) với tài khoản khác (400)"""
        admin_client = self._bearer(self.admin)
        res_post = admin_client.post('/api/users/', {
            'username': 'dup_email_u', 'password': 'abcdef12', 'email': 'LANDLORD@api.vn', 'role': UserRole.TENANT,
        }, format='json')
        self.assertEqual(res_post.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('email', res_post.data)

        res_patch_user = admin_client.patch(f'/api/users/{self.tenant.id}/', {'email': 'Admin@Api.vn'}, format='json')
        self.assertEqual(res_patch_user.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('email', res_patch_user.data)

        tenant_client = self._bearer(self.tenant)
        res_ok_me = tenant_client.patch('/api/auth/me/', {'first_name': 'Khách'}, format='json')
        self.assertEqual(res_ok_me.status_code, status.HTTP_200_OK)

        res_me = tenant_client.patch('/api/auth/me/', {'email': 'LANDLORD@API.VN'}, format='json')
        self.assertEqual(res_me.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('email', res_me.data)

        self.assertEqual(admin_client.delete(f'/api/users/{self.landlord.id}/').status_code,
                         status.HTTP_204_NO_CONTENT)
        self.landlord = User.objects.create_user(
            username='api_landlord', password='landlordpass123', email='landlord@api.vn', role=UserRole.LANDLORD,
        )

    def test_admin_create_requires_password_and_admin_cannot_lock_or_demote_self_api(self):
        """S1-API-032 | [ID-BUG-02, ID-BUG-03] POST /api/users/ bởi ADMIN thiếu password trả 400; PATCH /api/users/{admin_id}/ tự khóa hoặc tự hạ quyền trả 400"""
        admin_client = self._bearer(self.admin)
        res_nopw = admin_client.post('/api/users/', {'username': 'no_pw_admin', 'role': UserRole.LANDLORD},
                                     format='json')
        self.assertEqual(res_nopw.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('password', res_nopw.data)

        res_lock = admin_client.patch(f'/api/users/{self.admin.id}/', {'is_active': False}, format='json')
        self.assertEqual(res_lock.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('is_active', res_lock.data)

        res_demote = admin_client.patch(f'/api/users/{self.admin.id}/', {'role': UserRole.TENANT}, format='json')
        self.assertEqual(res_demote.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('role', res_demote.data)
        self.admin.refresh_from_db()
        self.assertTrue(self.admin.is_active)
        self.assertEqual(self.admin.role, UserRole.ADMIN)

    def test_refresh_token_syncs_latest_role_and_returns_401_for_deleted_or_inactive_user(self):
        """S1-API-033 | [ID-BUG-04] POST /api/auth/refresh/ cập nhật đúng claim role mới sau khi ADMIN đổi role, và trả 401 (không phải 500) khi user đã bị xóa hoặc bị khóa"""
        login_res = self.client.post('/api/auth/login/', {
            'username': 'api_tenant', 'password': 'tenantpass123',
        }, format='json')
        refresh_tok = login_res.data['refresh']

        self.tenant.role = UserRole.LANDLORD
        self.tenant.save(update_fields=['role'])

        refresh_res = self.client.post('/api/auth/refresh/', {'refresh': refresh_tok}, format='json')
        self.assertEqual(refresh_res.status_code, status.HTTP_200_OK, refresh_res.data)
        new_access = AccessToken(refresh_res.data['access'])
        self.assertEqual(new_access['role'], UserRole.LANDLORD)

        rotated_refresh = refresh_res.data['refresh']
        self.tenant.delete()
        deleted_res = self.client.post('/api/auth/refresh/', {'refresh': rotated_refresh}, format='json')
        self.assertEqual(deleted_res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_change_password_revokes_existing_refresh_tokens_and_prevents_foreign_logout(self):
        """S1-API-034 | [ID-BUG-05] POST /api/auth/change-password/ thu hồi toàn bộ refresh token đã cấp trước đó; LogoutView chặn thu hồi token của người khác hoặc token lỗi (400)"""
        login_res = self.client.post('/api/auth/login/', {
            'username': 'api_landlord', 'password': 'landlordpass123',
        }, format='json')
        old_refresh = login_res.data['refresh']
        access_tok = login_res.data['access']

        tenant_client = self._bearer(self.tenant)
        foreign_logout = tenant_client.post('/api/auth/logout/', {'refresh': old_refresh}, format='json')
        self.assertEqual(foreign_logout.status_code, status.HTTP_400_BAD_REQUEST)

        bad_logout = tenant_client.post('/api/auth/logout/', {'refresh': 'invalid-refresh-token'}, format='json')
        self.assertEqual(bad_logout.status_code, status.HTTP_400_BAD_REQUEST)

        auth_client = APIClient()
        auth_client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_tok}')
        pw_res = auth_client.post('/api/auth/change-password/', {
            'old_password': 'landlordpass123', 'new_password': 'newlandlordpass123',
        }, format='json')
        self.assertEqual(pw_res.status_code, status.HTTP_200_OK)

        refresh_after_pw_change = self.client.post('/api/auth/refresh/', {'refresh': old_refresh}, format='json')
        self.assertEqual(refresh_after_pw_change.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_users_list_role_filter_case_insensitive_and_all_keyword(self):
        """S1-API-035 | [ID-BUG-06] GET /api/users/?role=tenant (chữ thường) và ?role=ALL hoạt động đúng cho ADMIN và LANDLORD"""
        admin_client = self._bearer(self.admin)
        res_lower = admin_client.get('/api/users/?role=tenant')
        self.assertEqual(res_lower.status_code, status.HTTP_200_OK)
        self.assertEqual([u['username'] for u in res_lower.data], ['api_tenant'])

        res_all = admin_client.get('/api/users/?role=ALL')
        self.assertEqual(res_all.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res_all.data), 3)


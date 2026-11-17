from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework.throttling import ScopedRateThrottle
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken

User = get_user_model()
BASE = '/api/v1/'


class IdentitySecurityTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.password = 'River!Lemon7249'
        cls.admin = User.objects.create_user(username='manager', password=cls.password, role='ADMIN')
        cls.landlord = User.objects.create_user(username='owner', password=cls.password, role='LANDLORD')
        cls.tenant = User.objects.create_user(username='renter', password=cls.password, role='TENANT')
        cls.staff = User.objects.create_user(username='employee', password=cls.password, role='STAFF')

    def setUp(self):
        cache.clear()
        self.client = APIClient()

    def login(self, user=None):
        user = user or self.landlord
        response = self.client.post(BASE + 'auth/login/',
                                    {'username': user.username, 'password': self.password}, format='json')
        self.assertEqual(response.status_code, 200, response.data)
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + response.data['access'])
        return response.data

    def registration(self, **changes):
        data = {'username': 'newowner', 'password': self.password, 'password_confirm': self.password}
        data.update(changes)
        return self.client.post(BASE + 'auth/register/', data, format='json')

    def test_register_hashes_password_and_assigns_landlord(self):
        response = self.registration()
        self.assertEqual(response.status_code, 201, response.data)
        user = User.objects.get(username='newowner')
        self.assertEqual(user.role, 'LANDLORD')
        self.assertTrue(user.check_password(self.password))
        self.assertNotEqual(user.password, self.password)
        self.assertNotIn('password', response.data)
        self.assertNotIn('password_confirm', response.data)

    def test_register_rejects_privileged_roles(self):
        for role in ('ADMIN', 'STAFF', 'TENANT'):
            with self.subTest(role=role):
                self.assertEqual(self.registration(role=role).status_code, 400)
        self.assertFalse(User.objects.filter(username='newowner').exists())

    def test_register_rejects_privileged_flags(self):
        for flag in ('is_staff', 'is_superuser', 'is_active'):
            with self.subTest(flag=flag):
                self.assertEqual(self.registration(**{flag: True}).status_code, 400)

    def test_register_rejects_weak_password(self):
        self.assertEqual(self.registration(password='12345678', password_confirm='12345678').status_code, 400)

    def test_register_rejects_mismatched_confirmation(self):
        self.assertEqual(self.registration(password_confirm='different').status_code, 400)

    def test_register_rejects_duplicate_username(self):
        self.assertEqual(self.registration(username=self.landlord.username).status_code, 400)

    def test_login_returns_valid_tokens_for_every_role(self):
        for user in (self.admin, self.landlord, self.staff, self.tenant):
            with self.subTest(role=user.role):
                tokens = self.login(user)
                self.assertEqual(AccessToken(tokens['access'])['user_id'], str(user.pk))
                self.assertEqual(tokens['user']['role'], user.role)
                self.assertNotIn('password', tokens['user'])

    def test_login_rejects_bad_credentials(self):
        response = self.client.post(BASE + 'auth/login/',
                                    {'username': 'owner', 'password': 'bad'}, format='json')
        self.assertEqual(response.status_code, 401)

    def test_inactive_user_cannot_login(self):
        self.landlord.is_active = False
        self.landlord.save()
        response = self.client.post(BASE + 'auth/login/',
                                    {'username': 'owner', 'password': self.password}, format='json')
        self.assertEqual(response.status_code, 401)

    def test_missing_and_invalid_access_token_rejected(self):
        self.assertEqual(self.client.get(BASE + 'auth/me/').status_code, 401)
        self.client.credentials(HTTP_AUTHORIZATION='Bearer invalid')
        self.assertEqual(self.client.get(BASE + 'auth/me/').status_code, 401)

    def test_expired_access_token_rejected(self):
        token = AccessToken.for_user(self.landlord)
        token.set_exp(lifetime=timedelta(seconds=-1))
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + str(token))
        self.assertEqual(self.client.get(BASE + 'auth/me/').status_code, 401)

    def test_profile_updates_contact_fields(self):
        self.login()
        response = self.client.patch(BASE + 'auth/me/', {'first_name': 'Chính', 'phone_number': '0901234567'}, format='json')
        self.assertEqual(response.status_code, 200, response.data)
        self.landlord.refresh_from_db()
        self.assertEqual(self.landlord.phone_number, '0901234567')

    def test_profile_rejects_privilege_escalation(self):
        self.login(self.tenant)
        for field, value in [('role', 'ADMIN'), ('is_staff', True), ('is_superuser', True), ('is_active', False)]:
            with self.subTest(field=field):
                response = self.client.patch(BASE + 'auth/me/', {field: value}, format='json')
                self.assertEqual(response.status_code, 400)
        self.tenant.refresh_from_db()
        self.assertEqual(self.tenant.role, 'TENANT')

    def test_profile_rejects_password_bypass(self):
        self.login()
        self.assertEqual(self.client.patch(BASE + 'auth/me/', {'password': 'replacement'}, format='json').status_code, 400)

    def test_refresh_rotates_and_rejects_reuse(self):
        tokens = self.login()
        response = self.client.post(BASE + 'auth/refresh/', {'refresh': tokens['refresh']}, format='json')
        self.assertEqual(response.status_code, 200, response.data)
        self.assertNotEqual(response.data['refresh'], tokens['refresh'])
        self.assertEqual(self.client.post(BASE + 'auth/refresh/', {'refresh': tokens['refresh']}, format='json').status_code, 401)

    def test_refresh_rejects_invalid_or_expired_token(self):
        token = RefreshToken.for_user(self.landlord)
        token.set_exp(lifetime=timedelta(seconds=-1))
        for refresh in ('bad', str(token)):
            with self.subTest(refresh=refresh[:5]):
                self.assertEqual(self.client.post(BASE + 'auth/refresh/', {'refresh': refresh}, format='json').status_code, 401)

    def test_refresh_rejects_deactivated_user(self):
        tokens = self.login()
        self.landlord.is_active = False
        self.landlord.save()
        self.assertEqual(self.client.post(BASE + 'auth/refresh/', {'refresh': tokens['refresh']}, format='json').status_code, 401)

    def test_refresh_rejects_deleted_user_without_server_error(self):
        tokens = self.login()
        self.landlord.delete()
        self.assertEqual(self.client.post(BASE + 'auth/refresh/', {'refresh': tokens['refresh']}, format='json').status_code, 401)

    def test_logout_revokes_refresh_even_without_access_header(self):
        tokens = self.login()
        self.client.credentials()
        self.assertEqual(self.client.post(BASE + 'auth/logout/', {'refresh': tokens['refresh']}, format='json').status_code, 204)
        self.assertEqual(self.client.post(BASE + 'auth/refresh/', {'refresh': tokens['refresh']}, format='json').status_code, 401)

    def test_logout_rejects_missing_or_malformed_token(self):
        for data in ({}, {'refresh': 'bad'}):
            self.assertEqual(self.client.post(BASE + 'auth/logout/', data, format='json').status_code, 400)

    def password_change(self, **changes):
        data = {'old_password': self.password, 'new_password': 'Cloud!Mango8452', 'password_confirm': 'Cloud!Mango8452'}
        data.update(changes)
        return self.client.post(BASE + 'auth/change-password/', data, format='json')

    def test_password_change_invalidates_old_access_and_refresh(self):
        tokens = self.login()
        self.assertEqual(self.password_change().status_code, 200)
        self.assertEqual(self.client.get(BASE + 'auth/me/').status_code, 401)
        self.assertEqual(self.client.post(BASE + 'auth/refresh/', {'refresh': tokens['refresh']}, format='json').status_code, 401)
        self.client.credentials()
        old = self.client.post(BASE + 'auth/login/', {'username': 'owner', 'password': self.password}, format='json')
        self.assertEqual(old.status_code, 401)
        new = self.client.post(BASE + 'auth/login/', {'username': 'owner', 'password': 'Cloud!Mango8452'}, format='json')
        self.assertEqual(new.status_code, 200)

    def test_password_change_rejects_wrong_old_password(self):
        self.login()
        self.assertEqual(self.password_change(old_password='wrong').status_code, 400)

    def test_password_change_rejects_weak_or_mismatched_password(self):
        self.login()
        self.assertEqual(self.password_change(new_password='123', password_confirm='123').status_code, 400)
        self.assertEqual(self.password_change(password_confirm='mismatch').status_code, 400)

    def test_only_admin_can_manage_users(self):
        for user in (self.landlord, self.staff, self.tenant):
            self.login(user)
            with self.subTest(role=user.role):
                self.assertEqual(self.client.get(BASE + 'users/').status_code, 403)
                self.assertEqual(self.client.patch(BASE + f'users/{self.tenant.pk}/', {'role': 'ADMIN'}, format='json').status_code, 403)

    def test_admin_creates_user_with_hashed_password(self):
        self.login(self.admin)
        response = self.client.post(BASE + 'users/', {'username': 'newstaff', 'role': 'STAFF', 'password': self.password}, format='json')
        self.assertEqual(response.status_code, 201, response.data)
        self.assertTrue(User.objects.get(username='newstaff').check_password(self.password))
        self.assertNotIn('password', response.data)

    def test_admin_creation_requires_valid_password(self):
        self.login(self.admin)
        self.assertEqual(self.client.post(BASE + 'users/', {'username': 'no_password'}, format='json').status_code, 400)

    def test_admin_changes_role_and_filters_users(self):
        self.login(self.admin)
        response = self.client.patch(BASE + f'users/{self.tenant.pk}/', {'role': 'STAFF'}, format='json')
        self.assertEqual(response.status_code, 200)
        response = self.client.get(BASE + 'users/?role=STAFF&search=renter')
        self.assertEqual([item['id'] for item in response.data], [self.tenant.pk])

    def test_admin_deactivation_blocks_existing_access(self):
        tokens = self.login(self.tenant)
        self.login(self.admin)
        self.assertEqual(self.client.patch(BASE + f'users/{self.tenant.pk}/', {'is_active': False}, format='json').status_code, 200)
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + tokens['access'])
        self.assertEqual(self.client.get(BASE + 'auth/me/').status_code, 401)

    def test_admin_cannot_lock_or_demote_self(self):
        self.login(self.admin)
        for data in ({'is_active': False}, {'role': 'TENANT'}):
            self.assertEqual(self.client.patch(BASE + f'users/{self.admin.pk}/', data, format='json').status_code, 400)

    def test_user_deletion_disabled_to_preserve_business_records(self):
        self.login(self.admin)
        self.assertEqual(self.client.delete(BASE + f'users/{self.tenant.pk}/').status_code, 405)
        self.assertTrue(User.objects.filter(pk=self.tenant.pk).exists())

    def test_superuser_has_admin_api_access(self):
        user = User.objects.create_superuser(username='rootreview', password=self.password, role='LANDLORD')
        self.login(user)
        self.assertEqual(self.client.get(BASE + 'users/').status_code, 200)

    def test_login_rate_limit(self):
        with patch.dict(ScopedRateThrottle.THROTTLE_RATES, {'identity_login': '2/min'}):
            for _ in range(2):
                self.client.post(BASE + 'auth/login/', {'username': 'unknown', 'password': 'wrong'}, format='json')
            self.assertEqual(self.client.post(BASE + 'auth/login/', {'username': 'unknown', 'password': 'wrong'}, format='json').status_code, 429)

    def test_protected_service_endpoints_require_authentication(self):
        for url in ('properties/', 'rooms/', 'tenants/status/', 'contracts/status/', 'billing/status/'):
            with self.subTest(url=url):
                self.assertEqual(self.client.get(BASE + url).status_code, 401)

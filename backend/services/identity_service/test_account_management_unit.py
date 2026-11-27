from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.test import SimpleTestCase

from .models import UserRole
from .permissions import IsAdminUserRole
from .serializers import AdminUserSerializer

User = get_user_model()


class AccountPermissionUnitTests(SimpleTestCase):
    def test_admin_and_superuser_can_manage_accounts(self):
        permission = IsAdminUserRole()
        cases = (
            ('anonymous', AnonymousUser(), False),
            ('admin', User(role=UserRole.ADMIN), True),
            ('landlord', User(role=UserRole.LANDLORD), False),
            ('staff', User(role=UserRole.STAFF), False),
            ('tenant', User(role=UserRole.TENANT), False),
            ('superuser', User(role=UserRole.LANDLORD, is_superuser=True), True),
        )
        for name, user, allowed in cases:
            with self.subTest(account=name):
                self.assertEqual(permission.has_permission(SimpleNamespace(user=user), view=None), allowed)


class AccountManagementUnitTests(SimpleTestCase):
    def setUp(self):
        self.admin = User(pk=1, username='manager', role=UserRole.ADMIN)
        self.tenant = User(pk=2, username='renter', role=UserRole.TENANT)
        self.superuser = User(pk=3, username='root', role=UserRole.ADMIN, is_superuser=True)
        self.current_password = 'River!Lemon7249'
        self.tenant.set_password(self.current_password)

    def account_form(self, account, **changes):
        return AdminUserSerializer(
            account,
            data=changes,
            partial=True,
            context={'request': SimpleNamespace(user=self.admin)},
        )

    def test_admin_can_change_role_and_status_of_another_account(self):
        changes = {'role': UserRole.STAFF, 'is_active': False}
        serializer = self.account_form(self.tenant, **changes)

        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(serializer.validated_data, changes)

    def test_admin_cannot_lock_or_change_own_role(self):
        for changes in ({'is_active': False}, {'role': UserRole.TENANT}):
            with self.subTest(changes=changes):
                serializer = self.account_form(self.admin, **changes)

                self.assertFalse(serializer.is_valid())
                self.assertIn('non_field_errors', serializer.errors)

    def test_admin_cannot_lock_or_change_superuser_role(self):
        for changes in ({'is_active': False}, {'role': UserRole.TENANT}):
            with self.subTest(changes=changes):
                serializer = self.account_form(self.superuser, **changes)

                self.assertFalse(serializer.is_valid())
                self.assertIn('non_field_errors', serializer.errors)

    def test_admin_can_change_superuser_contact_details(self):
        email = 'root@example.com'
        serializer = self.account_form(self.superuser, email=email)

        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(serializer.validated_data, {'email': email})

    def test_contact_update_preserves_existing_password(self):
        email = 'renter@example.com'
        previous_hash = self.tenant.password
        serializer = self.account_form(self.tenant, email=email)

        self.assertTrue(serializer.is_valid(), serializer.errors)
        with patch.object(self.tenant, 'save') as save:
            account = serializer.save()

        save.assert_called_once_with()
        self.assertEqual(account.email, email)
        self.assertEqual(account.password, previous_hash)
        self.assertTrue(account.check_password(self.current_password))

    def test_admin_password_reset_stores_a_hash(self):
        new_password = 'Cloud!Mango8452'
        serializer = self.account_form(self.tenant, password=new_password)

        self.assertTrue(serializer.is_valid(), serializer.errors)
        with patch.object(self.tenant, 'save') as save:
            account = serializer.save()

        save.assert_called_once_with()
        self.assertNotEqual(account.password, new_password)
        self.assertTrue(account.check_password(new_password))
        self.assertFalse(account.check_password(self.current_password))

    def test_admin_password_reset_rejects_weak_password(self):
        serializer = self.account_form(self.tenant, password='12345678')

        self.assertFalse(serializer.is_valid())
        self.assertEqual(set(serializer.errors), {'password'})

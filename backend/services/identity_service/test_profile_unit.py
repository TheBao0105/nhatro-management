from types import SimpleNamespace

from django.contrib.auth import get_user_model
from django.test import SimpleTestCase

from .models import UserRole
from .serializers import ChangePasswordSerializer, ProfileSerializer

User = get_user_model()


class ProfileUnitTests(SimpleTestCase):
    def setUp(self):
        self.user = User(username='owner', role=UserRole.LANDLORD)

    def test_profile_accepts_contact_changes(self):
        changes = {'email': 'owner@example.com', 'phone_number': '0901234567'}
        serializer = ProfileSerializer(self.user, data=changes, partial=True)

        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(serializer.validated_data, changes)

    def test_profile_rejects_changes_to_protected_fields(self):
        protected_fields = {
            'username': 'another-name',
            'role': UserRole.ADMIN,
            'is_active': False,
            'is_staff': True,
            'is_superuser': True,
            'password': 'Another!Password710',
        }
        for field, value in protected_fields.items():
            with self.subTest(field=field):
                serializer = ProfileSerializer(self.user, data={field: value}, partial=True)

                self.assertFalse(serializer.is_valid())
                self.assertEqual(set(serializer.errors), {field})


class ChangePasswordUnitTests(SimpleTestCase):
    def setUp(self):
        self.current_password = 'River!Lemon7249'
        self.new_password = 'Cloud!Mango8452'
        self.user = User(username='owner', role=UserRole.LANDLORD)
        self.user.set_password(self.current_password)

    def password_form(self, **changes):
        data = {
            'old_password': self.current_password,
            'new_password': self.new_password,
            'password_confirm': self.new_password,
        }
        data.update(changes)
        return ChangePasswordSerializer(data=data, context={'request': SimpleNamespace(user=self.user)})

    def test_accepts_valid_new_password(self):
        serializer = self.password_form()

        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertEqual(serializer.validated_data['new_password'], self.new_password)

    def test_rejects_incorrect_current_password(self):
        serializer = self.password_form(old_password='Incorrect!Password817')

        self.assertFalse(serializer.is_valid())
        self.assertEqual(set(serializer.errors), {'old_password'})

    def test_rejects_mismatched_confirmation(self):
        serializer = self.password_form(password_confirm='Different!Password817')

        self.assertFalse(serializer.is_valid())
        self.assertEqual(set(serializer.errors), {'password_confirm'})

    def test_rejects_reuse_of_current_password(self):
        serializer = self.password_form(
            new_password=self.current_password,
            password_confirm=self.current_password,
        )

        self.assertFalse(serializer.is_valid())
        self.assertEqual(set(serializer.errors), {'new_password'})

    def test_rejects_weak_new_password(self):
        serializer = self.password_form(new_password='12345678', password_confirm='12345678')

        self.assertFalse(serializer.is_valid())
        self.assertEqual(set(serializer.errors), {'new_password'})

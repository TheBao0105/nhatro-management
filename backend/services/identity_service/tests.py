from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from services.identity_service.models import UserRole

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
        response = self.client.post('/api/v1/auth/login/', {
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
        response = self.client.post('/api/v1/auth/login/', {
            'username': 'testlandlord',
            'password': 'wrongpassword'
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_role_authorization_and_me(self):
        """SPRINT 1: Test Role Authorization & Me endpoint"""
        self.client.force_authenticate(user=self.landlord)
        response = self.client.get('/api/v1/auth/me/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['username'], 'testlandlord')
        self.assertEqual(response.data['role'], UserRole.LANDLORD)

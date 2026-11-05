from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from services.identity_service.models import UserRole
from services.property_service.models import Property, Room, RoomStatus

User = get_user_model()

class PropertyServiceTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.landlord = User.objects.create_user(
            username='landlord_prop',
            password='password123',
            role=UserRole.LANDLORD
        )
        self.client.force_authenticate(user=self.landlord)

        self.property = Property.objects.create(
            landlord=self.landlord,
            name='Nhà trọ Thử Nghiệm',
            address='123 Test Street',
            district='Quận 1',
            city='TP. Hồ Chí Minh',
            total_floors=2,
            electricity_rate=3500.0,
            water_rate=20000.0
        )

        self.room = Room.objects.create(
            property=self.property,
            room_number='101',
            floor=1,
            area=20.0,
            rent_price=3000000.0,
            deposit_amount=3000000.0,
            status=RoomStatus.AVAILABLE
        )

    def test_list_properties(self):
        response = self.client.get('/api/v1/properties/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Check that property is returned
        self.assertGreaterEqual(len(response.data), 1)

    def test_create_property(self):
        data = {
            'name': 'Nhà trọ Mới Tạo',
            'address': '456 Phố Mới',
            'district': 'Bình Thạnh',
            'city': 'TP.HCM',
            'total_floors': 3,
            'electricity_rate': 3800.0,
            'water_rate': 25000.0,
            'internet_rate': 100000.0
        }
        response = self.client.post('/api/v1/properties/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['name'], 'Nhà trọ Mới Tạo')
        self.assertEqual(response.data['landlord'], self.landlord.id)

    def test_list_rooms_of_property(self):
        response = self.client.get(f'/api/v1/properties/{self.property.id}/rooms/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['room_number'], '101')

    def test_property_stats(self):
        response = self.client.get(f'/api/v1/properties/{self.property.id}/stats/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['total_rooms'], 1)
        self.assertEqual(response.data['available_rooms'], 1)
        self.assertEqual(response.data['occupied_rooms'], 0)

    def test_update_room_status(self):
        response = self.client.patch(
            f'/api/v1/rooms/{self.room.id}/status/',
            {'status': RoomStatus.OCCUPIED},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.room.refresh_from_db()
        self.assertEqual(self.room.status, RoomStatus.OCCUPIED)


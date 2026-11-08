from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from services.identity_service.models import UserRole
from services.property_service.models import Property, Room, RoomStatus

User = get_user_model()

class PropertyServiceTests(TestCase):
    databases = {'default', 'property_db'}

    def setUp(self):
        self.client = APIClient()
        self.landlord = User.objects.create_user(
            username='testlandlord_prop',
            password='password123',
            role=UserRole.LANDLORD
        )
        self.client.force_authenticate(user=self.landlord)

        # Property in property_db
        self.property = Property.objects.create(
            owner_id=self.landlord.id,
            name='Nhà trọ Thử Nghiệm',
            address='123 Test Street',
            district='Quận 1',
            city='TP. Hồ Chí Minh',
            total_floors=2,
            electricity_rate=3500.0,
            water_rate=20000.0
        )
        # Room in property_db
        self.room = Room.objects.create(
            property=self.property,
            room_number='101',
            floor=1,
            area=20.0,
            rent_price=3000000.0,
            deposit_amount=3000000.0,
            status=RoomStatus.AVAILABLE
        )

    def test_view_property_list(self):
        """SPRINT 1: View Property List"""
        response = self.client.get('/api/v1/properties/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(response.data), 1)

    def test_create_property(self):
        """SPRINT 1: Create Property"""
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
        self.assertEqual(response.data['owner_id'], self.landlord.id)

    def test_update_property(self):
        """SPRINT 1: Update Property"""
        data = {
            'name': 'Nhà trọ Đã Sửa Tên',
            'address': self.property.address,
            'total_floors': 4,
            'electricity_rate': 4000.0,
            'water_rate': 30000.0,
            'internet_rate': 120000.0
        }
        response = self.client.put(f'/api/v1/properties/{self.property.id}/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.property.refresh_from_db()
        self.assertEqual(self.property.name, 'Nhà trọ Đã Sửa Tên')

    def test_delete_property(self):
        """SPRINT 1: Delete Property"""
        prop = Property.objects.create(
            owner_id=self.landlord.id,
            name='Nhà trọ Cần Xóa',
            address='789 Cần Xóa'
        )
        response = self.client.delete(f'/api/v1/properties/{prop.id}/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Property.objects.filter(id=prop.id).exists())

    def test_view_room_list(self):
        """SPRINT 1: View Room List"""
        response = self.client.get(f'/api/v1/rooms/?property_id={self.property.id}')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['room_number'], '101')

    def test_create_room(self):
        """SPRINT 1: Create Room"""
        data = {
            'property': self.property.id,
            'room_number': '102',
            'floor': 1,
            'area': 22.0,
            'rent_price': 3500000.0,
            'deposit_amount': 3500000.0,
            'max_occupants': 2,
            'status': RoomStatus.AVAILABLE
        }
        response = self.client.post('/api/v1/rooms/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['room_number'], '102')

    def test_update_room(self):
        """SPRINT 1: Update Room"""
        data = {
            'property': self.property.id,
            'room_number': '101-VIP',
            'floor': 1,
            'area': 25.0,
            'rent_price': 4000000.0,
            'deposit_amount': 4000000.0,
            'max_occupants': 3,
            'status': RoomStatus.AVAILABLE
        }
        response = self.client.put(f'/api/v1/rooms/{self.room.id}/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.room.refresh_from_db()
        self.assertEqual(self.room.room_number, '101-VIP')

    def test_update_room_status(self):
        """SPRINT 1: Update Room Status"""
        response = self.client.patch(
            f'/api/v1/rooms/{self.room.id}/status/',
            {'status': RoomStatus.OCCUPIED},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.room.refresh_from_db()
        self.assertEqual(self.room.status, RoomStatus.OCCUPIED)

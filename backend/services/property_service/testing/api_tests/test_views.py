"""[API/INTEGRATION] REST API của Property & Room (Sprint 1): CRUD, đổi trạng thái, thống kê. Qua APIClient + JWT giả lập."""
from decimal import Decimal
from unittest import mock

import requests
from django.test import TestCase
from rest_framework import status

from common.testing import fake_http_response, jwt_client
from services.property_service.models import MaintenanceRequest, Property, PropertyStatus, Room, RoomStatus
from ..unit_tests.base import OTHER_OWNER_ID, OWNER_ID, make_property, make_room


class ApiBase(TestCase):
    def setUp(self):
        patcher = mock.patch('common.service_client.requests.get', return_value=fake_http_response(200, []))
        self.external_api_mock = patcher.start()
        self.addCleanup(patcher.stop)
        self.client = jwt_client(OWNER_ID, 'LANDLORD')
        self.prop = make_property(code='NT100', name='Nhà trọ Thử Nghiệm', total_floors=2)
        self.room = make_room(self.prop, room_number='101', rent_price=3000000)

    def other_property(self):
        return make_property(owner_id=OTHER_OWNER_ID, name='Nhà người khác', code='OTH')


class PropertyApiTests(ApiBase):
    def test_list_returns_own_properties_with_expected_structure(self):
        """S2-API-001 | GET /api/properties/ | Data: landlord 101 có 1 nhà | Expected: 200, list 1 phần tử có id/code/name/full_address/status/total_rooms_count"""
        res = self.client.get('/api/properties/')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        for key in ('id', 'code', 'name', 'full_address', 'status', 'total_rooms_count', 'rooms', 'owner_id'):
            self.assertIn(key, res.data[0])

    def test_list_excludes_soft_deleted_by_default(self):
        """S2-API-002 | Danh sách ẩn nhà đã xóa mềm | Data: 1 nhà DELETED | Expected: chỉ trả nhà chưa DELETED"""
        make_property(code='GONE', status=PropertyStatus.DELETED)
        res = self.client.get('/api/properties/')
        self.assertEqual([p['code'] for p in res.data], ['NT100'])

    def test_retrieve_property(self):
        """S2-API-003 | GET /api/properties/{id}/ | Data: id hợp lệ | Expected: 200, đúng id/name, rooms lồng nhau 1 phòng"""
        res = self.client.get(f'/api/properties/{self.prop.id}/')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['name'], 'Nhà trọ Thử Nghiệm')
        self.assertEqual(len(res.data['rooms']), 1)

    def test_retrieve_nonexistent_property_returns_404(self):
        """S2-API-004 | Property không tồn tại | Data: id=999999 | Expected: 404"""
        self.assertEqual(self.client.get('/api/properties/999999/').status_code, status.HTTP_404_NOT_FOUND)

    def test_retrieve_soft_deleted_property_still_works(self):
        """S2-API-005 | Xem chi tiết nhà đã xóa mềm | Data: nhà DELETED | Expected: 200, status=DELETED (chỉ list mới ẩn)"""
        self.prop.status = PropertyStatus.DELETED
        self.prop.save()
        res = self.client.get(f'/api/properties/{self.prop.id}/')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['status'], 'DELETED')

    def test_create_property_success(self):
        """S2-API-006 | POST /api/properties/ hợp lệ | Data: name, address, district + owner_id=999 | Expected: 201, owner_id=101 (từ JWT), code 'NT...', lưu DB"""
        res = self.client.post('/api/properties/', {'name': 'Nhà Mới', 'address': '2 Phố B', 'district': 'Quận 7',
                                                    'owner_id': 999}, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED, res.data)
        self.assertEqual(res.data['owner_id'], OWNER_ID)
        self.assertTrue(res.data['code'].startswith('NT'))
        self.assertTrue(Property.objects.filter(name='Nhà Mới').exists())

    def test_create_property_missing_fields_returns_400(self):
        """S2-API-007 | POST thiếu trường bắt buộc | Data: {} | Expected: 400, lỗi 'name' và 'address'; không tạo bản ghi"""
        before = Property.objects.count()
        res = self.client.post('/api/properties/', {}, format='json')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue({'name', 'address'} <= set(res.data))
        self.assertEqual(Property.objects.count(), before)

    def test_create_property_invalid_status_returns_400(self):
        """S2-API-008 | POST status sai | Data: status='BOGUS' | Expected: 400, lỗi 'status'"""
        res = self.client.post('/api/properties/', {'name': 'A', 'address': 'a', 'status': 'BOGUS'}, format='json')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('status', res.data)

    def test_create_property_duplicate_code_returns_400(self):
        """S2-API-009 | POST code trùng | Data: code='NT100' đã có | Expected: 400, lỗi 'code'"""
        res = self.client.post('/api/properties/', {'name': 'A', 'address': 'a', 'code': 'NT100'}, format='json')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('code', res.data)

    def test_put_property_full_update(self):
        """S2-API-010 | PUT cập nhật đầy đủ | Data: name, address mới | Expected: 200, DB cập nhật"""
        res = self.client.put(f'/api/properties/{self.prop.id}/', {'name': 'Tên PUT', 'address': 'Địa chỉ PUT'},
                              format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK, res.data)
        self.prop.refresh_from_db()
        self.assertEqual((self.prop.name, self.prop.address), ('Tên PUT', 'Địa chỉ PUT'))

    def test_put_property_missing_required_returns_400(self):
        """S2-API-011 | PUT thiếu address | Data: chỉ name | Expected: 400, lỗi 'address'; DB không đổi"""
        res = self.client.put(f'/api/properties/{self.prop.id}/', {'name': 'Chỉ tên'}, format='json')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('address', res.data)
        self.prop.refresh_from_db()
        self.assertEqual(self.prop.name, 'Nhà trọ Thử Nghiệm')

    def test_patch_property_persists(self):
        """S2-API-012 | PATCH một phần | Data: name, total_floors=4 | Expected: 200, DB cập nhật, trường khác giữ nguyên"""
        res = self.client.patch(f'/api/properties/{self.prop.id}/', {'name': 'Tên Mới', 'total_floors': 4},
                                format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.prop.refresh_from_db()
        self.assertEqual((self.prop.name, self.prop.total_floors, self.prop.address), ('Tên Mới', 4, '1 Đường Test'))

    def test_patch_nonexistent_property_returns_404(self):
        """S2-API-013 | PATCH id không tồn tại | Data: id=999999 | Expected: 404"""
        res = self.client.patch('/api/properties/999999/', {'name': 'x'}, format='json')
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    def test_patch_property_invalid_status_returns_400(self):
        """S2-API-014 | PATCH status sai | Data: 'BOGUS' | Expected: 400; DB giữ ACTIVE"""
        res = self.client.patch(f'/api/properties/{self.prop.id}/', {'status': 'BOGUS'}, format='json')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.prop.refresh_from_db()
        self.assertEqual(self.prop.status, PropertyStatus.ACTIVE)

    def test_delete_empty_property_is_hard_delete(self):
        """S2-API-015 | DELETE nhà không có phòng | Data: nhà trống | Expected: 200, soft_deleted=False, bản ghi bị xóa"""
        empty = make_property(code='EMPTY', name='Trống')
        res = self.client.delete(f'/api/properties/{empty.id}/')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertFalse(res.data['soft_deleted'])
        self.assertFalse(Property.objects.filter(pk=empty.pk).exists())

    def test_delete_property_with_only_inactive_rooms_is_soft_delete(self):
        """S2-API-016 | DELETE nhà chỉ còn phòng INACTIVE | Data: nhà có 1 phòng INACTIVE | Expected: 200, soft_deleted=True, status=DELETED, phòng còn nguyên"""
        self.room.status = RoomStatus.INACTIVE
        self.room.save()
        res = self.client.delete(f'/api/properties/{self.prop.id}/')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertTrue(res.data['soft_deleted'])
        self.prop.refresh_from_db()
        self.assertEqual(self.prop.status, PropertyStatus.DELETED)
        self.assertEqual(Room.objects.filter(property=self.prop).count(), 1)

    def test_delete_property_with_rented_rooms_is_blocked(self):
        """S2-API-017 | DELETE nhà còn phòng đang thuê | Data: phòng OCCUPIED | Expected: 400 kèm 'error'; nhà vẫn ACTIVE"""
        self.room.status = RoomStatus.OCCUPIED
        self.room.current_occupants = 1
        self.room.save()
        res = self.client.delete(f'/api/properties/{self.prop.id}/')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', res.data)
        self.prop.refresh_from_db()
        self.assertEqual(self.prop.status, PropertyStatus.ACTIVE)

    def test_delete_property_with_full_rooms_is_blocked(self):
        """S2-API-018 | DELETE nhà có phòng FULL | Data: phòng FULL | Expected: 400 (FULL cũng là đang thuê)"""
        self.room.status = RoomStatus.FULL
        self.room.save()
        self.assertEqual(self.client.delete(f'/api/properties/{self.prop.id}/').status_code,
                         status.HTTP_400_BAD_REQUEST)

    def test_delete_property_with_active_rooms_is_blocked(self):
        """S2-API-064 | DELETE nhà còn phòng hoạt động | Data: phòng AVAILABLE (chưa thuê) | Expected: 400 kèm 'error'; nhà vẫn ACTIVE, phòng còn nguyên"""
        res = self.client.delete(f'/api/properties/{self.prop.id}/')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', res.data)
        self.prop.refresh_from_db()
        self.assertEqual(self.prop.status, PropertyStatus.ACTIVE)
        self.assertEqual(Room.objects.filter(property=self.prop).count(), 1)

    def test_update_status_to_deleted_with_active_rooms_is_blocked(self):
        """S2-API-065 | update_status=DELETED khi còn phòng hoạt động bị chặn (400), chỉ cho phép khi mọi phòng đã INACTIVE (200) | Data: phòng AVAILABLE -> INACTIVE | Expected: 400 rồi 200 DELETED"""
        res = self.client.post(f'/api/properties/{self.prop.id}/update_status/', {'status': 'DELETED'},
                               format='json')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.prop.refresh_from_db()
        self.assertEqual(self.prop.status, PropertyStatus.ACTIVE)

        self.room.status = RoomStatus.INACTIVE
        self.room.save()
        res_ok = self.client.post(f'/api/properties/{self.prop.id}/update_status/', {'status': 'DELETED'},
                                  format='json')
        self.assertEqual(res_ok.status_code, status.HTTP_200_OK)
        self.prop.refresh_from_db()
        self.assertEqual(self.prop.status, PropertyStatus.DELETED)

    def test_patch_and_put_property_status_deleted_with_active_rooms_is_blocked(self):
        """S2-API-068 | PATCH và PUT /properties/{id}/ với status='DELETED' khi còn phòng hoạt động | Data: nhà có 1 phòng AVAILABLE | Expected: 400 (lỗi 'status'), DB giữ ACTIVE; khi phòng đã INACTIVE thì PATCH/PUT status='DELETED' thành công (200)"""
        res_patch = self.client.patch(f'/api/properties/{self.prop.id}/', {'status': 'DELETED'}, format='json')
        self.assertEqual(res_patch.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('status', res_patch.data)

        put_payload = {
            'name': self.prop.name,
            'address': self.prop.address,
            'total_floors': self.prop.total_floors,
            'status': 'DELETED',
        }
        res_put = self.client.put(f'/api/properties/{self.prop.id}/', put_payload, format='json')
        self.assertEqual(res_put.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('status', res_put.data)
        self.prop.refresh_from_db()
        self.assertEqual(self.prop.status, PropertyStatus.ACTIVE)

        self.room.status = RoomStatus.INACTIVE
        self.room.save()
        res_ok = self.client.patch(f'/api/properties/{self.prop.id}/', {'status': 'DELETED'}, format='json')
        self.assertEqual(res_ok.status_code, status.HTTP_200_OK)
        self.prop.refresh_from_db()
        self.assertEqual(self.prop.status, PropertyStatus.DELETED)

    def test_delete_nonexistent_property_returns_404(self):
        """S2-API-019 | DELETE id không tồn tại | Data: id=999999 | Expected: 404"""
        self.assertEqual(self.client.delete('/api/properties/999999/').status_code, status.HTTP_404_NOT_FOUND)

    def test_update_status_action_persists(self):
        """S2-API-020 | POST update_status hợp lệ | Data: status='INACTIVE' | Expected: 200, DB INACTIVE, message + property trong response"""
        res = self.client.post(f'/api/properties/{self.prop.id}/update_status/', {'status': 'INACTIVE'},
                               format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['property']['status'], 'INACTIVE')
        self.prop.refresh_from_db()
        self.assertEqual(self.prop.status, PropertyStatus.INACTIVE)

    def test_update_status_accepts_lowercase(self):
        """S2-API-021 | update_status chấp nhận chữ thường | Data: 'inactive' | Expected: 200, lưu 'INACTIVE'"""
        res = self.client.post(f'/api/properties/{self.prop.id}/update_status/', {'status': 'inactive'},
                               format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.prop.refresh_from_db()
        self.assertEqual(self.prop.status, 'INACTIVE')

    def test_update_status_invalid_or_missing_returns_400(self):
        """S2-API-022 | update_status sai / thiếu | Data: 'BOGUS' và thiếu status | Expected: 400, 'error'; DB không đổi"""
        for payload in ({'status': 'BOGUS'}, {}):
            res = self.client.post(f'/api/properties/{self.prop.id}/update_status/', payload, format='json')
            self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertIn('error', res.data)
        self.prop.refresh_from_db()
        self.assertEqual(self.prop.status, PropertyStatus.ACTIVE)

    def test_update_status_nonexistent_returns_404(self):
        """S2-API-023 | update_status id không tồn tại | Data: id=999999 | Expected: 404"""
        res = self.client.post('/api/properties/999999/update_status/', {'status': 'INACTIVE'}, format='json')
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    def test_property_rooms_action_lists_rooms(self):
        """S2-API-024 | GET /properties/{id}/rooms/ | Data: 2 phòng (AVAILABLE, OCCUPIED) | Expected: 200, trả đủ 2 phòng của nhà"""
        make_room(self.prop, room_number='102', status='OCCUPIED', current_occupants=1)
        res = self.client.get(f'/api/properties/{self.prop.id}/rooms/')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(sorted(r['room_number'] for r in res.data), ['101', '102'])

    def test_property_rooms_action_filters_by_room_status(self):
        """S2-API-063 | GET /properties/{id}/rooms/?status=occupied | Data: 2 phòng (AVAILABLE, OCCUPIED) | Expected: 200, chỉ phòng '102'"""
        make_room(self.prop, room_number='102', status='OCCUPIED', current_occupants=1)
        res = self.client.get(f'/api/properties/{self.prop.id}/rooms/?status=occupied')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual([r['room_number'] for r in res.data], ['102'])

    def test_property_stats_values(self):
        """S2-API-025 | GET /properties/{id}/stats/ | Data: AVAILABLE 3tr, OCCUPIED 4tr, FULL 5tr, MAINTENANCE | Expected: total=4, occupancy=50.0, doanh thu=9,000,000"""
        make_room(self.prop, room_number='102', rent_price=4000000, status='OCCUPIED', current_occupants=1)
        make_room(self.prop, room_number='103', rent_price=5000000, status='FULL', current_occupants=2)
        make_room(self.prop, room_number='104', status='MAINTENANCE')
        res = self.client.get(f'/api/properties/{self.prop.id}/stats/')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['total_rooms'], 4)
        self.assertEqual(res.data['available_rooms'], 1)
        self.assertEqual(res.data['occupancy_rate_percent'], 50.0)
        self.assertEqual(Decimal(str(res.data['estimated_monthly_revenue'])), Decimal('9000000'))

    def test_property_stats_empty_property_has_zero_rate(self):
        """S2-API-026 | stats nhà chưa có phòng | Data: nhà trống | Expected: total=0, occupancy=0.0, doanh thu=0"""
        empty = make_property(code='E2', name='Trống 2')
        res = self.client.get(f'/api/properties/{empty.id}/stats/')
        self.assertEqual((res.data['total_rooms'], res.data['occupancy_rate_percent']), (0, 0.0))
        self.assertEqual(res.data['estimated_monthly_revenue'], 0)

    def test_room_matrix_groups_by_floor(self):
        """S2-API-027 | GET /properties/{id}/room_matrix/ | Data: phòng tầng 2, tầng 1 | Expected: floors sắp tăng dần ('Tầng 1','Tầng 2'), status_summary đủ 6 trạng thái, total_rooms đúng"""
        make_room(self.prop, room_number='201', floor=2)
        res = self.client.get(f'/api/properties/{self.prop.id}/room_matrix/')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual([f['floor_name'] for f in res.data['floors']], ['Tầng 1', 'Tầng 2'])
        self.assertEqual(set(res.data['status_summary']), set(RoomStatus.values))
        self.assertEqual(res.data['total_rooms'], 2)
        self.assertEqual(res.data['status_summary']['AVAILABLE'], 2)

    def test_summary_counts_for_landlord_scope(self):
        """S2-API-028 | GET /properties/summary/ | Data: 4 phòng AVAILABLE/OCCUPIED/FULL/MAINTENANCE + nhà người khác | Expected: total_rooms=4 (chỉ của mình), occupied=2, full=1, maintenance=1, rate=50.0"""
        make_room(self.prop, room_number='102', status='OCCUPIED', current_occupants=1)
        make_room(self.prop, room_number='103', status='FULL', current_occupants=2)
        make_room(self.prop, room_number='104', status='MAINTENANCE')
        make_room(self.other_property(), room_number='X', status='OCCUPIED')
        res = self.client.get('/api/properties/summary/')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual((res.data['total_properties'], res.data['total_rooms']), (1, 4))
        self.assertEqual((res.data['occupied_rooms'], res.data['full_rooms'], res.data['maintenance_rooms']),
                         (2, 1, 1))
        self.assertEqual(res.data['occupancy_rate_percent'], 50.0)

    def test_summary_excludes_soft_deleted_properties(self):
        """S2-API-029 | summary bỏ qua nhà đã xóa mềm | Data: nhà DELETED có phòng | Expected: không tính vào total_properties/total_rooms"""
        gone = make_property(code='GONE', status=PropertyStatus.DELETED)
        make_room(gone, room_number='G1')
        res = self.client.get('/api/properties/summary/')
        self.assertEqual((res.data['total_properties'], res.data['total_rooms']), (1, 1))

    def test_summary_total_properties_counts_only_active(self):
        """S2-API-066 | summary.total_properties chỉ đếm nhà đang vận hành | Data: 1 ACTIVE + 1 INACTIVE + 1 DELETED | Expected: total_properties=1"""
        make_property(code='PAUSED', status=PropertyStatus.INACTIVE)
        make_property(code='GONE', status=PropertyStatus.DELETED)
        res = self.client.get('/api/properties/summary/')
        self.assertEqual(res.data['total_properties'], 1)


class RoomApiTests(ApiBase):
    def test_list_rooms_excludes_rooms_of_deleted_property(self):
        """S2-API-067 | GET /api/rooms/ ẩn phòng của nhà đã xóa | Data: nhà B DELETED còn phòng AVAILABLE | Expected: 200, không có phòng của B ở list/available (không phòng mồ côi); xem chi tiết theo id vẫn 200"""
        gone = make_property(code='GONE', status=PropertyStatus.DELETED)
        orphan = make_room(gone, room_number='G1')
        res = self.client.get('/api/rooms/')
        self.assertEqual([r['room_number'] for r in res.data], ['101'])
        res = self.client.get('/api/rooms/available/')
        self.assertEqual([r['room_number'] for r in res.data], ['101'])
        self.assertEqual(self.client.get(f'/api/rooms/{orphan.id}/').status_code, status.HTTP_200_OK)

    def test_list_rooms(self):
        """S2-API-030 | GET /api/rooms/ | Data: 1 phòng | Expected: 200, 1 phần tử có room_number/code/rent_price/status/is_rentable"""
        res = self.client.get('/api/rooms/')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        for key in ('id', 'code', 'room_number', 'rent_price', 'status', 'is_rentable', 'property_name'):
            self.assertIn(key, res.data[0])

    def test_retrieve_room_and_404(self):
        """S2-API-031 | GET /api/rooms/{id}/ | Data: id hợp lệ và 999999 | Expected: 200 đúng dữ liệu; 404 khi không tồn tại"""
        res = self.client.get(f'/api/rooms/{self.room.id}/')
        self.assertEqual((res.status_code, res.data['room_number']), (200, '101'))
        self.assertEqual(self.client.get('/api/rooms/999999/').status_code, status.HTTP_404_NOT_FOUND)

    def test_create_room_success(self):
        """S2-API-032 | POST /api/rooms/ hợp lệ | Data: property, room_number='102', area, rent_price | Expected: 201, code='NT100-102', status=AVAILABLE, lưu DB"""
        res = self.client.post('/api/rooms/', {'property': self.prop.id, 'room_number': '102', 'floor': 1,
                                               'area': 22.5, 'rent_price': 3500000, 'max_occupants': 2},
                               format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED, res.data)
        self.assertEqual(res.data['code'], 'NT100-102')
        self.assertEqual(res.data['status'], 'AVAILABLE')
        self.assertTrue(Room.objects.filter(room_number='102', property=self.prop).exists())

    def test_create_room_missing_fields_returns_400(self):
        """S2-API-033 | POST phòng thiếu trường | Data: {} | Expected: 400, lỗi property/room_number/rent_price"""
        res = self.client.post('/api/rooms/', {}, format='json')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue({'property', 'room_number', 'rent_price'} <= set(res.data))

    def test_create_room_nonexistent_property_returns_400(self):
        """S2-API-034 | POST phòng vào nhà không tồn tại | Data: property=999999 | Expected: 400, lỗi 'property'"""
        res = self.client.post('/api/rooms/', {'property': 999999, 'room_number': 'X', 'rent_price': 1},
                               format='json')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('property', res.data)

    def test_create_room_in_other_landlords_property_returns_400(self):
        """S2-API-035 | POST phòng vào nhà của chủ khác | Data: property của owner 202 | Expected: 400 lỗi 'property'; không tạo phòng"""
        other = self.other_property()
        res = self.client.post('/api/rooms/', {'property': other.id, 'room_number': 'X', 'rent_price': 1},
                               format='json')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('property', res.data)
        self.assertFalse(Room.objects.filter(property=other).exists())

    def test_create_room_invalid_values_return_400(self):
        """S2-API-036 | POST phòng dữ liệu sai | Data: status='BOGUS'; current(3)>max(2); max_occupants=-1 | Expected: 400 cho từng trường hợp"""
        base = {'property': self.prop.id, 'room_number': 'Z', 'rent_price': 1}
        for extra, field in (({'status': 'BOGUS'}, 'status'),
                             ({'current_occupants': 3, 'max_occupants': 2}, 'current_occupants'),
                             ({'max_occupants': -1}, 'max_occupants')):
            with self.subTest(field=field):
                res = self.client.post('/api/rooms/', {**base, **extra}, format='json')
                self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
                self.assertIn(field, res.data)

    def test_create_room_negative_price_returns_400(self):
        """S2-API-037 | POST phòng giá âm | Data: rent_price=-100 | Expected: 400 lỗi 'rent_price'"""
        res = self.client.post('/api/rooms/', {'property': self.prop.id, 'room_number': 'NEG', 'rent_price': -100},
                               format='json')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_put_room_full_update(self):
        """S2-API-038 | PUT cập nhật phòng | Data: đủ trường bắt buộc, rent_price mới | Expected: 200, DB cập nhật"""
        res = self.client.put(f'/api/rooms/{self.room.id}/', {'property': self.prop.id, 'room_number': '101',
                                                              'rent_price': 4200000}, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK, res.data)
        self.room.refresh_from_db()
        self.assertEqual(self.room.rent_price, 4200000)

    def test_patch_room_persists(self):
        """S2-API-039 | PATCH phòng | Data: area=25, room_number='101-VIP' | Expected: 200, DB cập nhật"""
        res = self.client.patch(f'/api/rooms/{self.room.id}/', {'area': 25, 'room_number': '101-VIP'}, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.room.refresh_from_db()
        self.assertEqual((self.room.area, self.room.room_number), (25, '101-VIP'))

    def test_patch_room_nonexistent_returns_404(self):
        """S2-API-040 | PATCH phòng không tồn tại | Data: id=999999 | Expected: 404"""
        self.assertEqual(self.client.patch('/api/rooms/999999/', {'area': 1}, format='json').status_code, 404)

    def test_patch_room_occupants_over_max_returns_400(self):
        """S2-API-041 | PATCH current_occupants vượt max | Data: current=5, max=2 | Expected: 400; DB giữ 0"""
        res = self.client.patch(f'/api/rooms/{self.room.id}/', {'current_occupants': 5}, format='json')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.room.refresh_from_db()
        self.assertEqual(self.room.current_occupants, 0)

    def test_move_room_to_other_landlords_property_returns_400(self):
        """S2-API-042 | PATCH chuyển phòng sang nhà chủ khác | Data: property=nhà owner 202 | Expected: 400; phòng giữ nhà cũ"""
        other = self.other_property()
        res = self.client.patch(f'/api/rooms/{self.room.id}/', {'property': other.id}, format='json')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.room.refresh_from_db()
        self.assertEqual(self.room.property_id, self.prop.id)

    def test_delete_room_without_history_is_hard_delete(self):
        """S2-API-043 | DELETE phòng trống chưa có lịch sử | Data: phòng AVAILABLE | Expected: 200, soft_deleted=False, bản ghi bị xóa"""
        res = self.client.delete(f'/api/rooms/{self.room.id}/')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertFalse(res.data['soft_deleted'])
        self.assertFalse(Room.objects.filter(pk=self.room.pk).exists())

    def test_delete_room_with_maintenance_history_is_soft_delete(self):
        """S2-API-044 | DELETE phòng đã có yêu cầu bảo trì | Data: 1 MaintenanceRequest | Expected: 200, soft_deleted=True, status=INACTIVE, bản ghi còn"""
        MaintenanceRequest.objects.create(room=self.room, title='Hỏng đèn')
        res = self.client.delete(f'/api/rooms/{self.room.id}/')
        self.assertTrue(res.data['soft_deleted'])
        self.room.refresh_from_db()
        self.assertEqual(self.room.status, RoomStatus.INACTIVE)

    def test_delete_rented_room_is_blocked(self):
        """S2-API-045 | DELETE phòng đang thuê hoặc đã đặt cọc | Data: OCCUPIED, FULL, RESERVED, hoặc có người ở | Expected: 400 'error'; phòng còn nguyên"""
        for kwargs in ({'status': 'OCCUPIED'}, {'status': 'FULL'}, {'status': 'RESERVED'}, {'current_occupants': 1}):
            with self.subTest(**kwargs):
                room = make_room(self.prop, room_number=f"D-{sorted(kwargs.items())}", **kwargs)
                res = self.client.delete(f'/api/rooms/{room.id}/')
                self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
                self.assertIn('error', res.data)
                self.assertTrue(Room.objects.filter(pk=room.pk).exists())

    def test_create_and_update_duplicate_room_number_in_same_property_returns_400(self):
        """S2-API-069 | POST và PATCH /api/rooms/ trùng room_number trong cùng Property | Data: tạo/đổi tên phòng thành '101' hoặc '101' hoa-thường trong self.prop vs nhà trọ khác | Expected: 400 (lỗi 'room_number') khi cùng nhà; 201 khi khác nhà"""
        res_dup = self.client.post('/api/rooms/', {
            'property': self.prop.id,
            'room_number': '101',
            'rent_price': 3200000,
        }, format='json')
        self.assertEqual(res_dup.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('room_number', res_dup.data)

        r2 = make_room(self.prop, room_number='102', rent_price=3200000)
        res_patch_dup = self.client.patch(f'/api/rooms/{r2.id}/', {'room_number': '101'}, format='json')
        self.assertEqual(res_patch_dup.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('room_number', res_patch_dup.data)
        r2.refresh_from_db()
        self.assertEqual(r2.room_number, '102')

        prop2 = make_property(code='NT200', name='Nhà trọ 2')
        res_other_prop = self.client.post('/api/rooms/', {
            'property': prop2.id,
            'room_number': '101',
            'rent_price': 3200000,
        }, format='json')
        self.assertEqual(res_other_prop.status_code, status.HTTP_201_CREATED, res_other_prop.data)

    def test_delete_room_blocked_by_external_tenant_or_contract_links(self):
        """S2-API-070 | DELETE /api/rooms/{id}/ kiểm tra liên kết khách thuê (Tenant Service) và hợp đồng (Contract Service) | Data: phòng AVAILABLE nhưng còn tenant ACTIVE, contract ACTIVE/DRAFT/EXTENDED, lỗi kết nối 503, và trường hợp đã MOVED_OUT + TERMINATED | Expected: 400 khi còn liên kết, 503 khi mất kết nối, 200 khi đã kết thúc"""
        self.external_api_mock.side_effect = [
            fake_http_response(200, [{'tenant_id': 1, 'user_id': 555, 'room_id': self.room.id, 'status': 'ACTIVE'}]),
        ]
        res_tenant = self.client.delete(f'/api/rooms/{self.room.id}/')
        self.assertEqual(res_tenant.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('hồ sơ khách thuê', res_tenant.data['error'])
        self.assertTrue(Room.objects.filter(pk=self.room.pk).exists())

        self.external_api_mock.side_effect = [
            fake_http_response(200, []),
            fake_http_response(200, [{'id': 11, 'room_id': self.room.id, 'status': 'ACTIVE'}]),
        ]
        res_contract = self.client.delete(f'/api/rooms/{self.room.id}/')
        self.assertEqual(res_contract.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('hợp đồng', res_contract.data['error'])
        self.assertTrue(Room.objects.filter(pk=self.room.pk).exists())

        self.external_api_mock.side_effect = requests.exceptions.ConnectionError('down')
        res_down = self.client.delete(f'/api/rooms/{self.room.id}/')
        self.assertEqual(res_down.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
        self.assertTrue(Room.objects.filter(pk=self.room.pk).exists())

        self.external_api_mock.side_effect = [
            fake_http_response(200, [{'tenant_id': 1, 'room_id': self.room.id, 'status': 'MOVED_OUT'}]),
            fake_http_response(200, [{'id': 11, 'room_id': self.room.id, 'status': 'TERMINATED'}]),
        ]
        res_ok = self.client.delete(f'/api/rooms/{self.room.id}/')
        self.assertEqual(res_ok.status_code, status.HTTP_200_OK)
        self.assertFalse(Room.objects.filter(pk=self.room.pk).exists())

    def test_room_business_constraints_on_deleted_property_floor_bounds_and_status_sync(self):
        """S2-API-071 | Kiểm tra ràng buộc nghiệp vụ khi tạo/cập nhật phòng qua POST/PATCH /api/rooms/: chặn nhà trọ DELETED, chặn tầng ngoài 1..total_floors, chặn giảm total_floors nhà trọ thấp hơn tầng phòng hiện có, chặn đặt INACTIVE khi đang có khách thuê, và đồng bộ current_occupants theo status | Data: property DELETED, floor=0/5 (total_floors=2), PATCH status=OCCUPIED/INACTIVE/AVAILABLE | Expected: 400 khi vi phạm; 200 và đồng bộ đúng khi hợp lệ"""
        gone = make_property(code='GONE-P', status=PropertyStatus.DELETED, total_floors=2)
        res_del_prop = self.client.post('/api/rooms/', {
            'property': gone.id, 'room_number': '101', 'rent_price': 3000000,
        }, format='json')
        self.assertEqual(res_del_prop.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('property', res_del_prop.data)

        for bad_floor in (0, 3):
            res_floor = self.client.post('/api/rooms/', {
                'property': self.prop.id, 'room_number': f'F{bad_floor}', 'floor': bad_floor, 'rent_price': 3000000,
            }, format='json')
            self.assertEqual(res_floor.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertIn('floor', res_floor.data)

        r_f2 = make_room(self.prop, room_number='201', floor=2)
        res_shrink = self.client.patch(f'/api/properties/{self.prop.id}/', {'total_floors': 1}, format='json')
        self.assertEqual(res_shrink.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('total_floors', res_shrink.data)

        res_occ = self.client.patch(f'/api/rooms/{r_f2.id}/', {'status': 'OCCUPIED'}, format='json')
        self.assertEqual(res_occ.status_code, status.HTTP_200_OK)
        r_f2.refresh_from_db()
        self.assertEqual((r_f2.status, r_f2.current_occupants), (RoomStatus.OCCUPIED, 1))

        res_inact_bad = self.client.patch(f'/api/rooms/{r_f2.id}/', {'status': 'INACTIVE'}, format='json')
        self.assertEqual(res_inact_bad.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('status', res_inact_bad.data)

        res_avail = self.client.patch(f'/api/rooms/{r_f2.id}/', {'status': 'AVAILABLE'}, format='json')
        self.assertEqual(res_avail.status_code, status.HTTP_200_OK)
        r_f2.refresh_from_db()
        self.assertEqual((r_f2.status, r_f2.current_occupants), (RoomStatus.AVAILABLE, 0))

    def test_delete_nonexistent_room_returns_404(self):
        """S2-API-046 | DELETE phòng không tồn tại | Data: id=999999 | Expected: 404"""
        self.assertEqual(self.client.delete('/api/rooms/999999/').status_code, status.HTTP_404_NOT_FOUND)

    def test_get_room_status_detail(self):
        """S2-API-047 | GET /rooms/{id}/status/ | Data: phòng AVAILABLE | Expected: 200, status, status_display, is_rentable=True, rentability_reason"""
        res = self.client.get(f'/api/rooms/{self.room.id}/status/')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual((res.data['status'], res.data['is_rentable']), ('AVAILABLE', True))
        for key in ('status_display', 'rentability_reason', 'current_occupants', 'max_occupants'):
            self.assertIn(key, res.data)

    def test_set_status_occupied_defaults_one_occupant(self):
        """S2-API-048 | PATCH status=OCCUPIED không truyền người ở | Data: phòng trống | Expected: 200, status OCCUPIED, current_occupants=1"""
        res = self.client.patch(f'/api/rooms/{self.room.id}/status/', {'status': 'OCCUPIED'}, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.room.refresh_from_db()
        self.assertEqual((self.room.status, self.room.current_occupants), (RoomStatus.OCCUPIED, 1))

    def test_set_status_occupied_at_capacity_becomes_full(self):
        """S2-API-049 | OCCUPIED với số người = max | Data: current_occupants=2, max=2 | Expected: tự chuyển FULL"""
        self.client.post(f'/api/rooms/{self.room.id}/status/', {'status': 'OCCUPIED', 'current_occupants': 2},
                         format='json')
        self.room.refresh_from_db()
        self.assertEqual(self.room.status, RoomStatus.FULL)

    def test_set_status_full_sets_occupants_to_max(self):
        """S2-API-050 | status=FULL | Data: phòng max=2 | Expected: current_occupants=2"""
        self.client.post(f'/api/rooms/{self.room.id}/status/', {'status': 'FULL'}, format='json')
        self.room.refresh_from_db()
        self.assertEqual((self.room.status, self.room.current_occupants), (RoomStatus.FULL, 2))

    def test_set_status_available_resets_occupants_and_tenant(self):
        """S2-API-051 | status=AVAILABLE dọn thông tin người thuê | Data: phòng OCCUPIED có tenant_name/phone | Expected: current_occupants=0, tenant_name='' và tenant_phone=''"""
        self.room.status, self.room.current_occupants = RoomStatus.OCCUPIED, 1
        self.room.tenant_name, self.room.tenant_phone = 'Nguyễn A', '0900'
        self.room.save()
        self.client.post(f'/api/rooms/{self.room.id}/status/', {'status': 'AVAILABLE'}, format='json')
        self.room.refresh_from_db()
        self.assertEqual((self.room.status, self.room.current_occupants), (RoomStatus.AVAILABLE, 0))
        self.assertEqual((self.room.tenant_name, self.room.tenant_phone), ('', ''))

    def test_set_status_updates_tenant_info(self):
        """S2-API-052 | Cập nhật tenant_name/tenant_phone qua status | Data: OCCUPIED + tenant_name | Expected: lưu DB"""
        self.client.post(f'/api/rooms/{self.room.id}/status/',
                         {'status': 'OCCUPIED', 'tenant_name': 'Trần B', 'tenant_phone': '0911'}, format='json')
        self.room.refresh_from_db()
        self.assertEqual((self.room.tenant_name, self.room.tenant_phone), ('Trần B', '0911'))

    def test_set_each_valid_status(self):
        """S2-API-053 | Chuyển tới mọi trạng thái hợp lệ | Data: 6 trạng thái | Expected: 200 và status lưu đúng (OCCUPIED có thể thành FULL nếu đủ chỗ; INACTIVE chỉ cho phép khi phòng không đang thuê)"""
        for st in (RoomStatus.AVAILABLE, RoomStatus.RESERVED, RoomStatus.MAINTENANCE, RoomStatus.INACTIVE,
                   RoomStatus.OCCUPIED, RoomStatus.FULL):
            with self.subTest(status=st):
                res = self.client.post(f'/api/rooms/{self.room.id}/status/', {'status': st}, format='json')
                self.assertEqual(res.status_code, status.HTTP_200_OK, res.data)
                self.room.refresh_from_db()
                self.assertEqual(self.room.status, st)

        res_blocked = self.client.post(f'/api/rooms/{self.room.id}/status/', {'status': RoomStatus.INACTIVE},
                                       format='json')
        self.assertEqual(res_blocked.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', res_blocked.data)

    def test_set_status_invalid_returns_400_with_allowed_list(self):
        """S2-API-054 | status không hợp lệ | Data: 'BOGUS' và thiếu | Expected: 400, có 'allowed_statuses'; DB không đổi"""
        for payload in ({'status': 'BOGUS'}, {}):
            res = self.client.post(f'/api/rooms/{self.room.id}/status/', payload, format='json')
            self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertIn('allowed_statuses', res.data)
        self.room.refresh_from_db()
        self.assertEqual(self.room.status, RoomStatus.AVAILABLE)

    def test_set_status_occupants_boundaries(self):
        """S2-API-055 | Biên current_occupants khi đổi trạng thái | Data: -1, max+1 | Expected: 400; 0 và max chấp nhận (200)"""
        url = f'/api/rooms/{self.room.id}/status/'
        for bad in (-1, 3):
            res = self.client.post(url, {'status': 'RESERVED', 'current_occupants': bad}, format='json')
            self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST, bad)
        for ok in (0, 2):
            res = self.client.post(url, {'status': 'RESERVED', 'current_occupants': ok}, format='json')
            self.assertEqual(res.status_code, status.HTTP_200_OK, ok)

    def test_set_status_non_numeric_occupants_returns_400(self):
        """S2-API-056 | current_occupants không phải số | Data: 'abc' | Expected: 400 (không phải 500)"""
        res = self.client.post(f'/api/rooms/{self.room.id}/status/',
                               {'status': 'OCCUPIED', 'current_occupants': 'abc'}, format='json')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_set_status_nonexistent_room_returns_404(self):
        """S2-API-057 | Đổi trạng thái phòng không tồn tại | Data: id=999999 | Expected: 404"""
        res = self.client.post('/api/rooms/999999/status/', {'status': 'AVAILABLE'}, format='json')
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    def test_check_rentable_response_structure_and_values(self):
        """S2-API-058 | GET /rooms/{id}/check_rentable/ | Data: phòng trống rồi chuyển OCCUPIED | Expected: can_rent True->False, có room_id/code/property_name/reason/rent_price/area"""
        res = self.client.get(f'/api/rooms/{self.room.id}/check_rentable/')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        for key in ('room_id', 'code', 'room_number', 'property_name', 'status', 'can_rent', 'reason',
                    'rent_price', 'area', 'max_occupants', 'current_occupants'):
            self.assertIn(key, res.data)
        self.assertTrue(res.data['can_rent'])
        self.room.status = RoomStatus.OCCUPIED
        self.room.save()
        res = self.client.get(f'/api/rooms/{self.room.id}/check_rentable/')
        self.assertFalse(res.data['can_rent'])

    def test_check_rentable_nonexistent_returns_404(self):
        """S2-API-059 | check_rentable phòng không tồn tại | Data: id=999999 | Expected: 404"""
        self.assertEqual(self.client.get('/api/rooms/999999/check_rentable/').status_code, 404)

    def test_available_occupied_maintenance_lists(self):
        """S2-API-060 | Danh sách phòng theo trạng thái | Data: AVAILABLE, OCCUPIED, FULL, MAINTENANCE | Expected: /available/=1, /occupied/=2 (OCCUPIED+FULL), /maintenance/=1"""
        make_room(self.prop, room_number='102', status='OCCUPIED', current_occupants=1)
        make_room(self.prop, room_number='103', status='FULL', current_occupants=2)
        make_room(self.prop, room_number='104', status='MAINTENANCE')
        self.assertEqual([r['room_number'] for r in self.client.get('/api/rooms/available/').data], ['101'])
        self.assertEqual({r['room_number'] for r in self.client.get('/api/rooms/occupied/').data}, {'102', '103'})
        self.assertEqual([r['room_number'] for r in self.client.get('/api/rooms/maintenance/').data], ['104'])

    def test_room_response_is_json_with_private_fields_for_manager(self):
        """S2-API-061 | Định dạng response & dữ liệu riêng tư cho chủ trọ | Data: phòng có tenant_phone | Expected: Content-Type JSON; tenant_phone hiển thị"""
        self.room.tenant_phone = '0900000000'
        self.room.save()
        res = self.client.get(f'/api/rooms/{self.room.id}/')
        self.assertTrue(res['Content-Type'].startswith('application/json'))
        self.assertEqual(res.data['tenant_phone'], '0900000000')

    def test_health_endpoint_is_public(self):
        """S2-API-062 | GET /health/ không cần token | Data: client ẩn danh | Expected: 200, service key=property, port=8002, status=UP"""
        from rest_framework.test import APIClient
        res = APIClient().get('/health/')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual((res.data['key'], res.data['port'], res.data['status']), ('property', 8002, 'UP'))

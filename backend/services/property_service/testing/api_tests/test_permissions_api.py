"""[API/SECURITY] JWT Authentication & Role-Based Access Control (RBAC) API Tests for Service 2.

Moved from `testing/unit_tests/test_permissions.py` into `testing/api_tests/test_permissions_api.py`
so that Pure Unit Tests and API/HTTP Tests are cleanly separated by both directory and test class.
Contains 25 API/Security tests (`S2-SEC-009`..`S2-SEC-017`, `S2-SEC-019`..`S2-SEC-034`, including migrated `S2-LEG-029` & `S2-LEG-033`; `S2-SEC-018` moved to `unit_tests/test_permissions.py`).
"""
from datetime import timedelta
from unittest import mock

import jwt as pyjwt
import requests
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken

from common.testing import fake_http_response, jwt_client, make_access_token, patch_tenant_links, tenant_link
from services.property_service.models import MaintenanceRequest, MaintenanceStatus, Property, Room, RoomStatus
from ..unit_tests.base import (
    OTHER_OWNER_ID,
    OWNER_ID,
    TENANT_USER_ID,
    make_property,
    make_room,
    patch_rented_rooms,
)


def bearer_client(token_value, scheme='Bearer'):
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f'{scheme} {token_value}')
    return client


class JwtAuthenticationApiTests(TestCase):
    """[API/SECURITY] Xác thực JWT cho endpoint của Service 2."""

    def setUp(self):
        self.prop = make_property()
        self.room = make_room(self.prop)

    def assert_401(self, client):
        for url in ('/api/properties/', f'/api/properties/{self.prop.id}/', '/api/rooms/',
                    f'/api/rooms/{self.room.id}/'):
            res = client.get(url)
            self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED, url)

    def test_no_authorization_header_returns_401(self):
        """S2-SEC-009 | Không có Authorization header | Data: GET list/detail properties & rooms | Expected: 401 cho tất cả"""
        self.assert_401(APIClient())

    def test_unauthenticated_write_returns_401_and_creates_nothing(self):
        """S2-SEC-010 | Ghi dữ liệu khi chưa đăng nhập | Data: POST/PATCH/DELETE không token | Expected: 401; DB không đổi"""
        anon = APIClient()
        self.assertEqual(anon.post('/api/properties/', {'name': 'x', 'address': 'y'}, format='json').status_code, 401)
        self.assertEqual(anon.patch(f'/api/rooms/{self.room.id}/', {'area': 1}, format='json').status_code, 401)
        self.assertEqual(anon.delete(f'/api/properties/{self.prop.id}/').status_code, 401)
        self.assertEqual(Property.objects.count(), 1)

    def test_expired_token_returns_401(self):
        """S2-SEC-011 | JWT hết hạn | Data: access token exp trong quá khứ | Expected: 401"""
        token = AccessToken()
        token['user_id'] = OWNER_ID
        token['role'] = 'LANDLORD'
        token.set_exp(lifetime=-timedelta(seconds=30))
        self.assert_401(bearer_client(str(token)))

    def test_malformed_token_returns_401(self):
        """S2-SEC-012 | JWT sai định dạng | Data: 'not.a.jwt', 'abc', ký tự lạ | Expected: 401"""
        for garbage in ('not.a.jwt', 'abc', 'a.b.c.d', '###'):
            self.assert_401(bearer_client(garbage))

    def test_token_with_wrong_signature_returns_401(self):
        """S2-SEC-013 | JWT ký bằng khóa khác | Data: HS256 với 'wrong-key' | Expected: 401"""
        payload = {'token_type': 'access', 'user_id': OWNER_ID, 'role': 'ADMIN', 'jti': 'x',
                   'exp': 4102444800}
        forged = pyjwt.encode(payload, 'wrong-key-wrong-key-wrong-key-123456', algorithm='HS256')
        self.assert_401(bearer_client(forged))

    def test_wrong_scheme_and_empty_bearer_return_401(self):
        """S2-SEC-014 | Sai scheme / Bearer rỗng | Data: 'Token <jwt>', 'Bearer ' | Expected: 401"""
        valid = make_access_token(OWNER_ID, 'LANDLORD')
        self.assert_401(bearer_client(valid, scheme='Token'))
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION='Bearer ')
        self.assert_401(client)

    def test_refresh_token_cannot_be_used_as_access_token(self):
        """S2-SEC-015 | Dùng refresh token làm access | Data: RefreshToken hợp lệ | Expected: 401"""
        refresh = RefreshToken()
        refresh['user_id'] = OWNER_ID
        refresh['role'] = 'ADMIN'
        self.assert_401(bearer_client(str(refresh)))

    def test_token_without_user_id_claim_returns_401(self):
        """S2-SEC-016 | JWT thiếu claim user_id | Data: access token không có user_id | Expected: 401"""
        token = AccessToken()
        token['role'] = 'ADMIN'
        self.assert_401(bearer_client(str(token)))

    def test_valid_token_is_accepted(self):
        """S2-SEC-017 | JWT hợp lệ | Data: access token landlord 101 | Expected: 200 trên list/detail"""
        client = jwt_client(OWNER_ID, 'LANDLORD')
        self.assertEqual(client.get('/api/properties/').status_code, status.HTTP_200_OK)
        self.assertEqual(client.get(f'/api/rooms/{self.room.id}/').status_code, status.HTTP_200_OK)


class RoleAccessApiTests(TestCase):
    """[API/SECURITY] Ma trận quyền ADMIN / LANDLORD / TENANT / STAFF và cô lập dữ liệu."""

    def setUp(self):
        self.prop = make_property(code='MINE', owner_id=OWNER_ID)
        self.room = make_room(self.prop, room_number='1', status=RoomStatus.OCCUPIED, current_occupants=1,
                              tenant_name='Nguyễn A', tenant_phone='0900')
        self.free_room = make_room(self.prop, room_number='2')
        self.other_prop = make_property(code='OTHER', owner_id=OTHER_OWNER_ID)
        self.other_room = make_room(self.other_prop, room_number='9')
        self.landlord = jwt_client(OWNER_ID, 'LANDLORD')
        self.admin = jwt_client(1, 'ADMIN')
        self.tenant = jwt_client(TENANT_USER_ID, 'TENANT')

    def test_admin_sees_all_and_can_write(self):
        """S2-SEC-019 | ADMIN toàn quyền | Data: admin xem list + tạo nhà | Expected: thấy 2 nhà, 3 phòng; POST 201"""
        self.assertEqual(len(self.admin.get('/api/properties/').data), 2)
        self.assertEqual(len(self.admin.get('/api/rooms/').data), 3)
        res = self.admin.post('/api/properties/', {'name': 'Admin tạo', 'address': 'a'}, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

    def test_superuser_flag_grants_admin_access(self):
        """S2-SEC-020 | Token role TENANT nhưng is_superuser | Data: is_superuser=True | Expected: thấy toàn hệ thống như ADMIN"""
        client = jwt_client(77, 'TENANT', is_superuser=True)
        self.assertEqual(len(client.get('/api/properties/').data), 2)

    def test_landlord_cannot_access_other_landlord_data(self):
        """S2-SEC-021 | LANDLORD không truy cập dữ liệu chủ khác | Data: GET/PATCH/DELETE/actions trên nhà & phòng chủ 202 | Expected: tất cả 404"""
        pid, rid = self.other_prop.id, self.other_room.id
        checks = [
            self.landlord.get(f'/api/properties/{pid}/'),
            self.landlord.patch(f'/api/properties/{pid}/', {'name': 'Hack'}, format='json'),
            self.landlord.delete(f'/api/properties/{pid}/'),
            self.landlord.post(f'/api/properties/{pid}/update_status/', {'status': 'INACTIVE'}, format='json'),
            self.landlord.get(f'/api/properties/{pid}/stats/'),
            self.landlord.get(f'/api/properties/{pid}/rooms/'),
            self.landlord.get(f'/api/properties/{pid}/room_matrix/'),
            self.landlord.get(f'/api/rooms/{rid}/'),
            self.landlord.patch(f'/api/rooms/{rid}/', {'area': 1}, format='json'),
            self.landlord.delete(f'/api/rooms/{rid}/'),
            self.landlord.post(f'/api/rooms/{rid}/status/', {'status': 'INACTIVE'}, format='json'),
            self.landlord.get(f'/api/rooms/{rid}/check_rentable/'),
        ]
        for res in checks:
            self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)
        self.other_prop.refresh_from_db()
        self.assertEqual(self.other_prop.name, 'Nhà trọ Test')

    def test_landlord_lists_exclude_other_landlord(self):
        """S2-SEC-022 | Danh sách LANDLORD không chứa dữ liệu chủ khác | Data: list properties/rooms | Expected: chỉ 'MINE' và 2 phòng"""
        self.assertEqual([p['code'] for p in self.landlord.get('/api/properties/').data], ['MINE'])
        self.assertEqual(len(self.landlord.get('/api/rooms/').data), 2)

    def test_tenant_sees_only_rented_room_and_hides_pii(self):
        """S2-SEC-023 | TENANT chỉ xem phòng đang thuê, ẩn PII | Data: thuê phòng '1' | Expected: list=1 phòng; không có tenant_name/tenant_phone; phòng khác 404"""
        with patch_rented_rooms([self.room.id]):
            rooms = self.tenant.get('/api/rooms/')
            self.assertEqual([r['room_number'] for r in rooms.data], ['1'])
            self.assertNotIn('tenant_phone', rooms.data[0])
            self.assertNotIn('tenant_name', rooms.data[0])
            self.assertEqual(self.tenant.get(f'/api/rooms/{self.free_room.id}/').status_code, 404)
            self.assertEqual(self.tenant.get(f'/api/rooms/{self.other_room.id}/').status_code, 404)
            self.assertEqual([p['code'] for p in self.tenant.get('/api/properties/').data], ['MINE'])

    def test_tenant_cannot_write_anything(self):
        """S2-SEC-024 | TENANT bị chặn mọi thao tác ghi | Data: POST/PATCH/DELETE properties & rooms, đổi status | Expected: 403; dữ liệu không đổi"""
        with patch_rented_rooms([self.room.id]):
            responses = [
                self.tenant.post('/api/properties/', {'name': 'x', 'address': 'y'}, format='json'),
                self.tenant.patch(f'/api/properties/{self.prop.id}/', {'name': 'Hack'}, format='json'),
                self.tenant.delete(f'/api/properties/{self.prop.id}/'),
                self.tenant.post('/api/rooms/', {'property': self.prop.id, 'room_number': 'N', 'rent_price': 1},
                                 format='json'),
                self.tenant.patch(f'/api/rooms/{self.room.id}/', {'rent_price': 1}, format='json'),
                self.tenant.delete(f'/api/rooms/{self.room.id}/'),
                self.tenant.post(f'/api/rooms/{self.room.id}/status/', {'status': 'AVAILABLE'}, format='json'),
                self.tenant.post(f'/api/properties/{self.prop.id}/update_status/', {'status': 'INACTIVE'},
                                 format='json'),
            ]
        for res in responses:
            self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
        self.room.refresh_from_db()
        self.assertEqual(self.room.status, RoomStatus.OCCUPIED)
        self.assertEqual(Room.objects.count(), 3)

    def test_tenant_cannot_see_revenue_stats(self):
        """S2-SEC-025 | Thống kê doanh thu chỉ dành cho manager | Data: TENANT gọi stats; summary | Expected: stats=403; summary không có estimated_monthly_revenue"""
        with patch_rented_rooms([self.room.id]):
            self.assertEqual(self.tenant.get(f'/api/properties/{self.prop.id}/stats/').status_code, 403)
            self.assertNotIn('estimated_monthly_revenue', self.tenant.get('/api/properties/summary/').data)

    def test_tenant_without_active_rental_sees_nothing(self):
        """S2-SEC-026 | TENANT chưa thuê phòng nào | Data: danh sách phòng thuê rỗng | Expected: 200, list rỗng cho properties & rooms"""
        with patch_rented_rooms([]):
            self.assertEqual(self.tenant.get('/api/rooms/').data, [])
            self.assertEqual(self.tenant.get('/api/properties/').data, [])

    def test_legacy_staff_role_has_no_management_rights(self):
        """S2-SEC-027 | STAFF (legacy) bị coi là quyền hẹp nhất | Data: STAFF GET/POST/stats | Expected: không thấy dữ liệu, POST 403, stats 403"""
        staff = jwt_client(300, 'STAFF')
        with patch_rented_rooms([]):
            self.assertEqual(staff.get('/api/rooms/').data, [])
            self.assertEqual(staff.post('/api/properties/', {'name': 'x', 'address': 'y'}, format='json')
                             .status_code, 403)
            self.assertEqual(staff.get(f'/api/properties/{self.prop.id}/stats/').status_code, 403)

    def test_unknown_role_claim_is_treated_as_tenant(self):
        """S2-SEC-028 | Role lạ trong JWT | Data: role='HACKER' | Expected: bị xử lý như TENANT — POST 403, không thấy dữ liệu"""
        client = jwt_client(99, 'HACKER')
        with patch_rented_rooms([]):
            self.assertEqual(client.get('/api/rooms/').data, [])
            self.assertEqual(client.post('/api/properties/', {'name': 'x', 'address': 'y'}, format='json')
                             .status_code, 403)

    def test_tenant_service_down_fails_closed_with_503(self):
        """S2-SEC-029 | Tenant Service ngừng hoạt động | Data: requests.get ném ConnectionError | Expected: TENANT nhận 503, không lộ dữ liệu; LANDLORD không bị ảnh hưởng"""
        with mock.patch('common.service_client.requests.get', side_effect=requests.exceptions.ConnectionError()):
            self.assertEqual(self.tenant.get('/api/rooms/').status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
            self.assertEqual(self.landlord.get('/api/rooms/').status_code, status.HTTP_200_OK)

    def test_tenant_service_invalid_payload_fails_closed(self):
        """S2-SEC-030 | Tenant Service trả dữ liệu hỏng | Data: JSON không phải list | Expected: 503"""
        with mock.patch('common.service_client.requests.get', return_value=fake_http_response(200, {'bad': 1})):
            self.assertEqual(self.tenant.get('/api/properties/').status_code, status.HTTP_503_SERVICE_UNAVAILABLE)

    def test_tenant_lookup_forwards_users_own_jwt(self):
        """S2-SEC-031 | Gọi Tenant Service bằng JWT của chính người dùng | Data: mock requests.get | Expected: gọi đúng URL /api/tenants/links/ với header Bearer"""
        body = [{'tenant_id': 1, 'user_id': TENANT_USER_ID, 'room_id': self.room.id, 'landlord_id': OWNER_ID,
                 'status': 'ACTIVE'}]
        with mock.patch('common.service_client.requests.get', return_value=fake_http_response(200, body)) as fake:
            res = self.tenant.get('/api/rooms/')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(fake.call_args.args[0], 'http://127.0.0.1:8003/api/tenants/links/')
        self.assertTrue(fake.call_args.kwargs['headers']['Authorization'].startswith('Bearer '))

    def test_moved_out_tenant_loses_access(self):
        """S2-SEC-032 | Người thuê đã chuyển đi | Data: liên kết status=MOVED_OUT | Expected: rooms rỗng"""
        body = [{'tenant_id': 1, 'user_id': TENANT_USER_ID, 'room_id': self.room.id, 'landlord_id': OWNER_ID,
                 'status': 'MOVED_OUT'}]
        with mock.patch('common.service_client.requests.get', return_value=fake_http_response(200, body)):
            self.assertEqual(self.tenant.get('/api/rooms/').data, [])

    def test_tenant_without_active_link_sees_nothing_across_endpoints(self):
        """S2-SEC-033: [Legacy S2-LEG-029] TENANT có liên kết MOVED_OUT hoặc rỗng bị chặn trên cả /api/rooms/, /api/properties/ và /api/rooms/{id}/ (404)"""
        moved = {TENANT_USER_ID: [tenant_link(7, TENANT_USER_ID, room_id=self.room.id, status='MOVED_OUT')]}
        for links in (moved, {}):
            with patch_tenant_links(links):
                self.assertEqual(self.tenant.get('/api/rooms/').data, [])
                self.assertEqual(self.tenant.get('/api/properties/').data, [])
                self.assertEqual(
                    self.tenant.get(f'/api/rooms/{self.room.id}/').status_code,
                    status.HTTP_404_NOT_FOUND,
                )

    def test_maintenance_write_endpoints_locked_for_every_role_in_sprint1(self):
        """S2-SEC-034: [Legacy S2-LEG-033] Ma trận SprintFeatureLock chặn toàn bộ 9 write endpoints bảo trì (403) cho LANDLORD, ADMIN, TENANT và 401 cho anonymous"""
        req = MaintenanceRequest.objects.create(room=self.room, title='Hỏng đèn', reported_by_id=TENANT_USER_ID)
        rid = req.id
        calls = [
            ('post', '/api/maintenance/', {'room': self.room.id, 'title': 'x'}),
            ('patch', f'/api/maintenance/{rid}/', {'title': 'y'}),
            ('put', f'/api/maintenance/{rid}/', {'room': self.room.id, 'title': 'y'}),
            ('delete', f'/api/maintenance/{rid}/', None),
            ('post', f'/api/maintenance/{rid}/update_status/', {'status': 'IN_PROGRESS'}),
            ('post', f'/api/maintenance/{rid}/start/', {}),
            ('post', f'/api/maintenance/{rid}/record_cost/', {'actual_cost': '1'}),
            ('post', f'/api/maintenance/{rid}/complete/', {}),
            ('post', f'/api/maintenance/{rid}/cancel/', {}),
        ]
        with patch_tenant_links({TENANT_USER_ID: [tenant_link(1, TENANT_USER_ID, room_id=self.room.id, landlord_id=OWNER_ID)]}):
            for client in (self.landlord, self.admin, self.tenant):
                for method, url, data in calls:
                    res = getattr(client, method)(url, data, format='json')
                    self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN, (method, url))
        req.refresh_from_db()
        self.assertEqual(req.status, MaintenanceStatus.PENDING)
        self.assertEqual(MaintenanceRequest.objects.filter(id=rid).count(), 1)
        self.room.refresh_from_db()
        self.assertEqual(self.room.status, RoomStatus.OCCUPIED)
        self.assertEqual(
            APIClient().post('/api/maintenance/', {}, format='json').status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

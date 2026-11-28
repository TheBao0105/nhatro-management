"""[PURE UNIT] Service / Business Logic & Utilities Tests for Service 2.

Separated into two clear groups per test plan:
1. Validators / Utilities (`ParseHelperTests`, `ActorNameTests`): 7 tests (S2-UTL-001..007)
2. Services / Business Logic (`ScopedQuerysetTests`, `MaintenanceViewSetUnitTests`): 21 tests (S2-BIZ-001..021)
Total in module: 28 pure unit tests.
"""
from decimal import Decimal
from types import SimpleNamespace
from unittest import mock

from django.test import SimpleTestCase, TestCase
from rest_framework import serializers, status

from services.property_service.models import (
    MaintenanceHistory,
    MaintenanceRequest,
    MaintenanceStatus,
    PropertyStatus,
    RoomStatus,
)
from services.property_service.serializers import MaintenanceRequestSerializer
from services.property_service.views import (
    MaintenanceRequestViewSet,
    _actor_name,
    _parse_decimal,
    _parse_number,
    _room_status_after_maintenance,
    scoped_maintenance,
    scoped_properties,
    scoped_rooms,
)
from .base import OTHER_OWNER_ID, OWNER_ID, fake_user, make_property, make_room, patch_rented_rooms


class ParseHelperTests(SimpleTestCase):
    """[PURE UNIT — Validators / Utilities] Kiểm thử các hàm parse tham số truy vấn (_parse_decimal, _parse_number)."""

    def test_parse_decimal_empty_returns_none(self):
        """S2-UTL-001 | [Từ S2-BIZ-001] _parse_decimal giá trị rỗng | Data: None và '' | Expected: None"""
        self.assertIsNone(_parse_decimal(None))
        self.assertIsNone(_parse_decimal(''))

    def test_parse_decimal_valid_values(self):
        """S2-UTL-002 | [Từ S2-BIZ-002] _parse_decimal giá trị hợp lệ | Data: '12.5', 7, '0' | Expected: Decimal tương ứng"""
        self.assertEqual(_parse_decimal('12.5'), Decimal('12.5'))
        self.assertEqual(_parse_decimal(7), Decimal('7'))
        self.assertEqual(_parse_decimal('0'), Decimal('0'))

    def test_parse_decimal_invalid_raises_validation_error_with_field(self):
        """S2-UTL-003 | [Từ S2-BIZ-003] _parse_decimal giá trị sai | Data: 'abc', field='min_price' | Expected: ValidationError chứa khóa 'min_price'"""
        with self.assertRaises(serializers.ValidationError) as ctx:
            _parse_decimal('abc', 'min_price')
        self.assertIn('min_price', ctx.exception.detail)

    def test_parse_number_empty_and_all_return_none(self):
        """S2-UTL-004 | [Từ S2-BIZ-004] _parse_number bỏ qua giá trị rỗng/ALL | Data: None, '', 'ALL' | Expected: None"""
        for value in (None, '', 'ALL'):
            self.assertIsNone(_parse_number(value, int, 'floor'))

    def test_parse_number_casts_and_boundary_values(self):
        """S2-UTL-005 | [Gộp S2-BIZ-005, 007] _parse_number ép kiểu int/float và giữ đúng biên 0 / số âm | Data: '5', '2.5', '0', '-3' | Expected: 5, 2.5, 0, -3"""
        self.assertEqual(_parse_number('5', int, 'floor'), 5)
        self.assertEqual(_parse_number('2.5', float, 'min_area'), 2.5)
        self.assertEqual(_parse_number('0', int, 'floor'), 0)
        self.assertEqual(_parse_number('-3', int, 'floor'), -3)

    def test_parse_number_invalid_raises_validation_error(self):
        """S2-UTL-006 | [Từ S2-BIZ-006] _parse_number giá trị sai | Data: 'x' (int), '1.5' (int) | Expected: ValidationError chứa tên trường"""
        for raw in ('x', '1.5'):
            with self.assertRaises(serializers.ValidationError) as ctx:
                _parse_number(raw, int, 'floor')
            self.assertIn('floor', ctx.exception.detail)


class ActorNameTests(SimpleTestCase):
    """[PURE UNIT — Validators / Utilities] Kiểm thử hàm định danh người thao tác (_actor_name)."""

    def test_actor_name_resolution_order_and_anonymous_fallback(self):
        """S2-UTL-007 | [Gộp S2-BIZ-008, 009] _actor_name cho anonymous ('Hệ thống') và thứ tự ưu tiên full_name > username > 'User #id' | Data: None, unauth, full_name, username, id | Expected: 'Hệ thống', 'Nguyễn A', 'chutro1', 'User #5'"""
        self.assertEqual(_actor_name(None), 'Hệ thống')
        self.assertEqual(_actor_name(fake_user(authenticated=False)), 'Hệ thống')
        self.assertEqual(_actor_name(fake_user(full_name='Nguyễn A', username='a')), 'Nguyễn A')
        self.assertEqual(_actor_name(fake_user(username='chutro1')), 'chutro1')
        self.assertEqual(_actor_name(fake_user(user_id=5)), 'User #5')


class ScopedQuerysetTests(TestCase):
    """[PURE UNIT — Services / Business Logic] Phạm vi dữ liệu theo role (scoped_properties, scoped_rooms, scoped_maintenance)."""

    def setUp(self):
        self.p1 = make_property(code='P1', owner_id=OWNER_ID)
        self.p2 = make_property(code='P2', owner_id=OTHER_OWNER_ID)
        self.r1 = make_room(self.p1, room_number='1')
        self.r2 = make_room(self.p1, room_number='2')
        self.r3 = make_room(self.p2, room_number='3')

    def test_admin_sees_all_properties_and_rooms(self):
        """S2-BIZ-001 | [Từ S2-BIZ-010] ADMIN thấy toàn bộ nhà trọ và phòng | Data: 2 nhà của 2 chủ | Expected: 2 nhà, 3 phòng"""
        admin = fake_user(user_id=1, role='ADMIN')
        self.assertEqual(scoped_properties(admin).count(), 2)
        self.assertEqual(scoped_rooms(admin).count(), 3)

    def test_superuser_flag_is_treated_as_admin(self):
        """S2-BIZ-002 | [Từ S2-BIZ-011] Cờ is_superuser=True được cấp phạm vi toàn hệ thống như ADMIN | Data: role=TENANT, is_superuser=True | Expected: thấy 2 nhà"""
        user = fake_user(user_id=9, role='TENANT', is_superuser=True)
        self.assertEqual(scoped_properties(user).count(), 2)

    def test_landlord_sees_only_own_data(self):
        """S2-BIZ-003 | [Từ S2-BIZ-012] LANDLORD chỉ thấy nhà trọ và phòng thuộc sở hữu của mình | Data: owner 101 | Expected: nhà P1 và 2 phòng r1, r2"""
        landlord = fake_user(user_id=OWNER_ID, role='LANDLORD')
        self.assertEqual(list(scoped_properties(landlord)), [self.p1])
        self.assertEqual(set(scoped_rooms(landlord)), {self.r1, self.r2})

    def test_landlord_without_properties_sees_nothing(self):
        """S2-BIZ-004 | [Từ S2-BIZ-013] LANDLORD chưa có nhà trọ nhận queryset rỗng | Data: owner 777 | Expected: 0 nhà, 0 phòng"""
        landlord = fake_user(user_id=777, role='LANDLORD')
        self.assertEqual(scoped_properties(landlord).count(), 0)
        self.assertEqual(scoped_rooms(landlord).count(), 0)

    def test_tenant_sees_only_rented_room_and_its_property(self):
        """S2-BIZ-005 | [Từ S2-BIZ-014] TENANT chỉ thấy phòng đang thuê và nhà trọ chứa phòng đó | Data: thuê r1 | Expected: rooms=[r1], properties=[p1]"""
        tenant = fake_user(user_id=5, role='TENANT')
        with patch_rented_rooms([self.r1.id]):
            self.assertEqual(list(scoped_rooms(tenant)), [self.r1])
            self.assertEqual(list(scoped_properties(tenant)), [self.p1])

    def test_tenant_without_rented_rooms_sees_nothing(self):
        """S2-BIZ-006 | [Từ S2-BIZ-015] TENANT chưa thuê phòng nào nhận queryset rỗng | Data: rented_rooms=[] | Expected: 0 nhà, 0 phòng"""
        tenant = fake_user(user_id=5, role='TENANT')
        with patch_rented_rooms([]):
            self.assertEqual(scoped_rooms(tenant).count(), 0)
            self.assertEqual(scoped_properties(tenant).count(), 0)

    def test_legacy_staff_is_treated_as_narrowest_role(self):
        """S2-BIZ-007 | [Từ S2-BIZ-016] Role legacy STAFF bị giới hạn như TENANT không có phòng thuê | Data: role=STAFF | Expected: 0 phòng"""
        staff = fake_user(user_id=300, role='STAFF')
        with patch_rented_rooms([]):
            self.assertEqual(scoped_rooms(staff).count(), 0)

    def test_scoped_rooms_selects_property_relation(self):
        """S2-BIZ-008 | [Từ S2-BIZ-017] scoped_rooms sử dụng select_related('property') tránh lỗi N+1 query | Data: 3 phòng | Expected: 0 query phát sinh khi đọc room.property.name"""
        admin = fake_user(user_id=1, role='ADMIN')
        rooms = list(scoped_rooms(admin))
        with self.assertNumQueries(0):
            names = [r.property.name for r in rooms]
        self.assertEqual(len(names), 3)

    def test_deleted_property_still_in_scope_for_owner(self):
        """S2-BIZ-009 | [Từ S2-BIZ-018] Nhà xóa mềm (DELETED) vẫn nằm trong scoped_properties của chủ trọ để phục vụ xem chi tiết / khôi phục | Data: P1 DELETED | Expected: P1 thuộc scoped_properties"""
        self.p1.status = PropertyStatus.DELETED
        self.p1.save()
        self.assertIn(self.p1, scoped_properties(fake_user(user_id=OWNER_ID, role='LANDLORD')))

    def test_inactive_room_still_in_scope_for_owner(self):
        """S2-BIZ-010 | [Từ S2-BIZ-019] Phòng INACTIVE vẫn nằm trong scoped_rooms của chủ trọ | Data: r1 INACTIVE | Expected: r1 thuộc scoped_rooms"""
        self.r1.status = RoomStatus.INACTIVE
        self.r1.save()
        self.assertIn(self.r1, scoped_rooms(fake_user(user_id=OWNER_ID, role='LANDLORD')))

    def test_room_status_after_maintenance_all_branches(self):
        """S2-BIZ-011 | [Ngoài Sprint 1] [Từ S2-BIZ-020] _room_status_after_maintenance với requested hợp lệ/sai, previous_room_status, và current_occupants 0/1 | Data: 5 nhánh | Expected: trả đúng RoomStatus hoặc ValidationError"""
        req = MaintenanceRequest.objects.create(room=self.r1, title='Sửa điện')
        self.assertEqual(_room_status_after_maintenance(req, 'occupied'), RoomStatus.OCCUPIED)
        with self.assertRaises(serializers.ValidationError) as ctx:
            _room_status_after_maintenance(req, 'BOGUS')
        self.assertIn('room_status', ctx.exception.detail)

        req.previous_room_status = RoomStatus.RESERVED
        self.assertEqual(_room_status_after_maintenance(req), RoomStatus.RESERVED)

        req.previous_room_status = None
        self.r1.current_occupants = 0
        self.assertEqual(_room_status_after_maintenance(req), RoomStatus.AVAILABLE)
        self.r1.current_occupants = 1
        self.assertEqual(_room_status_after_maintenance(req), RoomStatus.OCCUPIED)

    def test_scoped_maintenance_for_admin_landlord_and_tenant(self):
        """S2-BIZ-012 | [Ngoài Sprint 1] [Từ S2-BIZ-021] scoped_maintenance phân quyền theo ADMIN/LANDLORD/TENANT | Data: 2 yêu cầu của 2 nhà trọ | Expected: ADMIN thấy 2, LANDLORD thấy 1, TENANT thấy yêu cầu mình báo"""
        m1 = MaintenanceRequest.objects.create(room=self.r1, title='M1', reported_by_id=555)
        m2 = MaintenanceRequest.objects.create(room=self.r3, title='M2', reported_by_id=666)
        self.assertEqual(scoped_maintenance(fake_user(user_id=1, role='ADMIN')).count(), 2)
        self.assertEqual(list(scoped_maintenance(fake_user(user_id=OWNER_ID, role='LANDLORD'))), [m1])
        self.assertEqual(list(scoped_maintenance(fake_user(user_id=666, role='TENANT'))), [m2])

    def test_room_external_block_reason_checks_tenants_and_contracts(self):
        """S2-BIZ-022 | room_external_block_reason và fetch_room_contracts kiểm tra liên kết khách thuê/hợp đồng từ Tenant Service & Contract Service trước khi xóa phòng | Data: tenant ACTIVE/MOVED_OUT, contract ACTIVE/DRAFT/EXTENDED/TERMINATED, lỗi 503 | Expected: trả lý do chặn khi còn liên kết, None khi đã kết thúc, DependencyUnavailable khi phản hồi lỗi"""
        from common.service_client import DependencyUnavailable, fetch_room_contracts, room_external_block_reason
        from common.testing import fake_http_response

        def make_auth_user():
            u = fake_user(user_id=OWNER_ID, role='LANDLORD')
            u.token = 'fake-jwt-token'
            return u

        with mock.patch('common.service_client.requests.get', side_effect=[
            fake_http_response(200, [{'tenant_id': 1, 'user_id': 555, 'room_id': self.r1.id, 'status': 'ACTIVE'}]),
        ]):
            reason_tenant = room_external_block_reason(make_auth_user(), self.r1.id)
        self.assertIn('hồ sơ khách thuê', reason_tenant)

        for contract_status in ('DRAFT', 'ACTIVE', 'EXTENDED'):
            with self.subTest(contract_status=contract_status):
                with mock.patch('common.service_client.requests.get', side_effect=[
                    fake_http_response(200, [{'tenant_id': 1, 'room_id': self.r1.id, 'status': 'MOVED_OUT'}]),
                    fake_http_response(200, {'results': [{'id': 9, 'room_id': self.r1.id, 'status': contract_status}]}),
                ]):
                    reason_contract = room_external_block_reason(make_auth_user(), self.r1.id)
                self.assertIn('hợp đồng', reason_contract)

        with mock.patch('common.service_client.requests.get', side_effect=[
            fake_http_response(200, [{'tenant_id': 1, 'room_id': self.r1.id, 'status': 'MOVED_OUT'}]),
            fake_http_response(200, [{'id': 9, 'room_id': self.r1.id, 'status': 'TERMINATED'}]),
        ]):
            self.assertIsNone(room_external_block_reason(make_auth_user(), self.r1.id))

        with mock.patch('common.service_client.requests.get', return_value=fake_http_response(500, {'detail': 'err'})):
            with self.assertRaises(DependencyUnavailable):
                fetch_room_contracts('Bearer x', self.r1.id)


class MaintenanceViewSetUnitTests(TestCase):
    """[PURE UNIT — Ngoài Sprint 1] Kiểm thử trực tiếp các method nghiệp vụ của MaintenanceRequestViewSet mà không tắt SPRINT_FEATURE_LOCK."""

    def setUp(self):
        self.prop = make_property(code='PM1', owner_id=OWNER_ID)
        self.other_prop = make_property(code='PM2', owner_id=OTHER_OWNER_ID)
        self.room = make_room(self.prop, room_number='101', status=RoomStatus.AVAILABLE)
        self.other_room = make_room(self.other_prop, room_number='201', status=RoomStatus.AVAILABLE)
        self.landlord = fake_user(user_id=OWNER_ID, role='LANDLORD', full_name='Chủ trọ A')

    def _view(self, user=None, data=None, action='create', pk=None):
        view = MaintenanceRequestViewSet()
        view.action = action
        view.format_kwarg = None
        view.kwargs = {'pk': pk} if pk is not None else {}
        view.request = SimpleNamespace(user=user or self.landlord, data=data or {}, query_params={})
        return view

    def test_get_permissions_and_helpers_set_room_status_and_transition(self):
        """S2-BIZ-013 | [Ngoài Sprint 1] [Từ S2-BIZ-022] get_permissions, _set_room_status và _ensure_transition | Data: action update/list, phòng cùng/khác status, chuyển trạng thái sai | Expected: trả đúng permission list, chỉ save khi đổi status, ném ValidationError khi sai luồng"""
        v_mgr = self._view(action='update')
        v_list = self._view(action='list')
        self.assertEqual(len(v_mgr.get_permissions()), 3)
        self.assertEqual(len(v_list.get_permissions()), 2)

        v_mgr._set_room_status(self.room, RoomStatus.AVAILABLE)
        v_mgr._set_room_status(self.room, RoomStatus.MAINTENANCE)
        self.room.refresh_from_db()
        self.assertEqual(self.room.status, RoomStatus.MAINTENANCE)

        req = MaintenanceRequest.objects.create(room=self.room, title='T', status=MaintenanceStatus.COMPLETED)
        with self.assertRaises(serializers.ValidationError):
            v_mgr._ensure_transition(req, [MaintenanceStatus.PENDING], MaintenanceStatus.IN_PROGRESS)

    def test_perform_create_all_branches(self):
        """S2-BIZ-014 | [Ngoài Sprint 1] [Từ S2-BIZ-023] perform_create với khóa phòng, set_room_maintenance=false, reported_by sẵn và phòng ngoài phạm vi | Data: 3 payload | Expected: tạo đúng trạng thái phòng, giữ reported_by, chặn phòng ngoài phạm vi"""
        v_bad = self._view(data={'room': self.other_room.id, 'title': 'X'})
        ser_bad = MaintenanceRequestSerializer(data={'room': self.other_room.id, 'title': 'X'},
                                               context={'request': v_bad.request})
        self.assertTrue(ser_bad.is_valid(), ser_bad.errors)
        with self.assertRaises(serializers.ValidationError):
            v_bad.perform_create(ser_bad)

        v1 = self._view(data={'room': self.room.id, 'title': 'Hỏng khóa'})
        s1 = MaintenanceRequestSerializer(data={'room': self.room.id, 'title': 'Hỏng khóa'},
                                          context={'request': v1.request})
        self.assertTrue(s1.is_valid(), s1.errors)
        v1.perform_create(s1)
        self.room.refresh_from_db()
        self.assertEqual(self.room.status, RoomStatus.MAINTENANCE)

        room2 = make_room(self.prop, room_number='102', status=RoomStatus.AVAILABLE)
        payload = {'room': room2.id, 'title': 'Thay bóng', 'reported_by': 'Khách B'}
        v2 = self._view(data={**payload, 'set_room_maintenance': 'false'})
        s2 = MaintenanceRequestSerializer(data=payload, context={'request': v2.request})
        self.assertTrue(s2.is_valid(), s2.errors)
        v2.perform_create(s2)
        room2.refresh_from_db()
        self.assertEqual(room2.status, RoomStatus.AVAILABLE)
        self.assertEqual(s2.instance.reported_by, 'Khách B')

    def test_perform_update_success_and_out_of_scope_room(self):
        """S2-BIZ-015 | [Ngoài Sprint 1] [Từ S2-BIZ-024] perform_update cập nhật hợp lệ và chặn đổi sang phòng ngoài phạm vi | Data: PATCH repair_info và PATCH room=other_room | Expected: lưu + ghi lịch sử khi hợp lệ; ValidationError khi phòng chủ khác"""
        req = MaintenanceRequest.objects.create(room=self.room, title='Cũ')
        v_ok = self._view(action='partial_update', pk=req.pk)
        s_ok = MaintenanceRequestSerializer(req, data={'title': 'Mới', 'repair_info': 'Đã kiểm tra',
                                                       'room': self.room.id},
                                            partial=True, context={'request': v_ok.request})
        self.assertTrue(s_ok.is_valid(), s_ok.errors)
        v_ok.perform_update(s_ok)
        req.refresh_from_db()
        self.assertEqual(req.title, 'Mới')
        self.assertEqual(MaintenanceHistory.objects.filter(maintenance_request=req).count(), 1)

        s_bad = MaintenanceRequestSerializer(req, data={'room': self.other_room.id}, partial=True,
                                             context={'request': v_ok.request})
        self.assertTrue(s_bad.is_valid(), s_bad.errors)
        with self.assertRaises(serializers.ValidationError):
            v_ok.perform_update(s_bad)

    def test_do_start_and_start_action_all_branches(self):
        """S2-BIZ-016 | [Ngoài Sprint 1] [Từ S2-BIZ-025] _do_start và action start với phòng AVAILABLE (có/không previous_room_status) và phòng đã MAINTENANCE | Data: 3 yêu cầu PENDING | Expected: chuyển IN_PROGRESS, khóa phòng và lưu previous_room_status đúng"""
        req1 = MaintenanceRequest.objects.create(room=self.room, title='T1')
        v1 = self._view(data={'assigned_to': 'Thợ 1', 'repair_info': 'Đang mở máy'}, action='start', pk=req1.pk)
        res = v1.start(v1.request, pk=req1.pk)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        req1.refresh_from_db()
        self.room.refresh_from_db()
        self.assertEqual((req1.status, req1.previous_room_status, self.room.status),
                         (MaintenanceStatus.IN_PROGRESS, RoomStatus.AVAILABLE, RoomStatus.MAINTENANCE))

        req2 = MaintenanceRequest.objects.create(room=self.room, title='T2')
        v1._do_start(req2)
        req2.refresh_from_db()
        self.assertEqual(req2.status, MaintenanceStatus.IN_PROGRESS)

        room3 = make_room(self.prop, room_number='103', status=RoomStatus.AVAILABLE)
        req3 = MaintenanceRequest.objects.create(room=room3, title='T3', previous_room_status=RoomStatus.OCCUPIED)
        v1._do_start(req3)
        req3.refresh_from_db()
        self.assertEqual(req3.previous_room_status, RoomStatus.OCCUPIED)

    def test_update_status_all_branches(self):
        """S2-BIZ-017 | [Ngoài Sprint 1] [Từ S2-BIZ-026] action update_status: status sai/PENDING (400), IN_PROGRESS, COMPLETED có technician, CANCELLED không technician | Data: 3 yêu cầu | Expected: 400 khi sai; 200 khi chuyển IN_PROGRESS/COMPLETED/CANCELLED"""
        req1 = MaintenanceRequest.objects.create(room=self.room, title='U1')
        v_bad = self._view(data={'status': 'PENDING'}, action='update_status', pk=req1.pk)
        self.assertEqual(v_bad.update_status(v_bad.request, pk=req1.pk).status_code, status.HTTP_400_BAD_REQUEST)

        v_prog = self._view(data={'status': 'IN_PROGRESS', 'technician_name': 'Thợ A'},
                            action='update_status', pk=req1.pk)
        self.assertEqual(v_prog.update_status(v_prog.request, pk=req1.pk).status_code, status.HTTP_200_OK)

        v_comp = self._view(data={'status': 'COMPLETED', 'technician_name': 'Thợ B', 'repair_info': 'Xong'},
                            action='update_status', pk=req1.pk)
        self.assertEqual(v_comp.update_status(v_comp.request, pk=req1.pk).status_code, status.HTTP_200_OK)
        req1.refresh_from_db()
        self.assertEqual((req1.status, req1.technician_name), (MaintenanceStatus.COMPLETED, 'Thợ B'))

        room2 = make_room(self.prop, room_number='104', status=RoomStatus.AVAILABLE)
        req2 = MaintenanceRequest.objects.create(room=room2, title='U2')
        v_canc = self._view(data={'status': 'CANCELLED'}, action='update_status', pk=req2.pk)
        self.assertEqual(v_canc.update_status(v_canc.request, pk=req2.pk).status_code, status.HTTP_200_OK)

    def test_record_cost_branches(self):
        """S2-BIZ-018 | [Ngoài Sprint 1] [Tách từ S2-BIZ-027] action record_cost với chi phí âm (ValidationError), payload rỗng và payload đầy đủ | Data: estimated_cost=-1, {}, đầy đủ | Expected: ValidationError khi âm; 200 và cập nhật DB khi hợp lệ"""
        self.room.status = RoomStatus.MAINTENANCE
        self.room.save()
        req = MaintenanceRequest.objects.create(room=self.room, title='C1', previous_room_status=RoomStatus.AVAILABLE)

        v_neg = self._view(data={'estimated_cost': -1}, action='record_cost', pk=req.pk)
        with self.assertRaises(serializers.ValidationError):
            v_neg.record_cost(v_neg.request, pk=req.pk)

        v_empty = self._view(data={}, action='record_cost', pk=req.pk)
        self.assertEqual(v_empty.record_cost(v_empty.request, pk=req.pk).status_code, status.HTTP_200_OK)

        v_full = self._view(data={'estimated_cost': 100000, 'actual_cost': 120000, 'repair_info': 'Thay van'},
                            action='record_cost', pk=req.pk)
        self.assertEqual(v_full.record_cost(v_full.request, pk=req.pk).status_code, status.HTTP_200_OK)
        req.refresh_from_db()
        self.assertEqual((req.estimated_cost, req.actual_cost, req.repair_info), (100000, 120000, 'Thay van'))

    def test_complete_action_branches(self):
        """S2-BIZ-019 | [Ngoài Sprint 1] [Tách từ S2-BIZ-027] action complete với chi phí âm (ValidationError) và hoàn tất hợp lệ khôi phục trạng thái phòng | Data: actual_cost=-50, actual_cost=150000 | Expected: ValidationError khi âm; COMPLETED và khôi phục AVAILABLE khi hợp lệ"""
        self.room.status = RoomStatus.MAINTENANCE
        self.room.save()
        req = MaintenanceRequest.objects.create(room=self.room, title='C2', previous_room_status=RoomStatus.AVAILABLE)

        v_cneg = self._view(data={'actual_cost': -50}, action='complete', pk=req.pk)
        with self.assertRaises(serializers.ValidationError):
            v_cneg.complete(v_cneg.request, pk=req.pk)

        v_cok = self._view(data={'actual_cost': 150000, 'repair_info': 'Hoàn tất'}, action='complete', pk=req.pk)
        self.assertEqual(v_cok.complete(v_cok.request, pk=req.pk).status_code, status.HTTP_200_OK)
        req.refresh_from_db()
        self.room.refresh_from_db()
        self.assertEqual((req.status, self.room.status), (MaintenanceStatus.COMPLETED, RoomStatus.AVAILABLE))

    def test_cancel_denies_other_tenant(self):
        """S2-BIZ-020 | [Ngoài Sprint 1] [Tách từ S2-BIZ-028] action cancel chặn TENANT khác hủy yêu cầu không phải của mình (403) | Data: reported_by_id=555, user_id=777 | Expected: 403 Forbidden"""
        req = MaintenanceRequest.objects.create(room=self.room, title='Hủy', reported_by_id=555)
        other_tenant = fake_user(user_id=777, role='TENANT')
        v_denied = self._view(user=other_tenant, data={}, action='cancel', pk=req.pk)
        with mock.patch.object(v_denied, 'get_object', return_value=req):
            res_denied = v_denied.cancel(v_denied.request, pk=req.pk)
        self.assertEqual(res_denied.status_code, status.HTTP_403_FORBIDDEN)

    def test_cancel_allows_reporting_tenant_and_restores_room(self):
        """S2-BIZ-021 | [Ngoài Sprint 1] [Tách từ S2-BIZ-028] action cancel cho phép người báo hủy yêu cầu của chính mình (200) | Data: reported_by_id=555, user_id=555 | Expected: 200 OK, status=CANCELLED"""
        req = MaintenanceRequest.objects.create(room=self.room, title='Hủy', reported_by_id=555)
        reporter = fake_user(user_id=555, role='TENANT')
        v_ok = self._view(user=reporter, data={'reason': 'Không cần nữa'}, action='cancel', pk=req.pk)
        res_ok = v_ok.cancel(v_ok.request, pk=req.pk)
        self.assertEqual(res_ok.status_code, status.HTTP_200_OK)
        req.refresh_from_db()
        self.assertEqual(req.status, MaintenanceStatus.CANCELLED)


class PropertyAndRoomViewSetUnitTests(TestCase):
    """[PURE UNIT — Sprint 1] Kiểm thử đơn vị trực tiếp các method nghiệp vụ và queryset của PropertyViewSet & RoomViewSet (không qua HTTP)."""

    def setUp(self):
        self.landlord = fake_user(user_id=OWNER_ID, role='LANDLORD', full_name='Chủ trọ A')
        self.other_landlord = fake_user(user_id=OTHER_OWNER_ID, role='LANDLORD', full_name='Chủ trọ B')
        self.tenant = fake_user(user_id=555, role='TENANT')
        self.p1 = make_property(
            code='NT01', owner_id=OWNER_ID, name='Hoa Mai Boarding',
            address='12 Nguyễn Gia Trí', ward='Phường 25', district='Bình Thạnh',
            city='TP. Hồ Chí Minh', total_floors=3, status=PropertyStatus.ACTIVE,
        )
        self.p2 = make_property(
            code='NT02', owner_id=OWNER_ID, name='Happy House',
            address='88 Đường số 7', ward='Tân Phong', district='Quận 7',
            city='TP. Hồ Chí Minh', total_floors=2, status=PropertyStatus.INACTIVE,
        )
        self.p_del = make_property(
            code='NT03', owner_id=OWNER_ID, name='Nhà Đã Xóa',
            address='99 Đường Cũ', ward='Phường 1', district='Quận 1',
            total_floors=2, status=PropertyStatus.DELETED,
        )
        self.p_other = make_property(
            code='NT99', owner_id=OTHER_OWNER_ID, name='Nhà Chủ Khác',
            address='1 Lê Lợi', district='Quận 1',
        )

    def _prop_view(self, action='list', user=None, query_params=None, data=None, pk=None):
        from services.property_service.views import PropertyViewSet
        view = PropertyViewSet()
        view.action = action
        view.format_kwarg = None
        view.kwargs = {'pk': pk} if pk is not None else {}
        view.request = SimpleNamespace(
            user=user or self.landlord,
            query_params=query_params or {},
            data=data or {},
            method='GET',
        )
        return view

    def _room_view(self, action='list', user=None, query_params=None, data=None, pk=None, method='GET'):
        from services.property_service.views import RoomViewSet
        view = RoomViewSet()
        view.action = action
        view.format_kwarg = None
        view.kwargs = {'pk': pk} if pk is not None else {}
        view.request = SimpleNamespace(
            user=user or self.landlord,
            query_params=query_params or {},
            data=data or {},
            method=method,
        )
        return view

    def test_property_viewset_summary_and_stats_unit_calculations_and_empty_state(self):
        """S2-BIZ-023 | [QLNT-253] PropertyViewSet.summary() và stats() tính đúng số nhà trọ ACTIVE, số phòng theo trạng thái, tỷ lệ lấp đầy, doanh thu và khi không có dữ liệu | Data: 0 phòng -> 6 phòng + nhà INACTIVE/DELETED | Expected: loại trừ nhà DELETED/INACTIVE khỏi total_properties, tính đúng từng trạng thái"""
        empty_user = fake_user(user_id=888, role='LANDLORD')
        v_empty = self._prop_view(action='summary', user=empty_user)
        res_empty = v_empty.summary(v_empty.request)
        self.assertEqual(res_empty.data['total_properties'], 0)
        self.assertEqual(res_empty.data['total_rooms'], 0)
        self.assertEqual(res_empty.data['occupancy_rate_percent'], 0.0)
        self.assertEqual(res_empty.data['estimated_monthly_revenue'], 0)

        r_av = make_room(self.p1, room_number='101', status=RoomStatus.AVAILABLE, rent_price=3000000)
        make_room(self.p1, room_number='102', status=RoomStatus.OCCUPIED, current_occupants=1, rent_price=4000000)
        make_room(self.p1, room_number='103', status=RoomStatus.FULL, current_occupants=2, rent_price=5000000)
        make_room(self.p1, room_number='201', status=RoomStatus.RESERVED, rent_price=3500000)
        make_room(self.p1, room_number='202', status=RoomStatus.MAINTENANCE, rent_price=3000000)
        make_room(self.p1, room_number='203', status=RoomStatus.INACTIVE, rent_price=2500000)
        make_room(self.p_del, room_number='D01', status=RoomStatus.AVAILABLE, rent_price=2000000)
        MaintenanceRequest.objects.create(room=r_av, title='Sửa khóa', status=MaintenanceStatus.PENDING)

        v_sum = self._prop_view(action='summary')
        res_sum = v_sum.summary(v_sum.request)
        self.assertEqual(res_sum.data['total_properties'], 1)
        self.assertEqual(res_sum.data['total_rooms'], 6)
        self.assertEqual(res_sum.data['available_rooms'], 1)
        self.assertEqual(res_sum.data['occupied_rooms'], 2)
        self.assertEqual(res_sum.data['full_rooms'], 1)
        self.assertEqual(res_sum.data['reserved_rooms'], 1)
        self.assertEqual(res_sum.data['maintenance_rooms'], 1)
        self.assertEqual(res_sum.data['inactive_rooms'], 1)
        self.assertEqual(res_sum.data['occupancy_rate_percent'], 33.3)
        self.assertEqual(res_sum.data['open_maintenance_requests'], 1)
        self.assertEqual(res_sum.data['estimated_monthly_revenue'], Decimal('9000000'))

        with patch_rented_rooms([r_av.id]):
            v_ten = self._prop_view(action='summary', user=self.tenant)
            self.assertNotIn('estimated_monthly_revenue', v_ten.summary(v_ten.request).data)

        v_stats = self._prop_view(action='stats', pk=self.p1.pk)
        res_stats = v_stats.stats(v_stats.request, pk=self.p1.pk)
        self.assertEqual(res_stats.data['total_rooms'], 6)
        self.assertEqual(res_stats.data['estimated_monthly_revenue'], Decimal('9000000'))

    def test_property_viewset_get_queryset_list_status_filters_and_excludes_deleted(self):
        """S2-BIZ-024 | [QLNT-258] PropertyViewSet.get_queryset() ẩn nhà trọ DELETED mặc định khi list, lọc đúng status/include_deleted/district/ward và xử lý danh sách rỗng | Data: ACTIVE, INACTIVE, DELETED | Expected: mặc định [NT01, NT02]; lọc ACTIVE=[NT01]; DELETED=[NT03]; ALL/include_deleted đủ 3"""
        codes_default = sorted(p.code for p in self._prop_view(action='list').get_queryset())
        self.assertEqual(codes_default, ['NT01', 'NT02'])

        codes_active = [p.code for p in self._prop_view(action='list', query_params={'status': 'active'}).get_queryset()]
        self.assertEqual(codes_active, ['NT01'])

        codes_deleted = [p.code for p in self._prop_view(action='list', query_params={'status': 'DELETED'}).get_queryset()]
        self.assertEqual(codes_deleted, ['NT03'])

        codes_all = sorted(p.code for p in self._prop_view(action='list', query_params={'status': 'ALL'}).get_queryset())
        self.assertEqual(codes_all, ['NT01', 'NT02', 'NT03'])

        codes_inc = sorted(p.code for p in self._prop_view(action='list', query_params={'include_deleted': 'true'}).get_queryset())
        self.assertEqual(codes_inc, ['NT01', 'NT02', 'NT03'])

        codes_dist = [p.code for p in self._prop_view(action='list', query_params={'district': 'Bình Thạnh', 'ward': 'Phường 25'}).get_queryset()]
        self.assertEqual(codes_dist, ['NT01'])

        empty_qs = self._prop_view(action='list', user=fake_user(user_id=999, role='LANDLORD')).get_queryset()
        self.assertEqual(list(empty_qs), [])

    def test_property_viewset_retrieve_detail_rooms_and_room_matrix_unit(self):
        """S2-BIZ-025 | [QLNT-262] PropertyViewSet xem chi tiết nhà trọ tồn tại, nhà trọ đã xóa mềm (DELETED), không tồn tại (Http404), danh sách rooms và sơ đồ room_matrix | Data: p1, p_del, pk=999999 | Expected: get_object trả đúng p1 và p_del; ném Http404 khi không tồn tại hoặc chủ khác"""
        from django.http import Http404

        make_room(self.p1, room_number='101', floor=1, status=RoomStatus.AVAILABLE)
        make_room(self.p1, room_number='201', floor=2, status=RoomStatus.OCCUPIED, current_occupants=1)

        v_ok = self._prop_view(action='retrieve', pk=self.p1.pk)
        self.assertEqual(v_ok.get_object().code, 'NT01')

        v_del = self._prop_view(action='retrieve', pk=self.p_del.pk)
        self.assertEqual(v_del.get_object().status, PropertyStatus.DELETED)

        for bad_pk in (999999, self.p_other.pk):
            with self.assertRaises(Http404):
                self._prop_view(action='retrieve', pk=bad_pk).get_object()

        v_rooms = self._prop_view(action='rooms', pk=self.p1.pk, query_params={'status': 'occupied'})
        res_rooms = v_rooms.rooms(v_rooms.request, pk=self.p1.pk)
        self.assertEqual([r['room_number'] for r in res_rooms.data], ['201'])

        v_matrix = self._prop_view(action='room_matrix', pk=self.p1.pk)
        res_matrix = v_matrix.room_matrix(v_matrix.request, pk=self.p1.pk)
        self.assertEqual(res_matrix.data['total_rooms'], 2)
        self.assertEqual([f['floor_name'] for f in res_matrix.data['floors']], ['Tầng 1', 'Tầng 2'])

    def test_property_viewset_destroy_and_update_status_soft_hard_delete_and_active_room_blocks(self):
        """S2-BIZ-026 | [QLNT-270] PropertyViewSet.destroy() và update_status() chặn xóa khi còn phòng hoạt động, xóa mềm khi chỉ còn phòng INACTIVE, xóa cứng khi không có phòng, và báo 404 khi không tồn tại | Data: phòng AVAILABLE -> INACTIVE -> nhà trống | Expected: 400 khi còn phòng active; soft_deleted=True khi phòng INACTIVE; soft_deleted=False khi nhà trống"""
        from django.http import Http404
        from services.property_service.models import Property

        with self.assertRaises(Http404):
            v_404 = self._prop_view(action='destroy', pk=999999)
            v_404.destroy(v_404.request, pk=999999)

        room = make_room(self.p1, room_number='101', status=RoomStatus.OCCUPIED, current_occupants=1)
        v_del = self._prop_view(action='destroy', pk=self.p1.pk)
        res_blocked = v_del.destroy(v_del.request, pk=self.p1.pk)
        self.assertEqual(res_blocked.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('đang thuê', res_blocked.data['error'])

        v_st_bad = self._prop_view(action='update_status', pk=self.p1.pk, data={'status': 'DELETED'})
        self.assertEqual(v_st_bad.update_status(v_st_bad.request, pk=self.p1.pk).status_code, status.HTTP_400_BAD_REQUEST)

        v_st_bogus = self._prop_view(action='update_status', pk=self.p1.pk, data={'status': 'BOGUS'})
        self.assertEqual(v_st_bogus.update_status(v_st_bogus.request, pk=self.p1.pk).status_code, status.HTTP_400_BAD_REQUEST)

        room.status = RoomStatus.INACTIVE
        room.current_occupants = 0
        room.save()
        res_soft = v_del.destroy(v_del.request, pk=self.p1.pk)
        self.assertEqual(res_soft.status_code, status.HTTP_200_OK)
        self.assertTrue(res_soft.data['soft_deleted'])
        self.p1.refresh_from_db()
        self.assertEqual(self.p1.status, PropertyStatus.DELETED)
        self.assertNotIn(self.p1, list(self._prop_view(action='list').get_queryset()))

        v_hard = self._prop_view(action='destroy', pk=self.p2.pk)
        res_hard = v_hard.destroy(v_hard.request, pk=self.p2.pk)
        self.assertEqual(res_hard.status_code, status.HTTP_200_OK)
        self.assertFalse(res_hard.data['soft_deleted'])
        self.assertFalse(Property.objects.filter(pk=self.p2.pk).exists())

    def test_room_viewset_get_queryset_list_excludes_deleted_property_and_filters_by_status_and_property(self):
        """S2-BIZ-027 | [QLNT-278, QLNT-282] RoomViewSet.get_queryset() loại trừ phòng của nhà trọ DELETED khi xem danh sách, lọc theo trạng thái/nhà trọ, nhưng vẫn cho xem chi tiết theo ID | Data: phòng thuộc p1, p2, p_del | Expected: list chỉ trả phòng của p1, p2; retrieve vẫn lấy được phòng của p_del"""
        from django.http import Http404

        r1 = make_room(self.p1, room_number='101', status=RoomStatus.AVAILABLE)
        r2 = make_room(self.p2, room_number='201', status=RoomStatus.OCCUPIED, current_occupants=1)
        r_del = make_room(self.p_del, room_number='D01', status=RoomStatus.AVAILABLE)

        for list_action in ('list', 'available_rooms', 'occupied_rooms', 'maintenance_rooms'):
            qs = self._room_view(action=list_action).get_queryset()
            self.assertNotIn(r_del, list(qs))

        qs_by_prop = self._room_view(action='list', query_params={'property_id': str(self.p1.id)}).get_queryset()
        self.assertEqual(list(qs_by_prop), [r1])

        qs_by_status = self._room_view(action='list', query_params={'status': 'occupied'}).get_queryset()
        self.assertEqual(list(qs_by_status), [r2])

        v_ret_del = self._room_view(action='retrieve', pk=r_del.pk)
        self.assertEqual(v_ret_del.get_object(), r_del)
        self.assertFalse(r_del.is_rentable)

        with self.assertRaises(Http404):
            self._room_view(action='retrieve', pk=999999).get_object()

    def test_room_viewset_perform_create_and_update_enforce_property_ownership(self):
        """S2-BIZ-028 | [QLNT-274, QLNT-286] RoomViewSet.perform_create() và perform_update() cho phép thao tác trên nhà trọ của mình và chặn gán/chuyển phòng sang nhà trọ của chủ khác | Data: property=p1 (hợp lệ) vs property=p_other (ValidationError) | Expected: lưu thành công cho p1; ném ValidationError cho p_other"""
        from services.property_service.serializers import RoomSerializer

        v_create = self._room_view(action='create')
        ser_ok = RoomSerializer(
            data={'property': self.p1.id, 'room_number': '101', 'floor': 1, 'area': 20, 'rent_price': 3000000},
            context={'request': v_create.request},
        )
        self.assertTrue(ser_ok.is_valid(), ser_ok.errors)
        v_create.perform_create(ser_ok)
        room = ser_ok.instance
        self.assertEqual(room.property_id, self.p1.id)

        ser_bad_create = RoomSerializer(
            data={'property': self.p_other.id, 'room_number': '901', 'floor': 1, 'area': 20, 'rent_price': 3000000},
            context={'request': v_create.request},
        )
        self.assertTrue(ser_bad_create.is_valid(), ser_bad_create.errors)
        with self.assertRaises(serializers.ValidationError) as ctx:
            v_create.perform_create(ser_bad_create)
        self.assertIn('property', ctx.exception.detail)

        v_update = self._room_view(action='partial_update', pk=room.pk)
        ser_bad_move = RoomSerializer(
            room, data={'property': self.p_other.id}, partial=True, context={'request': v_update.request},
        )
        self.assertTrue(ser_bad_move.is_valid(), ser_bad_move.errors)
        with self.assertRaises(serializers.ValidationError):
            v_update.perform_update(ser_bad_move)

        ser_ok_upd = RoomSerializer(
            room, data={'rent_price': 3500000}, partial=True, context={'request': v_update.request},
        )
        self.assertTrue(ser_ok_upd.is_valid(), ser_ok_upd.errors)
        v_update.perform_update(ser_ok_upd)
        room.refresh_from_db()
        self.assertEqual(room.rent_price, Decimal('3500000'))

    def test_room_viewset_destroy_unit_blocks_active_or_linked_and_soft_or_hard_deletes(self):
        """S2-BIZ-029 | [QLNT-290] RoomViewSet.destroy() chặn xóa phòng OCCUPIED/FULL/RESERVED/có người ở, chặn khi còn liên kết khách thuê/hợp đồng, xóa mềm sang INACTIVE khi có lịch sử bảo trì, xóa cứng khi sạch và ném Http404 khi không tồn tại | Data: 5 tình huống | Expected: 404, 400, soft_deleted=True, soft_deleted=False"""
        from django.http import Http404
        from services.property_service.models import Room

        with self.assertRaises(Http404):
            v_404 = self._room_view(action='destroy', pk=999999)
            v_404.destroy(v_404.request, pk=999999)

        for blocked_st in (RoomStatus.OCCUPIED, RoomStatus.FULL, RoomStatus.RESERVED):
            r_blk = make_room(self.p1, room_number=f'B-{blocked_st}', status=blocked_st)
            v_blk = self._room_view(action='destroy', pk=r_blk.pk)
            res_blk = v_blk.destroy(v_blk.request, pk=r_blk.pk)
            self.assertEqual(res_blk.status_code, status.HTTP_400_BAD_REQUEST)

        r_ext = make_room(self.p1, room_number='EXT-1', status=RoomStatus.AVAILABLE)
        v_ext = self._room_view(action='destroy', pk=r_ext.pk)
        with mock.patch('services.property_service.views.room_external_block_reason',
                        return_value='còn hợp đồng thuê đang hiệu lực (#10)'):
            res_ext = v_ext.destroy(v_ext.request, pk=r_ext.pk)
        self.assertEqual(res_ext.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('hợp đồng', res_ext.data['error'])

        r_hist = make_room(self.p1, room_number='HIST-1', status=RoomStatus.AVAILABLE)
        MaintenanceRequest.objects.create(room=r_hist, title='Đã sửa')
        v_hist = self._room_view(action='destroy', pk=r_hist.pk)
        with mock.patch('services.property_service.views.room_external_block_reason', return_value=None):
            res_soft = v_hist.destroy(v_hist.request, pk=r_hist.pk)
        self.assertEqual(res_soft.status_code, status.HTTP_200_OK)
        self.assertTrue(res_soft.data['soft_deleted'])
        r_hist.refresh_from_db()
        self.assertEqual(r_hist.status, RoomStatus.INACTIVE)

        r_clean = make_room(self.p1, room_number='CLEAN-1', status=RoomStatus.AVAILABLE)
        v_clean = self._room_view(action='destroy', pk=r_clean.pk)
        with mock.patch('services.property_service.views.room_external_block_reason', return_value=None):
            res_hard = v_clean.destroy(v_clean.request, pk=r_clean.pk)
        self.assertEqual(res_hard.status_code, status.HTTP_200_OK)
        self.assertFalse(res_hard.data['soft_deleted'])
        self.assertFalse(Room.objects.filter(pk=r_clean.pk).exists())

    def test_room_viewset_update_status_and_check_rentable_unit_transitions_and_invariants(self):
        """S2-BIZ-030 | [QLNT-294] RoomViewSet.update_status() và check_rentable() kiểm tra chuyển trạng thái hợp lệ/không hợp lệ, đồng bộ current_occupants & thông tin người thuê, và chặn đặt INACTIVE khi đang có người thuê | Data: AVAILABLE -> OCCUPIED -> FULL -> INACTIVE (chặn) -> AVAILABLE -> INACTIVE | Expected: đồng bộ chính xác, trả 400 khi vi phạm"""
        room = make_room(self.p1, room_number='101', max_occupants=2, status=RoomStatus.AVAILABLE)

        v_get = self._room_view(action='update_status', pk=room.pk, method='GET')
        res_get = v_get.update_status(v_get.request, pk=room.pk)
        self.assertTrue(res_get.data['is_rentable'])

        v_chk = self._room_view(action='check_rentable', pk=room.pk, method='GET')
        self.assertTrue(v_chk.check_rentable(v_chk.request, pk=room.pk).data['can_rent'])

        v_bad_st = self._room_view(action='update_status', pk=room.pk, method='POST', data={'status': 'INVALID'})
        self.assertEqual(v_bad_st.update_status(v_bad_st.request, pk=room.pk).status_code, status.HTTP_400_BAD_REQUEST)

        v_bad_occ = self._room_view(
            action='update_status', pk=room.pk, method='POST',
            data={'status': 'RESERVED', 'current_occupants': 5},
        )
        self.assertEqual(v_bad_occ.update_status(v_bad_occ.request, pk=room.pk).status_code, status.HTTP_400_BAD_REQUEST)

        v_occ = self._room_view(
            action='update_status', pk=room.pk, method='POST',
            data={'status': 'OCCUPIED', 'tenant_name': 'Nguyễn Văn A', 'tenant_phone': '0909123456'},
        )
        self.assertEqual(v_occ.update_status(v_occ.request, pk=room.pk).status_code, status.HTTP_200_OK)
        room.refresh_from_db()
        self.assertEqual((room.status, room.current_occupants, room.tenant_name), (RoomStatus.OCCUPIED, 1, 'Nguyễn Văn A'))

        v_inact_blocked = self._room_view(
            action='update_status', pk=room.pk, method='POST', data={'status': 'INACTIVE'},
        )
        self.assertEqual(
            v_inact_blocked.update_status(v_inact_blocked.request, pk=room.pk).status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        v_occ_max = self._room_view(
            action='update_status', pk=room.pk, method='POST',
            data={'status': 'OCCUPIED', 'current_occupants': 2},
        )
        v_occ_max.update_status(v_occ_max.request, pk=room.pk)
        room.refresh_from_db()
        self.assertEqual((room.status, room.current_occupants), (RoomStatus.FULL, 2))

        v_avail = self._room_view(
            action='update_status', pk=room.pk, method='POST', data={'status': 'AVAILABLE'},
        )
        v_avail.update_status(v_avail.request, pk=room.pk)
        room.refresh_from_db()
        self.assertEqual((room.status, room.current_occupants, room.tenant_name, room.tenant_phone),
                         (RoomStatus.AVAILABLE, 0, '', ''))

        v_inact_ok = self._room_view(
            action='update_status', pk=room.pk, method='POST', data={'status': 'INACTIVE'},
        )
        self.assertEqual(v_inact_ok.update_status(v_inact_ok.request, pk=room.pk).status_code, status.HTTP_200_OK)

    def test_property_viewset_search_by_name_code_address_area_and_combined_filters_unit(self):
        """S2-BIZ-031 | [QLNT-298] PropertyViewSet.get_queryset() tìm kiếm nhà trọ theo tên, mã, địa chỉ, phường, quận, thành phố (không phân biệt hoa/thường), tìm rỗng, không tìm thấy và kết hợp bộ lọc | Data: p1 (Hoa Mai, Bình Thạnh), p2 (Happy House, Quận 7) | Expected: khớp chính xác từng điều kiện"""
        def search_codes(**params):
            return sorted(p.code for p in self._prop_view(action='list', query_params=params).get_queryset())

        self.assertEqual(search_codes(search='hoa mai'), ['NT01'])
        self.assertEqual(search_codes(search='  NT02  '), ['NT02'])
        self.assertEqual(search_codes(search='nguyễn gia trí'), ['NT01'])
        self.assertEqual(search_codes(search='tân phong'), ['NT02'])
        self.assertEqual(search_codes(search='quận 7'), ['NT02'])
        self.assertEqual(search_codes(search='hồ chí minh'), ['NT01', 'NT02'])
        self.assertEqual(search_codes(search=''), ['NT01', 'NT02'])
        self.assertEqual(search_codes(search='khong-ton-tai-xyz'), [])
        self.assertEqual(search_codes(search='hồ chí minh', status='ACTIVE', district='Bình Thạnh'), ['NT01'])

    def test_room_viewset_search_filter_and_sort_queryset_unit(self):
        """S2-BIZ-032 | [QLNT-306] RoomViewSet.get_queryset() tìm kiếm phòng theo số phòng/mã/nhà trọ/người thuê, lọc theo diện tích/giá/trạng thái/tầng/số người, kết hợp nhiều điều kiện, không có kết quả và sắp xếp | Data: 3 phòng ở p1, p2 | Expected: lọc & sắp xếp chính xác, chặn TENANT tìm theo tenant_name"""
        r1 = make_room(
            self.p1, room_number='A101', floor=1, area=18.0, rent_price=2500000,
            max_occupants=2, status=RoomStatus.AVAILABLE,
        )
        r2 = make_room(
            self.p1, room_number='A201', floor=2, area=28.0, rent_price=4000000,
            max_occupants=3, status=RoomStatus.OCCUPIED, current_occupants=1, tenant_name='Trần Minh Quân',
        )
        make_room(
            self.p2, room_number='B101', floor=1, area=35.0, rent_price=5500000,
            max_occupants=4, status=RoomStatus.FULL, current_occupants=4,
        )

        def query_numbers(user=None, **params):
            return [r.room_number for r in self._room_view(action='list', user=user, query_params=params).get_queryset()]

        self.assertEqual(query_numbers(search='a101'), ['A101'])
        self.assertEqual(query_numbers(search='nt01-a201'), ['A201'])
        self.assertEqual(query_numbers(search='happy house'), ['B101'])
        self.assertEqual(query_numbers(search='Trần Minh Quân'), ['A201'])

        with patch_rented_rooms([r1.id, r2.id]):
            self.assertEqual(query_numbers(user=self.tenant, search='Trần Minh Quân'), [])

        self.assertEqual(query_numbers(min_area='20', max_area='30'), ['A201'])
        self.assertEqual(query_numbers(min_price='3000000', max_price='5000000'), ['A201'])
        self.assertEqual(query_numbers(status='available'), ['A101'])
        self.assertEqual(query_numbers(floor='2', max_occupants='3', district='Bình Thạnh', ward='Phường 25', address='Gia Trí'), ['A201'])
        self.assertEqual(query_numbers(search='hoa mai', status='OCCUPIED', min_price='3500000'), ['A201'])
        self.assertEqual(query_numbers(min_price='9000000'), [])
        self.assertEqual(query_numbers(sort='price_desc'), ['B101', 'A201', 'A101'])
        self.assertEqual(query_numbers(sort='area_asc'), ['A101', 'A201', 'B101'])

        with self.assertRaises(serializers.ValidationError):
            self._room_view(action='list', query_params={'min_price': 'abc'}).get_queryset()

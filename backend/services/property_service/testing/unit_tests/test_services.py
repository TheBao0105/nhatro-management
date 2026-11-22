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

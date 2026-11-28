"""[PURE UNIT] PropertySerializer & RoomSerializer Tests (Sprint 1).

Optimized suite: 18 cohesive, parameterized unit tests (consolidated from 44 granular tests
S2-SER-001..044 with 0 loss of assertion or branch coverage).
"""
from decimal import Decimal

from django.test import TestCase

from services.property_service.models import MaintenanceRequest, MaintenanceStatus, PropertyStatus, Room, RoomStatus
from services.property_service.serializers import PropertySerializer, RoomSerializer
from .base import OWNER_ID, fake_user, make_property, make_room, serializer_context


def room_payload(prop, **overrides):
    data = {
        'property': prop.id,
        'room_number': '101',
        'floor': 1,
        'area': 20,
        'rent_price': 3000000,
        'max_occupants': 2,
    }
    data.update(overrides)
    return data


class PropertySerializerTests(TestCase):
    def valid(self, **overrides):
        data = {'name': 'Nhà trọ Hoa Mai', 'address': '1 Đường A', 'district': 'Quận 1'}
        data.update(overrides)
        return PropertySerializer(data=data, context=serializer_context())

    def test_create_property_assigns_token_owner_and_ignores_payload_owner(self):
        """S2-SER-001 | [Gộp S2-SER-001, 003] Tạo Property hợp lệ gán owner_id từ request.user và bỏ qua owner_id=999 trong payload | Data: name, address, owner_id=999 | Expected: is_valid=True, owner_id=101, tự sinh code NT..."""
        ser = self.valid(owner_id=999)
        self.assertTrue(ser.is_valid(), ser.errors)
        prop = ser.save()
        self.assertEqual(prop.owner_id, OWNER_ID)
        self.assertTrue(prop.code.startswith('NT'))

    def test_create_without_request_context_uses_model_default_owner(self):
        """S2-SER-002 | [Từ S2-SER-002] Tạo Property khi context không có request | Data: payload hợp lệ, context={} | Expected: owner_id mặc định của model (=1)"""
        ser = PropertySerializer(data={'name': 'A', 'address': 'a'})
        self.assertTrue(ser.is_valid(), ser.errors)
        self.assertEqual(ser.save().owner_id, 1)

    def test_property_required_and_blank_fields_validation(self):
        """S2-SER-003 | [Gộp S2-SER-004, 005, 006, 007] Kiểm tra thiếu trường bắt buộc (name, address) và chuỗi rỗng/khoảng trắng | Data: {}, thiếu name/address, name=''/'   ' | Expected: is_valid=False, báo lỗi đúng trường"""
        empty = PropertySerializer(data={}, context=serializer_context())
        self.assertFalse(empty.is_valid())
        self.assertTrue({'name', 'address'} <= set(empty.errors))

        no_name = PropertySerializer(data={'address': 'a'}, context=serializer_context())
        self.assertFalse(no_name.is_valid())
        self.assertIn('name', no_name.errors)

        no_addr = PropertySerializer(data={'name': 'A'}, context=serializer_context())
        self.assertFalse(no_addr.is_valid())
        self.assertIn('address', no_addr.errors)

        for blank in ('', '   '):
            with self.subTest(name=blank):
                ser = self.valid(name=blank)
                self.assertFalse(ser.is_valid())
                self.assertIn('name', ser.errors)

    def test_property_status_choices_validation(self):
        """S2-SER-004 | [Gộp S2-SER-008, 009] Kiểm tra status hợp lệ (ACTIVE/INACTIVE/DELETED) và từ chối status='BOGUS' | Data: 3 status hợp lệ + 1 sai | Expected: hợp lệ True; BOGUS False ở 'status'"""
        for st in PropertyStatus.values:
            with self.subTest(status=st):
                self.assertTrue(self.valid(status=st).is_valid())
        bad = self.valid(status='BOGUS')
        self.assertFalse(bad.is_valid())
        self.assertIn('status', bad.errors)

    def test_property_numeric_and_utility_rates_validation(self):
        """S2-SER-005 | [Gộp S2-SER-010, 011, 012 — BUG-03] Chặn total_floors sai kiểu/<=0 hoặc nhỏ hơn tầng phòng hiện có, và chặn đơn giá điện/nước/internet âm | Data: total_floors='abc'/-1/0, giảm tầng < phòng hiện có, rates=-1 | Expected: is_valid=False ở từng trường"""
        for val in ('abc', -1, 0):
            with self.subTest(total_floors=val):
                ser = self.valid(total_floors=val)
                self.assertFalse(ser.is_valid())
                self.assertIn('total_floors', ser.errors)
        self.assertTrue(self.valid(total_floors=3).is_valid())
        for field in ('electricity_rate', 'water_rate', 'internet_rate'):
            with self.subTest(rate_field=field):
                ser = self.valid(**{field: -1})
                self.assertFalse(ser.is_valid())
                self.assertIn(field, ser.errors)

        prop = make_property(total_floors=4)
        make_room(prop, room_number='301', floor=3)
        shrink_bad = PropertySerializer(prop, data={'total_floors': 2}, partial=True, context=serializer_context())
        self.assertFalse(shrink_bad.is_valid())
        self.assertIn('total_floors', shrink_bad.errors)

        shrink_ok = PropertySerializer(prop, data={'total_floors': 3}, partial=True, context=serializer_context())
        self.assertTrue(shrink_ok.is_valid(), shrink_ok.errors)

    def test_property_duplicate_code_and_invalid_image_url_rejected(self):
        """S2-SER-006 | [Gộp S2-SER-013, 014] Chặn trùng code UNIQUE và image_url sai định dạng URL | Data: code='DUP', image_url='not-a-url' | Expected: lỗi ở 'code' và 'image_url'"""
        make_property(code='DUP')
        dup = self.valid(code='DUP')
        self.assertFalse(dup.is_valid())
        self.assertIn('code', dup.errors)

        bad_url = self.valid(image_url='not-a-url')
        self.assertFalse(bad_url.is_valid())
        self.assertIn('image_url', bad_url.errors)

    def test_property_serialized_output_computed_fields_and_room_counts(self):
        """S2-SER-007 | [Từ S2-SER-015] Đầu ra PropertySerializer chứa full_address, status_display, bộ đếm phòng và danh sách rooms lồng nhau | Data: 1 AVAILABLE, 1 OCCUPIED | Expected: total=2, available=1, occupied=1"""
        prop = make_property(code='NT1', address='A', ward='W', district='D', city='C')
        make_room(prop, room_number='1')
        make_room(prop, room_number='2', status='OCCUPIED', current_occupants=1)
        data = PropertySerializer(prop, context=serializer_context()).data
        self.assertEqual(data['full_address'], 'A, W, D, C')
        self.assertEqual(data['status_display'], 'Đang hoạt động')
        self.assertEqual((data['total_rooms_count'], data['available_rooms_count'], data['occupied_rooms_count']), (2, 1, 1))
        self.assertEqual(len(data['rooms']), 2)

    def test_property_partial_update_preserves_owner_and_ignores_readonly(self):
        """S2-SER-008 | [Gộp S2-SER-016, 017, 018] Cập nhật partial giữ nguyên trường khác, bỏ qua trường read-only (id, created_at, rooms) và không đổi owner_id khi ADMIN sửa | Data: PATCH name, total_floors | Expected: pk và owner_id không đổi"""
        prop = make_property(name='Cũ', address='Địa chỉ giữ', owner_id=OWNER_ID)
        admin_ctx = serializer_context(fake_user(user_id=7, role='ADMIN'))
        ser = PropertySerializer(
            prop,
            data={'name': 'Mới', 'total_floors': 5, 'id': 9999, 'created_at': '2000-01-01T00:00:00Z', 'rooms': []},
            partial=True,
            context=admin_ctx,
        )
        self.assertTrue(ser.is_valid(), ser.errors)
        saved = ser.save()
        self.assertEqual((saved.pk, saved.owner_id, saved.name, saved.address, saved.total_floors),
                         (prop.pk, OWNER_ID, 'Mới', 'Địa chỉ giữ', 5))


class RoomSerializerTests(TestCase):
    def setUp(self):
        self.prop = make_property(code='NT1')

    def ser(self, **overrides):
        return RoomSerializer(data=room_payload(self.prop, **overrides), context=serializer_context())

    def test_create_valid_room_and_ignore_readonly_fields(self):
        """S2-SER-009 | [Gộp S2-SER-019, 038] Tạo Room hợp lệ sinh mã 'NT1-101' và bỏ qua các trường read-only (id, is_rentable, property_name) | Data: payload hợp lệ + id=9999, is_rentable=False | Expected: lưu thành công, is_rentable=True"""
        ser = self.ser(id=9999, is_rentable=False, property_name='Giả', created_at='2000-01-01T00:00:00Z')
        self.assertTrue(ser.is_valid(), ser.errors)
        room = ser.save()
        self.assertEqual(room.code, 'NT1-101')
        self.assertNotEqual(room.pk, 9999)
        self.assertTrue(room.is_rentable)
        self.assertEqual(ser.data['property_name'], self.prop.name)

    def test_room_required_fields_and_invalid_property_fk(self):
        """S2-SER-010 | [Gộp S2-SER-020, 021, 022, 024] Thiếu trường bắt buộc, giá trị rỗng hoặc property không tồn tại / sai kiểu | Data: {}, room_number='', property=999999/'abc' | Expected: lỗi ở property, room_number, rent_price"""
        empty = RoomSerializer(data={}, context=serializer_context())
        self.assertFalse(empty.is_valid())
        self.assertTrue({'property', 'room_number', 'rent_price'} <= set(empty.errors))

        blank = self.ser(room_number='', rent_price='')
        self.assertFalse(blank.is_valid())
        self.assertTrue({'room_number', 'rent_price'} <= set(blank.errors))

        for bad_prop in (999999, 'abc'):
            with self.subTest(property=bad_prop):
                ser = self.ser(property=bad_prop)
                self.assertFalse(ser.is_valid())
                self.assertIn('property', ser.errors)

    def test_room_numeric_types_and_bug_validators(self):
        """S2-SER-011 | [Gộp S2-SER-023, 025..031 — BUG-01, BUG-02, BUG-04] Kiểm tra sai kiểu số, giá thuê/tiền cọc/chỉ số công tơ âm, thập phân/vượt 12 chữ số, diện tích <=0, tầng ngoài phạm vi 1..total_floors, max_occupants <=0 | Data: parameterized invalid values | Expected: is_valid=False đúng trường"""
        self.assertTrue(self.ser(rent_price=999999999999, deposit_amount=0).is_valid())
        invalid_cases = [
            ('rent_price', 'abc'),
            ('rent_price', -1),
            ('rent_price', '3000000.50'),
            ('rent_price', 10 ** 12),
            ('deposit_amount', -1),
            ('initial_electric_reading', -1),
            ('initial_water_reading', -1),
            ('area', 'abc'),
            ('area', -5),
            ('area', 0),
            ('floor', 'abc'),
            ('floor', 0),
            ('floor', self.prop.total_floors + 1),
            ('max_occupants', 'abc'),
            ('max_occupants', -1),
            ('max_occupants', 0),
        ]
        for field, value in invalid_cases:
            with self.subTest(field=field, value=value):
                ser = self.ser(**{field: value})
                self.assertFalse(ser.is_valid())
                self.assertIn(field, ser.errors)

    def test_room_choices_duplicate_code_and_amenities_boundary(self):
        """S2-SER-012 | [Gộp S2-SER-032, 036, 037] Chặn status/room_type sai, trùng code UNIQUE và biên độ dài amenities (500/501) | Data: status='BOGUS', code='DUP-ROOM', amenities 500 & 501 ký tự | Expected: báo lỗi đúng trường"""
        bad_choices = self.ser(status='BOGUS', room_type='BOGUS')
        self.assertFalse(bad_choices.is_valid())
        self.assertTrue({'status', 'room_type'} <= set(bad_choices.errors))

        make_room(self.prop, room_number='X', code='DUP-ROOM')
        dup = self.ser(code='DUP-ROOM')
        self.assertFalse(dup.is_valid())
        self.assertIn('code', dup.errors)

        self.assertTrue(self.ser(amenities='a' * 500).is_valid())
        too_long = self.ser(amenities='a' * 501)
        self.assertFalse(too_long.is_valid())
        self.assertIn('amenities', too_long.errors)

    def test_occupants_capacity_validation_on_create_and_partial_update(self):
        """S2-SER-013 | [Gộp S2-SER-033, 034, 035] Kiểm tra current_occupants <= max_occupants khi tạo mới (current=2/3, max=2) và khi PATCH partial dựa trên instance.max_occupants | Data: current=2 (OK), current=3 (lỗi), PATCH current=5 (lỗi) | Expected: chặn vượt sức chứa"""
        self.assertTrue(self.ser(current_occupants=2, max_occupants=2).is_valid())
        over = self.ser(current_occupants=3, max_occupants=2)
        self.assertFalse(over.is_valid())
        self.assertIn('current_occupants', over.errors)

        room = make_room(self.prop, max_occupants=2)
        patch_over = RoomSerializer(room, data={'current_occupants': 5}, partial=True, context=serializer_context())
        self.assertFalse(patch_over.is_valid())
        self.assertIn('current_occupants', patch_over.errors)

    def test_output_structure_and_rentability_for_manager(self):
        """S2-SER-014 | [Gộp S2-SER-039, 043] Đầu ra cho LANDLORD/ADMIN hiển thị đầy đủ PII (tenant_name, tenant_phone) và đồng bộ rentability_reason với model | Data: phòng có tenant_name, status=MAINTENANCE | Expected: đủ trường quản lý"""
        room = make_room(self.prop, tenant_name='Nguyễn A', tenant_phone='0900', status='MAINTENANCE')
        data = RoomSerializer(room, context=serializer_context(fake_user(role='LANDLORD'))).data
        for key in (
            'tenant_name', 'tenant_phone', 'maintenance_requests', 'is_rentable', 'rentability_reason',
            'property_code', 'property_name', 'status_display', 'room_type_display', 'active_maintenance_count',
        ):
            self.assertIn(key, data)
        self.assertEqual((data['tenant_name'], data['property_code']), ('Nguyễn A', 'NT1'))
        self.assertFalse(data['is_rentable'])
        self.assertEqual(data['rentability_reason'], room.check_rentability()[1])

    def test_output_hides_private_fields_for_tenant(self):
        """S2-SER-015 | [Từ S2-SER-040] Ẩn thông tin cá nhân người thuê đối với role TENANT | Data: user role=TENANT | Expected: không có tenant_name, tenant_phone, maintenance_requests"""
        room = make_room(self.prop, tenant_name='Nguyễn A', tenant_phone='0900')
        data = RoomSerializer(room, context=serializer_context(fake_user(user_id=5, role='TENANT'))).data
        for key in ('tenant_name', 'tenant_phone', 'maintenance_requests'):
            self.assertNotIn(key, data)
        self.assertIn('rent_price', data)

    def test_output_hides_private_fields_without_request_context(self):
        """S2-SER-016 | [Từ S2-SER-041] Mặc định an toàn (fail-safe) ẩn PII khi serializer không có request context | Data: RoomSerializer(room) | Expected: không có tenant_name"""
        room = make_room(self.prop, tenant_name='Nguyễn A')
        self.assertNotIn('tenant_name', RoomSerializer(room).data)

    def test_active_maintenance_count_counts_only_open_requests(self):
        """S2-SER-017 | [Từ S2-SER-042] active_maintenance_count chỉ đếm yêu cầu đang mở (PENDING, IN_PROGRESS) | Data: 1 PENDING, 1 IN_PROGRESS, 1 COMPLETED | Expected: =2"""
        room = make_room(self.prop)
        for st in (MaintenanceStatus.PENDING, MaintenanceStatus.IN_PROGRESS, MaintenanceStatus.COMPLETED):
            MaintenanceRequest.objects.create(room=room, title=st, status=st)
        data = RoomSerializer(room, context=serializer_context()).data
        self.assertEqual(data['active_maintenance_count'], 2)

    def test_many_serialization_returns_all_rooms(self):
        """S2-SER-018 | [Từ S2-SER-044] Serialize danh sách nhiều phòng (many=True) | Data: 3 phòng | Expected: 3 phần tử đúng giá thuê"""
        for n in ('1', '2', '3'):
            make_room(self.prop, room_number=n, rent_price=1000000 * int(n))
        data = RoomSerializer(Room.objects.all(), many=True, context=serializer_context()).data
        self.assertEqual(len(data), 3)
        self.assertEqual(
            sorted(Decimal(str(d['rent_price'])) for d in data),
            [Decimal('1000000'), Decimal('2000000'), Decimal('3000000')],
        )

    def test_property_serializer_blocks_deleted_status_when_active_rooms_exist(self):
        """S2-SER-019 | PropertySerializer.validate_status chặn đặt status=DELETED khi nhà trọ còn phòng hoạt động | Data: nhà có phòng AVAILABLE vs nhà chỉ có phòng INACTIVE | Expected: is_valid=False (lỗi 'status') khi còn phòng hoạt động; is_valid=True khi phòng đã INACTIVE hoặc đổi sang INACTIVE"""
        make_room(self.prop, room_number='101', status=RoomStatus.AVAILABLE)
        ser_blocked = PropertySerializer(self.prop, data={'status': 'DELETED'}, partial=True,
                                         context=serializer_context())
        self.assertFalse(ser_blocked.is_valid())
        self.assertIn('status', ser_blocked.errors)

        ser_inactive = PropertySerializer(self.prop, data={'status': 'INACTIVE'}, partial=True,
                                          context=serializer_context())
        self.assertTrue(ser_inactive.is_valid(), ser_inactive.errors)

        self.prop.rooms.update(status=RoomStatus.INACTIVE)
        ser_allowed = PropertySerializer(self.prop, data={'status': 'DELETED'}, partial=True,
                                         context=serializer_context())
        self.assertTrue(ser_allowed.is_valid(), ser_allowed.errors)

    def test_room_serializer_blocks_duplicate_room_number_in_same_property(self):
        """S2-SER-020 | RoomSerializer.validate chặn trùng room_number (không phân biệt hoa thường) trong cùng Property và cho phép ở Property khác hoặc cập nhật chính nó | Data: 'A101' vs 'a101' cùng nhà, 'A101' khác nhà | Expected: is_valid=False (lỗi 'room_number') khi trùng; is_valid=True khi hợp lệ"""
        r1 = make_room(self.prop, room_number='A101', rent_price=3000000)
        r2 = make_room(self.prop, room_number='A102', rent_price=3000000)

        dup_create = RoomSerializer(data={'property': self.prop.id, 'room_number': ' a101 ', 'rent_price': 3000000},
                                    context=serializer_context())
        self.assertFalse(dup_create.is_valid())
        self.assertIn('room_number', dup_create.errors)

        dup_update = RoomSerializer(r2, data={'room_number': 'a101'}, partial=True, context=serializer_context())
        self.assertFalse(dup_update.is_valid())
        self.assertIn('room_number', dup_update.errors)

        self_update = RoomSerializer(r1, data={'room_number': 'A101', 'rent_price': 3500000}, partial=True,
                                     context=serializer_context())
        self.assertTrue(self_update.is_valid(), self_update.errors)

        other_prop = make_property(code='P2', name='Nhà 2')
        other_create = RoomSerializer(data={'property': other_prop.id, 'room_number': 'A101', 'rent_price': 3000000},
                                      context=serializer_context())
        self.assertTrue(other_create.is_valid(), other_create.errors)

    def test_room_serializer_blocks_deleted_property_and_normalizes_status_invariants(self):
        """S2-SER-021 | RoomSerializer.validate chặn tạo/chuyển phòng vào Property đã DELETED, chặn đặt INACTIVE khi phòng đang có người ở, và đồng bộ current_occupants theo status (OCCUPIED/FULL/AVAILABLE) | Data: property DELETED, status OCCUPIED/FULL/AVAILABLE/INACTIVE | Expected: báo lỗi khi không hợp lệ; tự chuẩn hóa số người & thông tin khách thuê khi hợp lệ"""
        deleted_prop = make_property(code='DEL', status=PropertyStatus.DELETED)
        ser_del = RoomSerializer(data=room_payload(deleted_prop, room_number='D1'), context=serializer_context())
        self.assertFalse(ser_del.is_valid())
        self.assertIn('property', ser_del.errors)

        ser_occ = self.ser(room_number='O1', status=RoomStatus.OCCUPIED, current_occupants=0, max_occupants=2)
        self.assertTrue(ser_occ.is_valid(), ser_occ.errors)
        r_occ = ser_occ.save()
        self.assertEqual((r_occ.status, r_occ.current_occupants), (RoomStatus.OCCUPIED, 1))

        ser_occ_full = self.ser(room_number='O2', status=RoomStatus.OCCUPIED, current_occupants=2, max_occupants=2)
        self.assertTrue(ser_occ_full.is_valid(), ser_occ_full.errors)
        r_occ_full = ser_occ_full.save()
        self.assertEqual((r_occ_full.status, r_occ_full.current_occupants), (RoomStatus.FULL, 2))

        ser_full = self.ser(room_number='F1', status=RoomStatus.FULL, max_occupants=3)
        self.assertTrue(ser_full.is_valid(), ser_full.errors)
        r_full = ser_full.save()
        self.assertEqual((r_full.status, r_full.current_occupants), (RoomStatus.FULL, 3))

        ser_inact = RoomSerializer(r_occ, data={'status': RoomStatus.INACTIVE}, partial=True,
                                   context=serializer_context())
        self.assertFalse(ser_inact.is_valid())
        self.assertIn('status', ser_inact.errors)

        r_occ. tenant_name = 'Nguyễn A'
        r_occ.tenant_phone = '0900'
        r_occ.save()
        ser_avail = RoomSerializer(r_occ, data={'status': RoomStatus.AVAILABLE}, partial=True,
                                   context=serializer_context())
        self.assertTrue(ser_avail.is_valid(), ser_avail.errors)
        r_avail = ser_avail.save()
        self.assertEqual((r_avail.status, r_avail.current_occupants, r_avail.tenant_name, r_avail.tenant_phone),
                         (RoomStatus.AVAILABLE, 0, '', ''))

        ser_inact_ok = RoomSerializer(r_avail, data={'status': RoomStatus.INACTIVE}, partial=True,
                                      context=serializer_context())
        self.assertTrue(ser_inact_ok.is_valid(), ser_inact_ok.errors)
        self.assertEqual(ser_inact_ok.save().status, RoomStatus.INACTIVE)

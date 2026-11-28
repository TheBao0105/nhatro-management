"""[PURE UNIT] Model Tests for Service 2 (Property, Room, MaintenanceRequest, MaintenanceHistory).

Optimized suite: 15 cohesive, parameterized unit tests (consolidated from 46 granular tests
S2-MOD-001..046 with 0 loss of assertion or branch coverage).
"""
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase

from services.property_service.models import (
    RENTED_STATUSES,
    MaintenanceHistory,
    MaintenanceRequest,
    MaintenanceStatus,
    Property,
    PropertyStatus,
    Room,
    RoomStatus,
    RoomType,
)
from .base import make_property, make_room


class PropertyModelTests(TestCase):
    def test_create_property_defaults_str_and_computed_addresses(self):
        """S2-MOD-001 | [Gộp S2-MOD-001, 007, 008, 009, 014] Tạo Property hợp lệ, giá trị mặc định, __str__, full_address và area_location | Data: name, address, ward='' | Expected: lưu DB đúng mặc định, __str__='NT9 - Nhà A', bỏ phần rỗng trong địa chỉ"""
        prop = Property.objects.create(
            code='NT9', name='Nhà A', address='12 Lê Lợi', ward='', district='Quận 1', city='TP. Hồ Chí Minh',
        )
        prop.refresh_from_db()
        self.assertIsNotNone(prop.pk)
        self.assertEqual((prop.city, prop.total_floors, prop.owner_id), ('TP. Hồ Chí Minh', 1, 1))
        self.assertEqual((prop.electricity_rate, prop.water_rate, prop.internet_rate), (3500, 20000, 100000))
        self.assertEqual(prop.status, PropertyStatus.ACTIVE)
        self.assertEqual(set(PropertyStatus.values), {'ACTIVE', 'INACTIVE', 'DELETED'})
        self.assertEqual(str(prop), 'NT9 - Nhà A')
        self.assertEqual(prop.full_address, '12 Lê Lợi, Quận 1, TP. Hồ Chí Minh')
        prop.ward = 'Phường Bến Nghé'
        self.assertEqual(prop.area_location, 'Phường Bến Nghé, Quận 1, TP. Hồ Chí Minh')

    def test_property_auto_code_generation_and_collision_skip(self):
        """S2-MOD-002 | [Gộp S2-MOD-002, 003, 004] Tự sinh mã nhà trọ tăng dần NT001, NT002 và nhảy qua mã đã tồn tại | Data: tạo 2 nhà + tạo sẵn NT004 rồi tạo tiếp | Expected: NT001, NT002, NT004 -> NT005"""
        first = Property.objects.create(name='A', address='a')
        second = Property.objects.create(name='B', address='b')
        Property.objects.create(name='C', address='c', code='NT004')
        skipped = Property.objects.create(name='D', address='d')
        self.assertEqual((first.code, second.code, skipped.code), ('NT001', 'NT002', 'NT005'))

    def test_property_explicit_code_preserved_and_unique_constraint(self):
        """S2-MOD-003 | [Gộp S2-MOD-005, 006] Giữ nguyên code truyền vào và chặn trùng UNIQUE | Data: 2 Property cùng code='ABC-1' | Expected: nhà 1 giữ 'ABC-1'; nhà 2 ném IntegrityError"""
        p1 = Property.objects.create(name='A', address='a', code='ABC-1')
        self.assertEqual(p1.code, 'ABC-1')
        with self.assertRaises(IntegrityError), transaction.atomic():
            Property.objects.create(name='B', address='b', code='ABC-1')

    def test_property_field_validations_and_boundaries(self):
        """S2-MOD-004 | [Gộp S2-MOD-010, 011, 012, 013] Kiểm tra full_clean cho name, address, status, total_floors>=1 và biên độ dài name (150/151) | Data: name='', address='', status='BOGUS', total_floors=0, name 150 & 151 ký tự | Expected: ValidationError đúng trường"""
        Property(name='x' * 150, address='a', total_floors=1).full_clean()
        cases = [
            ({'name': '', 'address': 'a'}, 'name'),
            ({'name': 'A', 'address': ''}, 'address'),
            ({'name': 'A', 'address': 'a', 'status': 'BOGUS'}, 'status'),
            ({'name': 'x' * 151, 'address': 'a'}, 'name'),
            ({'name': 'A', 'address': 'a', 'total_floors': 0}, 'total_floors'),
        ]
        for kwargs, field in cases:
            with self.subTest(field=field, kwargs=kwargs):
                with self.assertRaises(ValidationError) as ctx:
                    Property(**kwargs).full_clean()
                self.assertIn(field, ctx.exception.message_dict)

    def test_property_room_count_aggregates_and_active_queryset(self):
        """S2-MOD-005 | [Gộp S2-MOD-015, 016, 018] Bộ đếm phòng khi nhà trống và khi có 6 phòng đủ trạng thái + active_rooms_qs | Data: 0 phòng -> 6 phòng | Expected: 0 ban đầu; sau đó total=6, available=1, occupied=2, full=1, maintenance=1, inactive=1"""
        prop = make_property()
        self.assertEqual((prop.total_rooms_count, prop.available_rooms_count, prop.occupied_rooms_count), (0, 0, 0))
        created = {}
        for number, st in enumerate([
            RoomStatus.AVAILABLE, RoomStatus.OCCUPIED, RoomStatus.FULL,
            RoomStatus.RESERVED, RoomStatus.MAINTENANCE, RoomStatus.INACTIVE,
        ]):
            created[st] = make_room(prop, room_number=f'R{number}', status=st)
        self.assertEqual(prop.total_rooms_count, 6)
        self.assertEqual(prop.available_rooms_count, 1)
        self.assertEqual(prop.occupied_rooms_count, 2)
        self.assertEqual(prop.full_rooms_count, 1)
        self.assertEqual(prop.maintenance_rooms_count, 1)
        self.assertEqual(prop.inactive_rooms_count, 1)
        self.assertNotIn(created[RoomStatus.INACTIVE], list(prop.active_rooms_qs))
        self.assertEqual(prop.active_rooms_qs.count(), 5)

    def test_deleting_property_cascades_rooms(self):
        """S2-MOD-006 | [Từ S2-MOD-017] FK CASCADE Property -> Room | Data: xóa Property có 2 phòng | Expected: các phòng thuộc nhà trọ bị xóa theo"""
        prop = make_property()
        make_room(prop, room_number='A')
        make_room(prop, room_number='B')
        prop.delete()
        self.assertEqual(Room.objects.count(), 0)


class RoomModelTests(TestCase):
    def setUp(self):
        self.prop = make_property(code='NT001')

    def test_create_room_defaults_str_and_ordering(self):
        """S2-MOD-007 | [Gộp S2-MOD-019, 024, 027, 028, 029] Tạo Room mặc định, __str__, enum RoomStatus/RoomType và thứ tự sắp xếp (property, floor, room_number) | Data: 3 phòng tầng 1-2 | Expected: mặc định đúng, sắp xếp [1/101, 1/102, 2/101]"""
        room = Room.objects.create(property=self.prop, room_number='101', rent_price=2500000)
        room.refresh_from_db()
        self.assertEqual((room.floor, room.room_type, room.area, room.deposit_amount), (1, RoomType.MEZZANINE, 20.0, 0))
        self.assertEqual((room.max_occupants, room.current_occupants, room.status), (2, 0, RoomStatus.AVAILABLE))
        self.assertEqual((room.initial_electric_reading, room.initial_water_reading), (0.0, 0.0))
        self.assertEqual(str(room), 'NT001-101 (101)')
        self.assertEqual(set(RoomStatus.values), {'AVAILABLE', 'OCCUPIED', 'FULL', 'RESERVED', 'MAINTENANCE', 'INACTIVE'})
        self.assertEqual(set(RENTED_STATUSES), {RoomStatus.OCCUPIED, RoomStatus.FULL})
        self.assertEqual(set(RoomType.values), {'SINGLE', 'MEZZANINE', 'STUDIO', 'ONE_BED', 'DORM'})

        make_room(self.prop, room_number='099', floor=2)
        make_room(self.prop, room_number='102', floor=1)
        self.assertEqual([(r.floor, r.room_number) for r in Room.objects.all()], [(1, '101'), (1, '102'), (2, '099')])

    def test_room_auto_code_normalization_and_collision_suffix(self):
        """S2-MOD-008 | [Gộp S2-MOD-020, 021, 022] Tự sinh mã phòng, chuẩn hóa ký tự đặc biệt và thêm hậu tố '-2' khi trùng | Data: '101', 'a-01 vip', '10-1' (chuẩn hóa trùng mã 'NT001-101') | Expected: 'NT001-101', 'NT001-A01VIP', 'NT001-101-2'"""
        r1 = make_room(self.prop, room_number='101')
        r_norm = make_room(self.prop, room_number='a-01 vip')
        r2 = make_room(self.prop, room_number='10-1')
        self.assertEqual((r1.code, r_norm.code, r2.code), ('NT001-101', 'NT001-A01VIP', 'NT001-101-2'))

    def test_room_explicit_code_unique_and_property_fk_required(self):
        """S2-MOD-009 | [Gộp S2-MOD-023, 025, 026] Giữ code truyền vào, UNIQUE code và bắt buộc FK property | Data: trùng code='X1', thiếu property | Expected: IntegrityError khi trùng code hoặc thiếu property"""
        r1 = make_room(self.prop, room_number='1', code='X1')
        self.assertEqual((r1.code, r1.property), ('X1', self.prop))
        with self.assertRaises(IntegrityError), transaction.atomic():
            make_room(self.prop, room_number='2', code='X1')
        with self.assertRaises(IntegrityError), transaction.atomic():
            Room.objects.create(room_number='NoProp', rent_price=1)

    def test_room_unique_room_number_per_property_constraint(self):
        """S2-MOD-016 | UniqueConstraint (property, room_number) ở tầng Database | Data: trùng room_number='101' cùng nhà trọ vs khác nhà trọ | Expected: IntegrityError khi cùng Property; thành công khi khác Property"""
        make_room(self.prop, room_number='101', code='C1')
        with self.assertRaises(IntegrityError), transaction.atomic():
            make_room(self.prop, room_number='101', code='C2')
        other_prop = make_property(name='Nhà Khác', code='NT002')
        other_room = make_room(other_prop, room_number='101', code='C3')
        self.assertEqual((other_room.property_id, other_room.room_number), (other_prop.id, '101'))

    def test_room_field_validations_and_bug_fixes(self):
        """S2-MOD-010 | [Gộp S2-MOD-030..037] Kiểm tra full_clean của Room (BUG-01 rent_price/deposit_amount<0, BUG-02 area<=0, BUG-04 max_occupants<1, chỉ số điện/nước ban đầu<0, biên max_digits=12, biên room_number=60) | Data: biên hợp lệ & không hợp lệ | Expected: ValidationError đúng trường"""
        Room(property=self.prop, room_number='9' * 60, rent_price=Decimal('999999999999'), deposit_amount=0, area=0.5, max_occupants=1).full_clean()
        invalid_cases = [
            ({'status': 'BOGUS'}, 'status'),
            ({'max_occupants': -1}, 'max_occupants'),
            ({'max_occupants': 0}, 'max_occupants'),
            ({'current_occupants': -1}, 'current_occupants'),
            ({'rent_price': Decimal(10 ** 12)}, 'rent_price'),
            ({'rent_price': -1}, 'rent_price'),
            ({'deposit_amount': -1}, 'deposit_amount'),
            ({'initial_electric_reading': -0.1}, 'initial_electric_reading'),
            ({'initial_water_reading': -0.1}, 'initial_water_reading'),
            ({'area': -5}, 'area'),
            ({'area': 0}, 'area'),
            ({'room_number': '9' * 61}, 'room_number'),
            ({'room_number': ''}, 'room_number'),
        ]
        for overrides, field in invalid_cases:
            with self.subTest(field=field, overrides=overrides):
                base = {'property': self.prop, 'room_number': '1', 'rent_price': 1000}
                base.update(overrides)
                with self.assertRaises(ValidationError) as ctx:
                    Room(**base).full_clean()
                self.assertIn(field, ctx.exception.message_dict)


class RoomRentabilityAndMaintenanceModelTests(TestCase):
    def setUp(self):
        self.prop = make_property(name='Nhà R', code='NR')

    def test_available_room_in_active_property_is_rentable(self):
        """S2-MOD-011 | [Từ S2-MOD-038] Phòng AVAILABLE trong nhà ACTIVE | Data: AVAILABLE, property ACTIVE | Expected: is_rentable=True, check_rentability=(True, '...trống...')"""
        room = make_room(self.prop)
        can_rent, reason = room.check_rentability()
        self.assertTrue(room.is_rentable)
        self.assertTrue(can_rent)
        self.assertIn('trống', reason)

    def test_room_not_rentable_when_property_inactive(self):
        """S2-MOD-012 | [Từ S2-MOD-040] Nhà trọ INACTIVE thì phòng AVAILABLE cũng không cho thuê | Data: property INACTIVE | Expected: is_rentable=False, reason nêu tên nhà trọ"""
        self.prop.status = PropertyStatus.INACTIVE
        self.prop.save()
        room = make_room(self.prop)
        can_rent, reason = room.check_rentability()
        self.assertFalse(room.is_rentable)
        self.assertFalse(can_rent)
        self.assertIn('Nhà R', reason)

    def test_non_available_statuses_and_unknown_fallback_reasons(self):
        """S2-MOD-013 | [Gộp S2-MOD-039, 041, 042, 044] Lý do check_rentability cho OCCUPIED (còn chỗ), FULL, RESERVED, MAINTENANCE, INACTIVE và nhánh fallback UNKNOWN_STATE | Data: 6 trạng thái | Expected: is_rentable=False, lý do khớp từng trạng thái"""
        occ = make_room(self.prop, room_number='OCC', status=RoomStatus.OCCUPIED, max_occupants=3, current_occupants=1)
        self.assertFalse(occ.is_rentable)
        self.assertIn('1/3', occ.check_rentability()[1])
        self.assertIn('còn 2', occ.check_rentability()[1])

        expected = {
            RoomStatus.FULL: 'đủ số người',
            RoomStatus.RESERVED: 'đặt cọc',
            RoomStatus.MAINTENANCE: 'bảo trì',
            RoomStatus.INACTIVE: 'ngừng hoạt động',
        }
        for st, keyword in expected.items():
            with self.subTest(status=st):
                room = make_room(self.prop, room_number=f'K-{st}', status=st)
                self.assertFalse(room.is_rentable)
                can_rent, reason = room.check_rentability()
                self.assertFalse(can_rent)
                self.assertIn(keyword, reason)

        unknown = Room(property=self.prop, room_number='U1', rent_price=1000000, status='UNKNOWN_STATE')
        self.assertEqual(unknown.check_rentability(), (False, 'Không xác định.'))

    def test_maintenance_request_auto_code_collision_and_is_open(self):
        """S2-MOD-014 | [Ngoài Sprint 1] [Gộp S2-MOD-043, 045] Quan hệ Room-MaintenanceRequest, thuộc tính is_open, giữ code truyền sẵn và tự tăng mã BTxxxx khi trùng | Data: tạo BT0002 rồi tạo mới không code | Expected: is_open=True, mã kế tiếp là BT0003"""
        room = make_room(self.prop)
        explicit = MaintenanceRequest.objects.create(room=room, title='Đã có mã', code='BT0002')
        auto_next = MaintenanceRequest.objects.create(room=room, title='Tự sinh né trùng')
        self.assertEqual(room.maintenance_requests.count(), 2)
        self.assertEqual((explicit.code, auto_next.code), ('BT0002', 'BT0003'))
        self.assertEqual(auto_next.status, MaintenanceStatus.PENDING)
        self.assertTrue(auto_next.is_open)

    def test_maintenance_request_and_history_str_representations(self):
        """S2-MOD-015 | [Ngoài Sprint 1] [Từ S2-MOD-046] __str__ của MaintenanceRequest và MaintenanceHistory | Data: code='BT0001', title='Hỏng đèn', action='Tạo mới' | Expected: 'BT0001 - Hỏng đèn' và 'BT0001 - Tạo mới'"""
        room = make_room(self.prop)
        req = MaintenanceRequest.objects.create(room=room, title='Hỏng đèn', code='BT0001')
        hist = MaintenanceHistory.objects.create(maintenance_request=req, room=room, action='Tạo mới')
        self.assertEqual(str(req), 'BT0001 - Hỏng đèn')
        self.assertEqual(str(hist), 'BT0001 - Tạo mới')

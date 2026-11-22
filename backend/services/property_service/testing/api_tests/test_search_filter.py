"""[API/INTEGRATION] Tìm kiếm / Lọc / Sắp xếp Phòng và Nhà trọ (Sprint 1)."""
from datetime import timedelta

from django.test import TestCase
from django.utils import timezone
from rest_framework import status

from common.testing import jwt_client
from services.property_service.models import (
    MaintenanceHistory, MaintenancePriority, MaintenanceRequest, MaintenanceStatus,
    Property, PropertyStatus, Room,
)
from ..unit_tests.base import OWNER_ID, make_property, make_room, patch_rented_rooms


class RoomSearchFilterBase(TestCase):
    """Fixture: 2 nhà, 5 phòng (giá/diện tích/tầng/sức chứa/trạng thái khác nhau)."""

    @classmethod
    def setUpTestData(cls):
        cls.p1 = make_property(code='HM', name='Hoa Mai Boarding', district='Bình Thạnh', ward='Phường 25',
                               address='Nguyễn Gia Trí')
        cls.p2 = make_property(code='HH', name='Happy House', district='Quận 7', ward='Tân Phong',
                               address='Đường số 7')
        specs = [
            (cls.p1, 'A101', 1, 18, 2000000, 2, 'AVAILABLE', 0, ''),
            (cls.p1, 'A102', 1, 25, 3000000, 3, 'OCCUPIED', 1, 'Nguyễn Văn A'),
            (cls.p1, 'A201', 2, 30, 4000000, 4, 'AVAILABLE', 0, ''),
            (cls.p2, 'B101', 1, 22, 2500000, 2, 'MAINTENANCE', 0, ''),
            (cls.p2, 'B201', 2, 40, 6000000, 2, 'FULL', 2, ''),
        ]
        base = timezone.now() - timedelta(days=10)
        for index, (prop, number, floor, area, price, cap, st, occ, tenant) in enumerate(specs):
            room = make_room(prop, room_number=number, floor=floor, area=area, rent_price=price,
                             max_occupants=cap, status=st, current_occupants=occ, tenant_name=tenant)
            Room.objects.filter(pk=room.pk).update(created_at=base + timedelta(hours=index))

    def setUp(self):
        self.client = jwt_client(OWNER_ID, 'LANDLORD')

    def numbers(self, query):
        res = self.client.get(f'/api/rooms/?{query}')
        self.assertEqual(res.status_code, status.HTTP_200_OK, getattr(res, 'data', None))
        return [r['room_number'] for r in res.data]


class RoomSearchTests(RoomSearchFilterBase):
    def test_search_by_room_number_partial_case_insensitive(self):
        """S2-FLT-001 | Tìm theo tên/số phòng (một phần, không phân biệt hoa thường) | Data: search=a10 | Expected: A101, A102"""
        self.assertEqual(self.numbers('search=a10'), ['A101', 'A102'])

    def test_search_by_room_code(self):
        """S2-FLT-002 | Tìm theo mã phòng | Data: search=hm-a201 | Expected: A201"""
        self.assertEqual(self.numbers('search=hm-a201'), ['A201'])

    def test_search_by_property_name(self):
        """S2-FLT-003 | Tìm theo tên nhà trọ | Data: search=happy | Expected: B101, B201"""
        self.assertEqual(self.numbers('search=happy'), ['B101', 'B201'])

    def test_search_by_district_ward_address(self):
        """S2-FLT-004 | Tìm theo quận / phường / địa chỉ | Data: 'Quận 7', 'Phường 25', 'Gia Trí' | Expected: phòng B*, A*, A* tương ứng"""
        self.assertEqual(self.numbers('search=Quận 7'), ['B101', 'B201'])
        self.assertEqual(self.numbers('search=Phường 25'), ['A101', 'A102', 'A201'])
        self.assertEqual(self.numbers('search=Gia Trí'), ['A101', 'A102', 'A201'])

    def test_search_no_result_returns_empty_list(self):
        """S2-FLT-005 | Tìm không có kết quả | Data: search=zzzzzz | Expected: 200, []"""
        self.assertEqual(self.numbers('search=zzzzzz'), [])

    def test_search_by_tenant_name_for_manager(self):
        """S2-FLT-006 | Chủ trọ tìm theo tên người thuê | Data: search='Nguyễn Văn A' | Expected: A102"""
        self.assertEqual(self.numbers('search=Nguyễn Văn A'), ['A102'])

    def test_tenant_cannot_search_by_other_tenant_name(self):
        """S2-FLT-007 | TENANT không tìm theo tên người thuê | Data: TENANT thuê A102, search='Nguyễn Văn A' | Expected: [] (không rò rỉ qua tìm kiếm)"""
        room = Room.objects.get(room_number='A102')
        tenant = jwt_client(555, 'TENANT')
        with patch_rented_rooms([room.id]):
            res = tenant.get('/api/rooms/?search=Nguyễn Văn A')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, [])

    def test_search_empty_string_returns_all(self):
        """S2-FLT-008 | search rỗng | Data: search= | Expected: toàn bộ 5 phòng"""
        self.assertEqual(len(self.numbers('search=')), 5)


class RoomFilterTests(RoomSearchFilterBase):
    def test_filter_by_property_id_and_alias(self):
        """S2-FLT-009 | Lọc theo nhà trọ | Data: property_id và property | Expected: 3 phòng của p1 cho cả hai tham số"""
        expected = ['A101', 'A102', 'A201']
        self.assertEqual(self.numbers(f'property_id={self.p1.id}'), expected)
        self.assertEqual(self.numbers(f'property={self.p1.id}'), expected)

    def test_filter_by_district_ward_address(self):
        """S2-FLT-010 | Lọc theo quận / phường / địa chỉ | Data: district=Quận 7; ward=Tân Phong; address=Gia Trí | Expected: B*, B*, A*"""
        self.assertEqual(self.numbers('district=Quận 7'), ['B101', 'B201'])
        self.assertEqual(self.numbers('ward=Tân Phong'), ['B101', 'B201'])
        self.assertEqual(self.numbers('address=Gia Trí'), ['A101', 'A102', 'A201'])

    def test_filter_by_floor(self):
        """S2-FLT-011 | Lọc theo tầng | Data: floor=2 | Expected: A201, B201"""
        self.assertEqual(self.numbers('floor=2'), ['A201', 'B201'])

    def test_filter_by_status_case_insensitive(self):
        """S2-FLT-012 | Lọc theo trạng thái | Data: AVAILABLE, available, FULL | Expected: [A101,A201] (cả hoa/thường), [B201]"""
        self.assertEqual(self.numbers('status=AVAILABLE'), ['A101', 'A201'])
        self.assertEqual(self.numbers('status=available'), ['A101', 'A201'])
        self.assertEqual(self.numbers('status=FULL'), ['B201'])

    def test_filter_status_all_returns_everything(self):
        """S2-FLT-013 | status=ALL | Data: ALL | Expected: 5 phòng"""
        self.assertEqual(len(self.numbers('status=ALL')), 5)

    def test_filter_status_without_matches_returns_empty(self):
        """S2-FLT-014 | Lọc trạng thái không có phòng | Data: RESERVED / INACTIVE | Expected: []"""
        self.assertEqual(self.numbers('status=RESERVED'), [])
        self.assertEqual(self.numbers('status=INACTIVE'), [])

    def test_filter_min_price_is_inclusive(self):
        """S2-FLT-015 | Lọc giá tối thiểu (biên bao gồm) | Data: min_price=3000000 | Expected: A102 (=3tr), A201, B201"""
        self.assertEqual(self.numbers('min_price=3000000'), ['A102', 'A201', 'B201'])

    def test_filter_max_price_is_inclusive(self):
        """S2-FLT-016 | Lọc giá tối đa (biên bao gồm) | Data: max_price=3000000 | Expected: A101, A102, B101"""
        self.assertEqual(self.numbers('max_price=3000000'), ['A101', 'A102', 'B101'])

    def test_filter_price_range(self):
        """S2-FLT-017 | Lọc khoảng giá | Data: min=2500000, max=4000000 | Expected: A102, A201, B101"""
        self.assertEqual(self.numbers('min_price=2500000&max_price=4000000'), ['A102', 'A201', 'B101'])

    def test_filter_price_range_without_results(self):
        """S2-FLT-018 | Khoảng giá không có phòng | Data: min=7000000 | Expected: []; min>max cũng []"""
        self.assertEqual(self.numbers('min_price=7000000'), [])
        self.assertEqual(self.numbers('min_price=5000000&max_price=1000000'), [])

    def test_filter_area_range(self):
        """S2-FLT-019 | Lọc diện tích | Data: min_area=25; max_area=22; 22..30 | Expected: [A102,A201,B201]; [A101,B101]; [A102,A201,B101]"""
        self.assertEqual(self.numbers('min_area=25'), ['A102', 'A201', 'B201'])
        self.assertEqual(self.numbers('max_area=22'), ['A101', 'B101'])
        self.assertEqual(self.numbers('min_area=22&max_area=30'), ['A102', 'A201', 'B101'])

    def test_filter_max_occupants_exact(self):
        """S2-FLT-020 | Lọc theo số người tối đa (khớp chính xác) | Data: max_occupants=2 | Expected: A101, B101, B201"""
        self.assertEqual(self.numbers('max_occupants=2'), ['A101', 'B101', 'B201'])

    def test_combined_filters(self):
        """S2-FLT-021 | Kết hợp nhiều điều kiện | Data: property_id=p1 & status=AVAILABLE & min_price=3000000 | Expected: A201"""
        self.assertEqual(self.numbers(f'property_id={self.p1.id}&status=AVAILABLE&min_price=3000000'), ['A201'])

    def test_combined_search_and_filters(self):
        """S2-FLT-022 | Kết hợp tìm kiếm + lọc | Data: search=house & floor=2 & max_price=6000000 | Expected: B201"""
        self.assertEqual(self.numbers('search=house&floor=2&max_price=6000000'), ['B201'])

    def test_combined_filters_without_results(self):
        """S2-FLT-023 | Kết hợp điều kiện mâu thuẫn | Data: status=FULL & max_price=1000000 | Expected: []"""
        self.assertEqual(self.numbers('status=FULL&max_price=1000000'), [])

    def test_invalid_numeric_filters_return_400(self):
        """S2-FLT-024 | Tham số lọc số không hợp lệ | Data: min_price/max_price/min_area/max_area/floor/max_occupants/property_id='abc' | Expected: 400 (không phải 500)"""
        for param in ('min_price', 'max_price', 'min_area', 'max_area', 'floor', 'max_occupants', 'property_id'):
            with self.subTest(param=param):
                res = self.client.get(f'/api/rooms/?{param}=abc')
                self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_filter_by_other_landlords_property_returns_empty(self):
        """S2-FLT-025 | Lọc theo nhà của chủ khác | Data: property_id nhà owner 202 | Expected: [] (không rò rỉ)"""
        other = make_property(owner_id=202, code='OT')
        make_room(other, room_number='X1')
        self.assertEqual(self.numbers(f'property_id={other.id}'), [])


class RoomSortTests(RoomSearchFilterBase):
    def test_sort_price(self):
        """S2-FLT-026 | Sắp xếp theo giá | Data: sort=price_asc / price_desc | Expected: tăng dần / giảm dần"""
        self.assertEqual(self.numbers('sort=price_asc'), ['A101', 'B101', 'A102', 'A201', 'B201'])
        self.assertEqual(self.numbers('sort=price_desc'), ['B201', 'A201', 'A102', 'B101', 'A101'])

    def test_sort_area(self):
        """S2-FLT-027 | Sắp xếp theo diện tích | Data: area_asc / area_desc | Expected: tăng dần / giảm dần"""
        self.assertEqual(self.numbers('sort=area_asc'), ['A101', 'B101', 'A102', 'A201', 'B201'])
        self.assertEqual(self.numbers('sort=area_desc'), ['B201', 'A201', 'A102', 'B101', 'A101'])

    def test_sort_name(self):
        """S2-FLT-028 | Sắp xếp theo tên phòng | Data: name_asc / name_desc | Expected: A101..B201 và ngược lại"""
        self.assertEqual(self.numbers('sort=name_asc'), ['A101', 'A102', 'A201', 'B101', 'B201'])
        self.assertEqual(self.numbers('sort=name_desc'), ['B201', 'B101', 'A201', 'A102', 'A101'])

    def test_sort_created(self):
        """S2-FLT-029 | Sắp xếp theo ngày tạo | Data: created_asc / created_desc | Expected: thứ tự tạo / đảo ngược"""
        self.assertEqual(self.numbers('sort=created_asc'), ['A101', 'A102', 'A201', 'B101', 'B201'])
        self.assertEqual(self.numbers('sort=created_desc'), ['B201', 'B101', 'A201', 'A102', 'A101'])

    def test_ordering_alias_parameter(self):
        """S2-FLT-030 | Tham số alias ordering | Data: ordering=price_desc | Expected: giống sort=price_desc"""
        self.assertEqual(self.numbers('ordering=price_desc'), self.numbers('sort=price_desc'))

    def test_unknown_sort_falls_back_to_default_order(self):
        """S2-FLT-031 | Giá trị sort không hợp lệ | Data: sort=bogus | Expected: 200, thứ tự mặc định (nhà, tầng, tên phòng)"""
        self.assertEqual(self.numbers('sort=bogus'), ['A101', 'A102', 'A201', 'B101', 'B201'])

    def test_sort_combined_with_filter(self):
        """S2-FLT-032 | Sắp xếp kết hợp lọc | Data: status=AVAILABLE & sort=price_desc | Expected: A201, A101"""
        self.assertEqual(self.numbers('status=AVAILABLE&sort=price_desc'), ['A201', 'A101'])


class PropertySearchFilterTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.p1 = make_property(code='HM', name='Hoa Mai Boarding', district='Bình Thạnh', ward='Phường 25',
                               address='Nguyễn Gia Trí', city='TP. Hồ Chí Minh')
        cls.p2 = make_property(code='HH', name='Happy House', district='Quận 7', ward='Tân Phong',
                               address='Đường số 7', city='TP. Hồ Chí Minh')
        cls.p3 = make_property(code='OLD', name='Nhà cũ', status=PropertyStatus.DELETED)
        cls.p4 = make_property(code='PAUSE', name='Nhà tạm ngưng', status=PropertyStatus.INACTIVE)

    def setUp(self):
        self.client = jwt_client(OWNER_ID, 'LANDLORD')

    def codes(self, query=''):
        res = self.client.get(f'/api/properties/?{query}')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        return sorted(p['code'] for p in res.data)

    def test_default_list_hides_deleted(self):
        """S2-FLT-033 | Danh sách mặc định | Data: 4 nhà (1 DELETED) | Expected: HH, HM, PAUSE"""
        self.assertEqual(self.codes(), ['HH', 'HM', 'PAUSE'])

    def test_search_property_by_each_field(self):
        """S2-FLT-034 | Tìm nhà theo tên/mã/địa chỉ/phường/quận/thành phố | Data: hoa; hh; Gia Trí; Tân Phong; Quận 7; Hồ Chí Minh | Expected: HM; HH; HM; HH; HH; HH+HM+PAUSE (cả 3 nhà chưa xóa có city mặc định)"""
        self.assertEqual(self.codes('search=hoa'), ['HM'])
        self.assertEqual(self.codes('search=hh'), ['HH'])
        self.assertEqual(self.codes('search=Gia Trí'), ['HM'])
        self.assertEqual(self.codes('search=Tân Phong'), ['HH'])
        self.assertEqual(self.codes('search=Quận 7'), ['HH'])
        self.assertEqual(self.codes('search=Hồ Chí Minh'), ['HH', 'HM', 'PAUSE'])

    def test_search_property_no_result(self):
        """S2-FLT-035 | Tìm nhà không có kết quả | Data: search=zzzz | Expected: []"""
        self.assertEqual(self.codes('search=zzzz'), [])

    def test_filter_property_by_status(self):
        """S2-FLT-036 | Lọc nhà theo trạng thái | Data: ACTIVE, INACTIVE, DELETED | Expected: [HH,HM], [PAUSE], [OLD]"""
        self.assertEqual(self.codes('status=ACTIVE'), ['HH', 'HM'])
        self.assertEqual(self.codes('status=INACTIVE'), ['PAUSE'])
        self.assertEqual(self.codes('status=DELETED'), ['OLD'])

    def test_filter_property_status_all_and_include_deleted(self):
        """S2-FLT-037 | status=ALL và include_deleted=true | Data: tham số | Expected: cả 4 nhà (kể cả DELETED)"""
        self.assertEqual(self.codes('status=ALL'), ['HH', 'HM', 'OLD', 'PAUSE'])
        self.assertEqual(self.codes('include_deleted=true'), ['HH', 'HM', 'OLD', 'PAUSE'])

    def test_filter_property_by_district_and_ward(self):
        """S2-FLT-038 | Lọc nhà theo quận / phường | Data: district=Quận 7; ward=Phường 25 | Expected: [HH]; [HM]"""
        self.assertEqual(self.codes('district=Quận 7'), ['HH'])
        self.assertEqual(self.codes('ward=Phường 25'), ['HM'])

    def test_filter_property_unknown_status_returns_empty(self):
        """S2-FLT-039 | Lọc nhà theo trạng thái lạ | Data: status=XYZ | Expected: []"""
        self.assertEqual(self.codes('status=XYZ'), [])

    def test_combined_property_filters(self):
        """S2-FLT-040 | Kết hợp tìm kiếm + lọc nhà | Data: search=house & status=ACTIVE & district=Quận 7 | Expected: [HH]"""
        self.assertEqual(self.codes('search=house&status=ACTIVE&district=Quận 7'), ['HH'])


class MaintenanceReadFilterTests(TestCase):
    """[API/INTEGRATION — Ngoài Sprint 1] Kiểm thử bộ lọc GET /api/maintenance/ và GET /api/maintenance-history/ (đọc không bị khóa bởi SprintFeatureLock)."""

    @classmethod
    def setUpTestData(cls):
        cls.p1 = make_property(code='MP1', name='Nhà Bảo Trì 1')
        cls.p2 = make_property(code='MP2', name='Nhà Bảo Trì 2')
        cls.r1 = make_room(cls.p1, room_number='101')
        cls.r2 = make_room(cls.p2, room_number='202')
        cls.m1 = MaintenanceRequest.objects.create(
            room=cls.r1, code='BT0101', title='Hỏng máy lạnh', description='Không mát',
            priority=MaintenancePriority.HIGH, status=MaintenanceStatus.PENDING,
        )
        cls.m2 = MaintenanceRequest.objects.create(
            room=cls.r2, code='BT0202', title='Rò nước bồn rửa', description='Rò nhẹ',
            priority=MaintenancePriority.LOW, status=MaintenanceStatus.COMPLETED,
        )
        cls.h1 = MaintenanceHistory.objects.create(
            maintenance_request=cls.m1, room=cls.r1, action='Tạo yêu cầu 1',
        )
        cls.h2 = MaintenanceHistory.objects.create(
            maintenance_request=cls.m2, room=cls.r2, action='Hoàn thành 2',
        )

    def setUp(self):
        self.client = jwt_client(OWNER_ID, 'LANDLORD')

    def test_filter_maintenance_requests_and_detail_history(self):
        """S2-FLT-041 | [Ngoài Sprint 1] Lọc GET /api/maintenance/ theo room_id, property_id, status, priority, search & xem /history/ | Data: 2 yêu cầu BT0101, BT0202 | Expected: 200, trả đúng bản ghi khớp bộ lọc"""
        self.assertEqual(len(self.client.get('/api/maintenance/').data), 2)
        res = self.client.get(
            f'/api/maintenance/?room_id={self.r1.id}&property_id={self.p1.id}'
            f'&status=PENDING&priority=HIGH&search=máy lạnh'
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual([m['code'] for m in res.data], ['BT0101'])

        hist_res = self.client.get(f'/api/maintenance/{self.m1.id}/history/')
        self.assertEqual(hist_res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(hist_res.data), 1)

    def test_filter_maintenance_history_by_room_and_property(self):
        """S2-FLT-042 | [Ngoài Sprint 1] Lọc GET /api/maintenance-history/ theo room_id và property_id | Data: 2 bản ghi lịch sử ở 2 phòng/nhà trọ | Expected: 200, trả đúng 1 bản ghi khớp"""
        self.assertEqual(len(self.client.get('/api/maintenance-history/').data), 2)
        res = self.client.get(f'/api/maintenance-history/?room_id={self.r1.id}&property_id={self.p1.id}')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual([h['action'] for h in res.data], ['Tạo yêu cầu 1'])

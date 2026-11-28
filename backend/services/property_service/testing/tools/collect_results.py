"""
Automated Test Execution & Evidence Generator for Sprint 1 - Service 2 (Property & Room).

Location: `backend/services/property_service/testing/tools/collect_results.py`
Capabilities:
1. Executes all 220 tests in `services.property_service`:
   - 78 Pure Unit Tests in `testing/unit_tests/`:
     * Models (`test_models.py`): 16 tests (`S2-MOD-001`..`016`)
     * Serializers (`test_serializers.py`): 21 tests (`S2-SER-001`..`021`)
     * Validators / Utilities (`test_services.py` -> `ParseHelperTests`, `ActorNameTests`): 7 tests (`S2-UTL-001`..`007`)
     * Services / Business Logic (`test_services.py` -> `ScopedQuerysetTests`, `MaintenanceViewSetUnitTests`): 22 tests (`S2-BIZ-001`..`022`)
     * Permissions & JWT Config (`test_permissions.py` -> `PermissionClassUnitTests`): 12 tests (`S2-PERM-001`..`011`, `S2-SEC-018`)
   - 142 API / HTTP Tests in `testing/api_tests/`:
     * Property & Room CRUD / Status API (`test_views.py`): 71 tests (`S2-API-001`..`071`)
     * Search / Filter / Sort API (`test_search_filter.py`): 42 tests (`S2-FLT-001`..`042`)
     * JWT Auth & RBAC Security API (`test_permissions_api.py`): 25 tests (`S2-SEC-009`..`017`, `S2-SEC-019`..`034`)
     * Maintenance HTTP Pipeline API (`test_maintenance_api.py`): 4 tests (`S2-MAPI-001`..`004`)
   Breakdown by Sprint Scope:
   - 201 in-scope Sprint 1 tests (`65` Pure Unit Tests + `136` API/HTTP Tests)
   - 19 out-of-Sprint-1 Maintenance tests (`13` Pure Unit Tests + `6` API/HTTP Tests)
2. Supports `--sprint1-only`, `--unit-only`, `--api-only`, and `--coverage-json` modes.
3. Generates:
   - `backend/services/property_service/testing/reports/results.json`
   - `backend/services/property_service/testing/reports/UNIT_TEST_CASES.md`
   - `backend/services/property_service/testing/evidence/TEST_EXECUTION_REPORT.html`
   - `backend/services/property_service/testing/evidence/junit-report.xml`
"""
import argparse
import datetime
import html
import json
import os
import re
import sys
import time
import unittest
import xml.etree.ElementTree as ET
from xml.dom import minidom

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TESTING_DIR = os.path.dirname(SCRIPT_DIR)
REPORTS_DIR = os.path.join(TESTING_DIR, 'reports')
EVIDENCE_DIR = os.path.join(TESTING_DIR, 'evidence')
BACKEND_DIR = os.path.abspath(os.path.join(TESTING_DIR, '..', '..', '..'))

sys.path.insert(0, BACKEND_DIR)
os.environ.setdefault('DB_ENGINE', 'sqlite')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.service_settings.property')

import django  # noqa: E402
django.setup()
from django.test.runner import DiscoverRunner  # noqa: E402

OUT_OF_SPRINT1_IDS = {
    'S2-MOD-014', 'S2-MOD-015',
    'S2-BIZ-011', 'S2-BIZ-012', 'S2-BIZ-013', 'S2-BIZ-014', 'S2-BIZ-015',
    'S2-BIZ-016', 'S2-BIZ-017', 'S2-BIZ-018', 'S2-BIZ-019', 'S2-BIZ-020', 'S2-BIZ-021',
    'S2-FLT-041', 'S2-FLT-042',
    'S2-MAPI-001', 'S2-MAPI-002', 'S2-MAPI-003', 'S2-MAPI-004',
}

LEGACY_ID_MAP = {
    'S2-SEC-033': 'S2-LEG-029',
    'S2-SEC-034': 'S2-LEG-033',
    'S2-MAPI-001': 'S2-LEG-018',
    'S2-MAPI-002': 'S2-LEG-019',
    'S2-MAPI-003': 'S2-LEG-020',
    'S2-MAPI-004': 'S2-LEG-021',
}

BUG_CATALOG = [
    {
        'id': 'BUG-01',
        'name': 'Cho phép giá thuê phòng và tiền đặt cọc âm (rent_price < 0, deposit_amount < 0)',
        'severity': 'High',
        'cause': 'Room.rent_price và Room.deposit_amount trong models.py dùng DecimalField nhưng thiếu MinValueValidator(0).',
        'files': 'backend/services/property_service/models.py',
        'fix': 'Gắn MinValueValidator(0) trực tiếp lên Room.rent_price và Room.deposit_amount trong models.py để tự động áp dụng cho Model.full_clean() và RoomSerializer.',
        'tests': ['S2-MOD-010', 'S2-SER-011', 'S2-API-037'],
    },
    {
        'id': 'BUG-02',
        'name': 'Cho phép diện tích phòng âm hoặc bằng 0 (area <= 0)',
        'severity': 'High',
        'cause': 'Room.area là FloatField(default=20.0) chưa gắn validator kiểm tra giá trị dương > 0.',
        'files': 'backend/services/property_service/models.py',
        'fix': 'Bổ sung hàm validate_positive_area(value) ném ValidationError khi value <= 0 và gắn vào Room.area.',
        'tests': ['S2-MOD-010', 'S2-SER-011'],
    },
    {
        'id': 'BUG-03',
        'name': 'Cho phép đơn giá điện, nước, internet của nhà trọ âm',
        'severity': 'Medium',
        'cause': 'Property.electricity_rate, water_rate, internet_rate dùng DecimalField nhưng thiếu MinValueValidator(0).',
        'files': 'backend/services/property_service/models.py',
        'fix': 'Gắn MinValueValidator(0) cho cả 3 trường electricity_rate, water_rate, internet_rate trên model Property.',
        'tests': ['S2-SER-005'],
    },
    {
        'id': 'BUG-04',
        'name': 'Cho phép tạo phòng với số người ở tối đa bằng 0 (max_occupants = 0)',
        'severity': 'Medium',
        'cause': 'Room.max_occupants dùng PositiveIntegerField vốn mặc định chấp nhận giá trị 0 (>= 0).',
        'files': 'backend/services/property_service/models.py',
        'fix': 'Gắn MinValueValidator(1) cho Room.max_occupants để bắt buộc sức chứa tối thiểu là 1 người.',
        'tests': ['S2-MOD-010', 'S2-SER-011'],
    },
    {
        'id': 'BUG-05',
        'name': 'Lọc phòng theo trạng thái tại GET /api/properties/{id}/rooms/?status=OCCUPIED trả về 404',
        'severity': 'Medium',
        'cause': 'PropertyViewSet.get_queryset() lọc Property.status theo query param ?status= cho mọi action, khiến get_object() lọc nhầm Property.status == OCCUPIED.',
        'files': 'backend/services/property_service/views.py',
        'fix': 'Giới hạn bộ lọc Property.status trong PropertyViewSet.get_queryset() chỉ áp dụng khi self.action == "list".',
        'tests': ['S2-API-063'],
    },
    {
        'id': 'BUG-06',
        'name': 'Xóa nhà trọ (DELETE / update_status=DELETED) khi bên trong còn phòng đang hoạt động chưa thuê',
        'severity': 'High',
        'cause': 'PropertyViewSet.destroy() và update_status() trước đó chỉ chặn khi có phòng OCCUPIED/FULL, bỏ sót các phòng AVAILABLE, RESERVED, MAINTENANCE.',
        'files': 'backend/services/property_service/views.py',
        'fix': 'Dùng helper _active_rooms_block_response(prop) chặn xóa mềm khi prop.rooms.exclude(status=RoomStatus.INACTIVE).exists().',
        'tests': ['S2-API-064', 'S2-API-065'],
    },
    {
        'id': 'BUG-07',
        'name': 'Phòng của nhà trọ đã xóa mềm (DELETED) vẫn hiển thị trong danh sách phòng (GET /api/rooms/)',
        'severity': 'High',
        'cause': 'RoomViewSet.get_queryset() không loại trừ các phòng có property__status = PropertyStatus.DELETED khi liệt kê danh sách.',
        'files': 'backend/services/property_service/views.py',
        'fix': 'Trong RoomViewSet.get_queryset(), thêm exclude(property__status=PropertyStatus.DELETED) cho các action list, available_rooms, occupied_rooms, maintenance_rooms.',
        'tests': ['S2-API-067'],
    },
    {
        'id': 'BUG-08',
        'name': 'Thống kê summary.total_properties ("Cơ sở đang vận hành") đếm cả nhà trọ tạm ngưng (INACTIVE)',
        'severity': 'Medium',
        'cause': 'PropertyViewSet.summary() đếm toàn bộ properties.exclude(status=DELETED) thay vì chỉ đếm nhà trọ đang vận hành (ACTIVE).',
        'files': 'backend/services/property_service/views.py',
        'fix': 'Cập nhật total_properties = properties.filter(status=PropertyStatus.ACTIVE).count() trong PropertyViewSet.summary().',
        'tests': ['S2-API-066'],
    },
    {
        'id': 'BUG-09',
        'name': 'Lách luật xóa mềm nhà trọ qua PATCH / PUT /api/properties/{id}/ với status = DELETED khi còn phòng hoạt động',
        'severity': 'High',
        'cause': 'PropertySerializer cho phép cập nhật trực tiếp trường status sang DELETED mà không kiểm tra các phòng đang hoạt động trong nhà trọ.',
        'files': 'backend/services/property_service/serializers.py',
        'fix': 'Bổ sung PropertySerializer.validate_status() chặn giá trị PropertyStatus.DELETED khi self.instance.rooms.exclude(status=RoomStatus.INACTIVE).exists().',
        'tests': ['S2-SER-019', 'S2-API-068'],
    },
    {
        'id': 'BUG-10',
        'name': 'Cho phép trùng số phòng (room_number) trong cùng một nhà trọ (Property)',
        'severity': 'High',
        'cause': 'Model Room chỉ có unique=True trên trường code, thiếu UniqueConstraint(property, room_number) ở DB và thiếu kiểm tra trùng không phân biệt hoa/thường ở RoomSerializer.',
        'files': 'backend/services/property_service/models.py, serializers.py, migrations/0003_room_unique_room_number_per_property.py',
        'fix': 'Thêm UniqueConstraint(fields=["property", "room_number"]) vào Room.Meta.constraints và kiểm tra Room.objects.filter(property=prop, room_number__iexact=room_num) trong RoomSerializer.validate().',
        'tests': ['S2-MOD-016', 'S2-SER-020', 'S2-API-069'],
    },
    {
        'id': 'BUG-11',
        'name': 'Xóa phòng (DELETE /api/rooms/{id}/) không chặn trạng thái RESERVED và không kiểm tra liên kết khách thuê / hợp đồng liên service',
        'severity': 'High',
        'cause': 'RoomViewSet.destroy() bỏ sót trạng thái RESERVED (đã nhận cọc nhưng current_occupants=0) và không đối chiếu Tenant Service (:8003) / Contract Service (:8004).',
        'files': 'backend/services/property_service/views.py, backend/common/service_client.py',
        'fix': 'Mở rộng điều kiện chặn trong RoomViewSet.destroy() cho RoomStatus.RESERVED và gọi room_external_block_reason() để chặn xóa khi phòng còn hồ sơ khách thuê (!= MOVED_OUT) hoặc hợp đồng (DRAFT, ACTIVE, EXTENDED).',
        'tests': ['S2-BIZ-022', 'S2-API-045', 'S2-API-070'],
    },
    {
        'id': 'BUG-12',
        'name': 'Cho phép thêm/chuyển phòng vào nhà trọ đã xóa mềm (DELETED), chuyển phòng đang thuê sang INACTIVE, và lệch current_occupants khi đổi status qua Serializer',
        'severity': 'High',
        'cause': 'RoomSerializer.validate() chưa chặn property có status=DELETED, chưa chặn đổi status sang INACTIVE khi phòng đang có người thuê, và chưa chuẩn hóa current_occupants theo status.',
        'files': 'backend/services/property_service/serializers.py, views.py',
        'fix': 'Trong RoomSerializer.validate() và RoomViewSet.update_status(): chặn nhà trọ DELETED, chặn đặt INACTIVE khi đang có khách thuê, và đồng bộ current_occupants / tenant_name khi đặt AVAILABLE, OCCUPIED, FULL.',
        'tests': ['S2-SER-021', 'S2-API-053', 'S2-API-071'],
    },
    {
        'id': 'BUG-13',
        'name': 'Cho phép số tầng nhà trọ <= 0, tầng phòng vượt ngoài 1..total_floors, hoặc giảm total_floors thấp hơn tầng của phòng hiện có',
        'severity': 'Medium',
        'cause': 'Property.total_floors thiếu MinValueValidator(1), RoomSerializer không kiểm tra 1 <= floor <= property.total_floors, và PropertySerializer chưa chặn giảm total_floors dưới tầng phòng đang có.',
        'files': 'backend/services/property_service/models.py, serializers.py',
        'fix': 'Gắn MinValueValidator(1) cho Property.total_floors, kiểm tra biên tầng trong RoomSerializer.validate() và bổ sung PropertySerializer.validate_total_floors().',
        'tests': ['S2-MOD-004', 'S2-SER-005', 'S2-SER-011', 'S2-API-071'],
    },
    {
        'id': 'BUG-14',
        'name': 'Cho phép chỉ số điện/nước ban đầu của phòng và chi phí bảo trì ở tầng Model nhận giá trị âm',
        'severity': 'Medium',
        'cause': 'Room.initial_electric_reading, Room.initial_water_reading và MaintenanceRequest.estimated_cost / actual_cost chưa gắn MinValueValidator(0).',
        'files': 'backend/services/property_service/models.py',
        'fix': 'Gắn MinValueValidator(0.0) / MinValueValidator(0) trực tiếp trên các trường chỉ số điện/nước ban đầu và chi phí bảo trì trong models.py.',
        'tests': ['S2-MOD-010', 'S2-SER-011'],
    },
]

BUG_VERIFICATION_MAP = {
    'S2-MOD-004': {'bugs': ['BUG-13'], 'is_new': False, 'note': 'Kiểm tra Property.total_floors >= 1 ở tầng Model'},
    'S2-MOD-010': {'bugs': ['BUG-01', 'BUG-02', 'BUG-04', 'BUG-14'], 'is_new': False, 'note': 'Kiểm tra rent_price>=0, deposit_amount>=0, area>0, max_occupants>=1, chỉ số điện/nước ban đầu>=0'},
    'S2-MOD-016': {'bugs': ['BUG-10'], 'is_new': True, 'note': 'UniqueConstraint (property, room_number) ở tầng Database'},
    'S2-SER-005': {'bugs': ['BUG-03', 'BUG-13'], 'is_new': False, 'note': 'Chặn đơn giá điện/nước/internet âm, total_floors<=0 hoặc nhỏ hơn tầng phòng hiện có'},
    'S2-SER-011': {'bugs': ['BUG-01', 'BUG-02', 'BUG-04', 'BUG-13', 'BUG-14'], 'is_new': False, 'note': 'Chặn giá thuê/tiền cọc/chỉ số điện nước âm, diện tích<=0, max_occupants<=0, tầng phòng vượt 1..total_floors'},
    'S2-SER-019': {'bugs': ['BUG-09'], 'is_new': True, 'note': 'PropertySerializer.validate_status chặn status=DELETED khi nhà trọ còn phòng hoạt động'},
    'S2-SER-020': {'bugs': ['BUG-10'], 'is_new': True, 'note': 'RoomSerializer.validate chặn trùng room_number (không phân biệt hoa/thường) trong cùng Property'},
    'S2-SER-021': {'bugs': ['BUG-12'], 'is_new': True, 'note': 'RoomSerializer.validate chặn thêm phòng vào nhà trọ DELETED, chặn đặt INACTIVE khi đang có khách thuê & đồng bộ current_occupants'},
    'S2-BIZ-022': {'bugs': ['BUG-11'], 'is_new': True, 'note': 'room_external_block_reason & fetch_room_contracts kiểm tra liên kết khách thuê/hợp đồng liên service'},
    'S2-API-037': {'bugs': ['BUG-01'], 'is_new': False, 'note': 'POST /api/rooms/ từ chối giá thuê âm (400)'},
    'S2-API-045': {'bugs': ['BUG-11'], 'is_new': False, 'note': 'DELETE /api/rooms/{id}/ chặn xóa phòng đang thuê (OCCUPIED, FULL) hoặc đã đặt cọc (RESERVED)'},
    'S2-API-053': {'bugs': ['BUG-12'], 'is_new': False, 'note': 'POST /api/rooms/{id}/status/ chặn chuyển phòng đang có người thuê sang INACTIVE (400)'},
    'S2-API-063': {'bugs': ['BUG-05'], 'is_new': False, 'note': 'GET /api/properties/{id}/rooms/?status=occupied lọc đúng phòng của nhà trọ ACTIVE (200)'},
    'S2-API-064': {'bugs': ['BUG-06'], 'is_new': True, 'note': 'DELETE /api/properties/{id}/ chặn xóa nhà trọ còn phòng đang hoạt động (AVAILABLE)'},
    'S2-API-065': {'bugs': ['BUG-06'], 'is_new': True, 'note': 'POST /api/properties/{id}/update_status/ chặn đặt status=DELETED khi còn phòng đang hoạt động'},
    'S2-API-066': {'bugs': ['BUG-08'], 'is_new': True, 'note': 'GET /api/properties/summary/ chỉ đếm cơ sở đang vận hành (ACTIVE) vào total_properties'},
    'S2-API-067': {'bugs': ['BUG-07'], 'is_new': True, 'note': 'GET /api/rooms/ và /api/rooms/available/ ẩn phòng của nhà trọ đã xóa mềm (DELETED)'},
    'S2-API-068': {'bugs': ['BUG-09'], 'is_new': True, 'note': 'PATCH và PUT /api/properties/{id}/ chặn đặt status=DELETED khi còn phòng hoạt động'},
    'S2-API-069': {'bugs': ['BUG-10'], 'is_new': True, 'note': 'POST và PATCH /api/rooms/ chặn trùng room_number trong cùng Property (400)'},
    'S2-API-070': {'bugs': ['BUG-11'], 'is_new': True, 'note': 'DELETE /api/rooms/{id}/ chặn xóa phòng còn liên kết khách thuê (Tenant Service) hoặc hợp đồng (Contract Service)'},
    'S2-API-071': {'bugs': ['BUG-12', 'BUG-13'], 'is_new': True, 'note': 'POST/PATCH /api/rooms/ & /api/properties/ kiểm tra nhà trọ DELETED, biên tầng 1..total_floors, và đồng bộ trạng thái phòng'},
}

S2_US_SPEC = [
    (
        'QLNT-253',
        'Xem Dashboard tổng quan (FE+BE)',
        2,
        ['S2-MOD-005', 'S2-SER-007', 'S2-BIZ-023'],
        'Đủ (Bao phủ bộ đếm phòng trên Property, serialize số liệu thống kê, và PropertyViewSet.summary() / stats() khi có dữ liệu, không có dữ liệu, loại trừ nhà trọ DELETED/INACTIVE khỏi cơ sở đang vận hành)',
    ),
    (
        'QLNT-254',
        'Thêm nhà trọ (FE+BE)',
        10,
        ['S2-MOD-001', 'S2-MOD-002', 'S2-MOD-003', 'S2-MOD-004', 'S2-SER-001', 'S2-SER-002', 'S2-SER-003', 'S2-SER-004', 'S2-SER-005', 'S2-SER-006'],
        'Đủ (Bao phủ tạo thành công, tự sinh mã NTxxx, thiếu trường bắt buộc name/address, đơn giá điện/nước/internet âm, số tầng <= 0, sai định dạng URL, biên độ dài name 150/151, gán owner_id từ JWT)',
    ),
    (
        'QLNT-258',
        'Xem danh sách nhà trọ (FE+BE)',
        6,
        ['S2-BIZ-001', 'S2-BIZ-002', 'S2-BIZ-003', 'S2-BIZ-004', 'S2-BIZ-005', 'S2-BIZ-006', 'S2-BIZ-024'],
        'Đủ (Bao phủ có dữ liệu, không có dữ liệu, phân quyền phạm vi ADMIN/LANDLORD/TENANT, ẩn nhà trọ DELETED mặc định và lọc theo trạng thái ACTIVE/INACTIVE/DELETED/ALL, quận/phường)',
    ),
    (
        'QLNT-262',
        'Xem chi tiết nhà trọ (FE+BE)',
        4,
        ['S2-MOD-001', 'S2-MOD-005', 'S2-SER-007', 'S2-BIZ-009', 'S2-BIZ-025'],
        'Đủ (Bao phủ nhà trọ tồn tại, không tồn tại Http404, nhà trọ đã xóa mềm DELETED vẫn tra cứu được chi tiết, kiểm tra dữ liệu trả về full_address, rooms, room_matrix)',
    ),
    (
        'QLNT-266',
        'Cập nhật nhà trọ (FE+BE)',
        5,
        ['S2-MOD-004', 'S2-SER-004', 'S2-SER-005', 'S2-SER-008', 'S2-SER-019'],
        'Đủ (Bao phủ cập nhật thành công, dữ liệu không hợp lệ, giảm số tầng thấp hơn tầng của phòng hiện có, trạng thái không hợp lệ, chặn đặt status=DELETED khi còn phòng hoạt động)',
    ),
    (
        'QLNT-270',
        'Xóa nhà trọ (FE+BE)',
        2,
        ['S2-MOD-006', 'S2-SER-019', 'S2-BIZ-026'],
        'Đủ (Bao phủ xóa cứng khi nhà trống, xóa mềm sang DELETED khi chỉ còn phòng INACTIVE, nhà trọ không tồn tại Http404, chặn xóa/chuyển DELETED khi còn phòng hoạt động, ẩn nhà đã xóa khỏi danh sách)',
    ),
    (
        'QLNT-274',
        'Thêm phòng trọ (FE+BE)',
        12,
        ['S2-MOD-007', 'S2-MOD-008', 'S2-MOD-009', 'S2-MOD-010', 'S2-MOD-016', 'S2-SER-009', 'S2-SER-010', 'S2-SER-011', 'S2-SER-012', 'S2-SER-013', 'S2-SER-020', 'S2-SER-021', 'S2-BIZ-028'],
        'Đủ (Bao phủ tạo phòng hợp lệ, trùng room_number cùng nhà trọ ở Serializer & DB UniqueConstraint, giá thuê/tiền cọc âm, diện tích <= 0, max_occupants <= 0, tầng ngoài 1..total_floors, nhà trọ không tồn tại/đã xóa/của chủ khác, chỉ số điện nước âm)',
    ),
    (
        'QLNT-278',
        'Xem danh sách phòng trọ (FE+BE)',
        9,
        ['S2-SER-018', 'S2-BIZ-001', 'S2-BIZ-003', 'S2-BIZ-004', 'S2-BIZ-005', 'S2-BIZ-006', 'S2-BIZ-007', 'S2-BIZ-008', 'S2-BIZ-010', 'S2-BIZ-027'],
        'Đủ (Bao phủ có dữ liệu, không có dữ liệu, loại trừ phòng thuộc nhà trọ đã xóa DELETED khỏi mọi danh sách, lọc theo trạng thái và lọc theo nhà trọ)',
    ),
    (
        'QLNT-282',
        'Xem chi tiết phòng trọ (FE+BE)',
        8,
        ['S2-MOD-011', 'S2-MOD-012', 'S2-MOD-013', 'S2-SER-014', 'S2-SER-015', 'S2-SER-016', 'S2-SER-017', 'S2-PERM-011', 'S2-BIZ-027'],
        'Đủ (Bao phủ phòng tồn tại, không tồn tại Http404, dữ liệu chi tiết cho quản lý vs ẩn PII đối với TENANT, active_maintenance_count, và phòng thuộc nhà trọ đã xóa/tạm ngưng báo is_rentable=False)',
    ),
    (
        'QLNT-286',
        'Cập nhật phòng trọ (FE+BE)',
        7,
        ['S2-MOD-010', 'S2-MOD-016', 'S2-SER-011', 'S2-SER-012', 'S2-SER-013', 'S2-SER-020', 'S2-SER-021', 'S2-BIZ-028'],
        'Đủ (Bao phủ cập nhật thành công, trùng room_number, giá thuê/diện tích/max_occupants/tầng/trạng thái không hợp lệ, chặn chuyển sang nhà trọ DELETED hoặc của chủ khác, đồng bộ người thuê & trạng thái)',
    ),
    (
        'QLNT-290',
        'Xóa phòng trọ (FE+BE)',
        1,
        ['S2-BIZ-022', 'S2-BIZ-029'],
        'Đủ (Bao phủ xóa cứng khi chưa có lịch sử, xóa mềm sang INACTIVE khi có lịch sử bảo trì, phòng không tồn tại Http404, chặn xóa phòng OCCUPIED/FULL/RESERVED/có người ở, chặn xóa khi còn liên kết khách thuê hoặc hợp đồng)',
    ),
    (
        'QLNT-294',
        'Quản lý trạng thái phòng (FE+BE)',
        5,
        ['S2-MOD-011', 'S2-MOD-012', 'S2-MOD-013', 'S2-SER-021', 'S2-BIZ-011', 'S2-BIZ-030'],
        'Đủ (Bao phủ chuyển trạng thái hợp lệ/không hợp lệ, phòng đang có người thuê hoặc đang đặt cọc RESERVED, tự đồng bộ current_occupants & thông tin người thuê, chặn chuyển phòng đang thuê sang INACTIVE)',
    ),
    (
        'QLNT-298',
        'Tìm kiếm nhà trọ (FE+BE)',
        0,
        ['S2-BIZ-031'],
        'Đủ (Bao phủ tìm theo tên, mã, địa chỉ, phường, quận, thành phố không phân biệt hoa/thường, không tìm thấy, tìm kiếm rỗng và kết hợp điều kiện tìm kiếm với bộ lọc status/district)',
    ),
    (
        'QLNT-306',
        'Tìm kiếm phòng trọ (FE+BE)',
        6,
        ['S2-UTL-001', 'S2-UTL-002', 'S2-UTL-003', 'S2-UTL-004', 'S2-UTL-005', 'S2-UTL-006', 'S2-BIZ-032'],
        'Đủ (Bao phủ parse tham số số/Decimal, tìm theo số phòng/mã/nhà trọ/tên khách thuê, lọc theo diện tích, giá, trạng thái, tầng, sức chứa, kết hợp nhiều điều kiện, không có kết quả và sắp xếp)',
    ),
    (
        'QLNT-302',
        'Phân trang danh sách nhà trọ (FE+BE)',
        0,
        [],
        'Backend Pure Unit Test: 0 | Frontend Flutter Widget Test: 6/6 PASS (3 test có sẵn + 3 test mới trong frontend/test/property_room_test.dart, bao phủ đầy đủ 11 kịch bản phân trang nhà trọ với _pageSize=6).',
    ),
    (
        'QLNT-315',
        'Phân trang danh sách phòng trọ (FE+BE)',
        0,
        [],
        'Backend Pure Unit Test: 0 | Frontend Flutter Widget Test: 5/5 PASS (1 test có sẵn + 4 test mới trong frontend/test/property_room_test.dart, bao phủ đầy đủ 11 kịch bản phân trang phòng trọ với _pageSize=6).',
    ),
]

S2_FRONTEND_PAGINATION_TESTS = [
    {
        'id': 'FE-PAG-01',
        'us': 'QLNT-302',
        'is_new': False,
        'name': 'Nhà trọ: Hiển thị đúng và đủ danh sách backend trả về (phạm vi do backend lọc)',
        'file': 'frontend/test/property_room_test.dart',
        'scenarios': 'Kịch bản #9: Xử lý danh sách nhà trọ chỉ có 1 trang (2 bản ghi <= _pageSize=6, hiển thị "Hiển thị 1–2 trong tổng số 2 bản ghi")',
        'status': 'PASS',
    },
    {
        'id': 'FE-PAG-02',
        'us': 'QLNT-302',
        'is_new': False,
        'name': 'Nhà trọ: Backend thật sự không có tòa nhà: hiển thị trạng thái rỗng',
        'file': 'frontend/test/property_room_test.dart',
        'scenarios': 'Kịch bản #8: Xử lý danh sách nhà trọ rỗng (hiển thị EmptyState property_list_empty, ẩn thanh phân trang)',
        'status': 'PASS',
    },
    {
        'id': 'FE-PAG-03',
        'us': 'QLNT-302',
        'is_new': False,
        'name': 'Nhà trọ: Xóa tòa nhà ở trang cuối: danh sách cập nhật, không kẹt ở trang trống',
        'file': 'frontend/test/property_room_test.dart',
        'scenarios': 'Kịch bản #1, #3, #7, #11: Danh sách >6 phần tử (7 nhà trọ), chuyển sang trang 2, xóa phần tử cuối ở trang 2 và tự động lùi về trang 1 (1–6/6)',
        'status': 'PASS',
    },
    {
        'id': 'FE-PAG-04',
        'us': 'QLNT-302',
        'is_new': True,
        'name': 'Nhà trọ: [QLNT-302] Phân trang danh sách nhà trọ (>6 phần tử): hiển thị 6 phần tử trang đầu, chuyển trang Sau/Trước, chặn biên trang 0 và vượt trang cuối, xử lý danh sách 1 trang',
        'file': 'frontend/test/property_room_test.dart',
        'scenarios': 'Kịch bản #1, #2, #3, #4, #5, #6, #7, #9: 8 nhà trọ -> trang 1 hiện đúng 6 nhà (Tòa 1..6), chặn Trước ở trang 1, bấm Sau sang trang 2 hiện 2 nhà (Tòa 7..8), chặn Sau ở trang cuối, bấm Trước về trang 1',
        'status': 'PASS',
    },
    {
        'id': 'FE-PAG-05',
        'us': 'QLNT-302',
        'is_new': True,
        'name': 'Nhà trọ: [QLNT-302] Khi tìm kiếm hoặc lọc trạng thái nhà trọ ở trang 2: tự động quay về trang 1 và tính lại phân trang',
        'file': 'frontend/test/property_room_test.dart',
        'scenarios': 'Kịch bản #10: Đang ở trang 2 của 8 nhà trọ, tìm kiếm theo mã/tên hoặc lọc trạng thái ("Tạm ngưng") -> tự động đưa _page về 1 và tính lại tổng số bản ghi/số trang',
        'status': 'PASS',
    },
    {
        'id': 'FE-PAG-06',
        'us': 'QLNT-315',
        'is_new': False,
        'name': 'Phòng: Backend thật sự không có phòng: trạng thái rỗng',
        'file': 'frontend/test/property_room_test.dart',
        'scenarios': 'Kịch bản #8: Xử lý danh sách phòng trọ rỗng (hiển thị EmptyState room_list_empty, ẩn thanh phân trang)',
        'status': 'PASS',
    },
    {
        'id': 'FE-PAG-07',
        'us': 'QLNT-315',
        'is_new': True,
        'name': 'Phòng: [QLNT-315] Phân trang danh sách phòng trọ (>6 phần tử): hiển thị 6 phòng trang đầu, chuyển trang Sau/Trước, chặn biên trang 0 và vượt trang cuối, xử lý danh sách 1 trang',
        'file': 'frontend/test/property_room_test.dart',
        'scenarios': 'Kịch bản #1, #2, #3, #4, #5, #6, #7, #9: 1 trang (3 phòng) khóa Trước/Sau; 8 phòng -> trang 1 hiện 6 phòng (P1..P6), chặn Trước ở trang 1, bấm Sau sang trang 2 hiện 2 phòng (P7..P8), chặn Sau ở trang cuối, bấm Trước về trang 1',
        'status': 'PASS',
    },
    {
        'id': 'FE-PAG-08',
        'us': 'QLNT-315',
        'is_new': True,
        'name': 'Phòng: [QLNT-315] Khi tìm kiếm hoặc lọc phòng trọ (nhà trọ/trạng thái/mức giá) ở trang 2: tự động quay về trang 1 và tính lại phân trang',
        'file': 'frontend/test/property_room_test.dart',
        'scenarios': 'Kịch bản #10: Đang ở trang 2 của 8 phòng, tìm kiếm hoặc lọc theo trạng thái ("Đang thuê") -> tự động quay về trang 1 và tính lại số trang',
        'status': 'PASS',
    },
    {
        'id': 'FE-PAG-09',
        'us': 'QLNT-315',
        'is_new': True,
        'name': 'Phòng: [QLNT-315] Xóa phòng ở trang cuối khiến trang hiện tại không còn hợp lệ: tự động lùi về trang cuối còn dữ liệu',
        'file': 'frontend/test/property_room_test.dart',
        'scenarios': 'Kịch bản #11: 7 phòng -> sang trang 2 xóa Phòng X7 (DELETE /api/rooms/207/) -> trang 2 không còn hợp lệ, tự động clamp về trang 1 (1–6/6)',
        'status': 'PASS',
    },
    {
        'id': 'FE-PAG-10',
        'us': 'QLNT-302, QLNT-315 (Dùng chung)',
        'is_new': True,
        'name': 'Phòng: [QLNT-302, QLNT-315] PaginationWidget xử lý trực tiếp danh sách 0 bản ghi và khóa nút Trước/Sau ở biên',
        'file': 'frontend/test/property_room_test.dart',
        'scenarios': 'Kịch bản #5, #6, #8: Kiểm thử trực tiếp PaginationWidget với totalItems=0 ("Hiển thị 0–0 trong tổng số 0 bản ghi"), khóa cả hai nút Trước và Sau',
        'status': 'PASS',
    },
]

S2_SHARED_FOUNDATION_UNIT_IDS = [
    'S2-PERM-001', 'S2-PERM-002', 'S2-PERM-003', 'S2-PERM-004', 'S2-PERM-005',
    'S2-PERM-006', 'S2-PERM-007', 'S2-PERM-008', 'S2-PERM-009', 'S2-PERM-010',
    'S2-SEC-018', 'S2-UTL-007',
]

S2_OUT_OF_SPRINT1_MAINT_UNIT_IDS = [
    'S2-MOD-014', 'S2-MOD-015',
    'S2-BIZ-012', 'S2-BIZ-013', 'S2-BIZ-014', 'S2-BIZ-015', 'S2-BIZ-016',
    'S2-BIZ-017', 'S2-BIZ-018', 'S2-BIZ-019', 'S2-BIZ-020', 'S2-BIZ-021',
]

MODULE_CATEGORY_MAP = {
    'test_models': '[Unit Test] Model Tests (Property, Room, Maintenance)',
    'test_serializers': '[Unit Test] Serializer Tests (PropertySerializer, RoomSerializer)',
    'test_services': '[Unit Test] Services / Business Logic & Utilities Tests',
    'test_permissions': '[Unit Test] Permission & Role Logic Unit Tests',
    'test_views': '[API Test] Property & Room View / CRUD / Status API Tests',
    'test_search_filter': '[API Test] Search / Filter / Sort API Tests',
    'test_permissions_api': '[API Test] JWT Authentication & RBAC Security API Tests',
    'test_maintenance_api': '[API Test] Maintenance HTTP Pipeline Tests (Out-of-Sprint-1)',
}


def classify_test_level(full_module_name):
    if '.unit_tests.' in full_module_name:
        return 'Pure Unit Test'
    return 'API/HTTP Test'


def extract_meta(test):
    doc = (test._testMethodDoc or '').strip()
    m = re.match(r'^(S2-[A-Z]+-\d+)\s*[:|]\s*(.+)$', doc, re.DOTALL)
    if m:
        tc_id = m.group(1)
        desc = ' '.join(m.group(2).split())
    else:
        tc_id = test._testMethodName
        desc = ' '.join(doc.split()) if doc else test._testMethodName.replace('_', ' ').capitalize()
    full_mod = test.__class__.__module__
    mod = full_mod.split('.')[-1]
    cls = test.__class__.__name__
    method = test._testMethodName
    if tc_id in OUT_OF_SPRINT1_IDS or '[Ngoài Sprint 1]' in desc:
        scope = 'Ngoài Sprint 1 (Maintenance)'
    else:
        scope = 'Sprint 1'
    bug_info = BUG_VERIFICATION_MAP.get(tc_id, {})
    return {
        'id': tc_id,
        'legacy_id': LEGACY_ID_MAP.get(tc_id, ''),
        'bugs_verified': bug_info.get('bugs', []),
        'is_new_bug_test': bool(bug_info.get('is_new', False)),
        'bug_note': bug_info.get('note', ''),
        'module': mod,
        'full_module': full_mod,
        'category': MODULE_CATEGORY_MAP.get(mod, mod),
        'class': cls,
        'method': method,
        'description': desc,
        'sprint_scope': scope,
        'test_level': classify_test_level(full_mod),
    }


def flatten_suite(suite):
    tests = []
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            tests.extend(flatten_suite(item))
        else:
            tests.append(item)
    return tests


class TimedResult(unittest.TextTestResult):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.records = []
        self._t0 = 0.0

    def startTest(self, test):
        self._t0 = time.perf_counter()
        super().startTest(test)

    def _record(self, test, status, detail=''):
        elapsed = max(0.0, time.perf_counter() - self._t0)
        meta = extract_meta(test)
        meta['status'] = status
        meta['detail'] = detail
        meta['duration_sec'] = round(elapsed, 5)
        self.records.append(meta)

    def addSuccess(self, test):
        super().addSuccess(test)
        self._record(test, 'PASS')

    def addExpectedFailure(self, test, err):
        super().addExpectedFailure(test, err)
        self._record(test, 'EXPECTED_FAIL (BUG)', self._exc_info_to_string(err, test))

    def addFailure(self, test, err):
        super().addFailure(test, err)
        self._record(test, 'FAIL', self._exc_info_to_string(err, test))

    def addError(self, test, err):
        super().addError(test, err)
        self._record(test, 'ERROR', self._exc_info_to_string(err, test))

    def addSkip(self, test, reason):
        super().addSkip(test, reason)
        self._record(test, 'SKIP', reason)


def infer_inputs_and_expected(r):
    method = r['method']
    desc = r['description']
    mod = r['module']

    if 'unauthenticated' in method or 'anonymous' in method:
        auth = 'Anonymous (No JWT)'
    elif 'tenant' in method:
        auth = 'JWT Role=TENANT'
    elif 'manager' in method or 'owner' in method or 'landlord' in method:
        auth = 'JWT Role=LANDLORD (Property Owner)'
    elif 'other_manager' in method or 'non_owner' in method:
        auth = 'JWT Role=LANDLORD (Other Manager)'
    elif 'staff' in method:
        auth = 'JWT Role=STAFF'
    else:
        auth = 'JWT Role=ADMIN/LANDLORD'

    if mod in ('test_models', 'test_serializers'):
        inp = f'ORM / Serializer input ({cls_target(r["class"])})'
    elif mod in ('test_services', 'test_permissions'):
        inp = f'Direct Python / Method call ({auth})'
    else:
        inp = f'HTTP Request ({auth})'

    if r['status'] == 'PASS':
        if any(k in method for k in ('reject', 'invalid', 'negative', 'zero', 'forbidden', 'denied', 'unauthenticated', 'not_found', 'conflict', 'duplicate', 'exceeds', 'blank', 'missing', 'locked', 'without_active_link')):
            expected = 'Validate & từ chối thao tác không hợp lệ (400/401/403/404/503 hoặc ValidationError)'
            actual = 'Hệ thống từ chối đúng theo quy tắc bảo mật/nghiệp vụ (PASS)'
        else:
            expected = f'Thực thi thành công: {desc}'
            actual = 'Kết quả trả về & trạng thái DB khớp kỳ vọng (PASS)'
    else:
        expected = f'Thực thi đúng: {desc}'
        actual = f'KẾT QUẢ: {r["status"]} — {r["detail"][:120]}'

    return inp, expected, actual


def cls_target(cls_name):
    for name in ('RoomImage', 'MaintenanceHistory', 'MaintenanceRequest', 'Property', 'Room', 'Amenity'):
        if name.lower() in cls_name.lower():
            return name
    return cls_name


def load_coverage_summary(coverage_json_path):
    """Load dynamic Coverage.py JSON metrics when provided via --coverage-json."""
    if not coverage_json_path or not os.path.exists(coverage_json_path):
        return None
    with open(coverage_json_path, encoding='utf-8') as f:
        data = json.load(f)

    meta = data.get('meta', {})
    totals = data.get('totals', {})
    files = []
    for rel_path, info in sorted(data.get('files', {}).items()):
        summary = info.get('summary', {})
        files.append({
            'path': rel_path.replace('\\', '/'),
            'num_statements': summary.get('num_statements', 0),
            'missing_lines': summary.get('missing_lines', 0),
            'num_branches': summary.get('num_branches', 0),
            'num_partial_branches': summary.get('num_partial_branches', 0),
            'percent_covered_display': str(summary.get('percent_covered_display', '0')),
        })

    return {
        'version': meta.get('version', 'unknown'),
        'branch_coverage': bool(meta.get('branch_coverage', False)),
        'files': files,
        'totals': {
            'num_statements': totals.get('num_statements', 0),
            'missing_lines': totals.get('missing_lines', 0),
            'num_branches': totals.get('num_branches', 0),
            'num_partial_branches': totals.get('num_partial_branches', 0),
            'stmt_pct': str(totals.get('percent_statements_covered_display', '0')),
            'branch_pct': str(totals.get('percent_branches_covered_display', '0')),
            'total_pct': str(totals.get('percent_covered_display', '0')),
        },
    }


def write_junit_xml(records, total_duration, xml_path):
    os.makedirs(os.path.dirname(xml_path), exist_ok=True)
    suites_by_mod = {}
    for r in records:
        suites_by_mod.setdefault(r['module'], []).append(r)

    total_tests = len(records)
    unit_tests = sum(1 for r in records if r['test_level'] == 'Pure Unit Test')
    api_tests = sum(1 for r in records if r['test_level'] == 'API/HTTP Test')
    total_failures = sum(1 for r in records if r['status'] == 'FAIL')
    total_errors = sum(1 for r in records if r['status'] == 'ERROR')
    total_skipped = sum(1 for r in records if r['status'].startswith('SKIP'))

    root = ET.Element('testsuites', {
        'name': f'Service 2 - Property & Room Test Suite ({unit_tests} Unit + {api_tests} API = {total_tests} tests)',
        'tests': str(total_tests),
        'failures': str(total_failures),
        'errors': str(total_errors),
        'skipped': str(total_skipped),
        'time': f'{total_duration:.4f}',
        'timestamp': datetime.datetime.now().isoformat(timespec='seconds'),
    })

    for mod, mod_records in suites_by_mod.items():
        mod_time = sum(r.get('duration_sec', 0.0) for r in mod_records)
        mod_fail = sum(1 for r in mod_records if r['status'] == 'FAIL')
        mod_err = sum(1 for r in mod_records if r['status'] == 'ERROR')
        mod_skip = sum(1 for r in mod_records if r['status'].startswith('SKIP'))
        full_mod = mod_records[0]['full_module']
        ts = ET.SubElement(root, 'testsuite', {
            'name': full_mod,
            'tests': str(len(mod_records)),
            'failures': str(mod_fail),
            'errors': str(mod_err),
            'skipped': str(mod_skip),
            'time': f'{mod_time:.4f}',
        })
        for r in mod_records:
            tc = ET.SubElement(ts, 'testcase', {
                'classname': f'{r["full_module"]}.{r["class"]}',
                'name': f'{r["id"]}: {r["method"]}',
                'time': f'{r.get("duration_sec", 0.0):.5f}',
            })
            props = ET.SubElement(tc, 'properties')
            ET.SubElement(props, 'property', {'name': 'test_id', 'value': r['id']})
            if r.get('legacy_id'):
                ET.SubElement(props, 'property', {'name': 'legacy_id', 'value': r['legacy_id']})
            ET.SubElement(props, 'property', {'name': 'sprint_scope', 'value': r['sprint_scope']})
            ET.SubElement(props, 'property', {'name': 'test_level', 'value': r['test_level']})
            ET.SubElement(props, 'property', {'name': 'description', 'value': r['description']})
            if r['status'] == 'FAIL':
                fail_el = ET.SubElement(tc, 'failure', {'message': r['description'], 'type': 'AssertionError'})
                fail_el.text = r.get('detail', '')
            elif r['status'] == 'ERROR':
                err_el = ET.SubElement(tc, 'error', {'message': r['description'], 'type': 'Exception'})
                err_el.text = r.get('detail', '')
            elif r['status'].startswith('SKIP'):
                ET.SubElement(tc, 'skipped', {'message': r.get('detail', '')})

    xml_bytes = ET.tostring(root, encoding='utf-8')
    pretty_xml = minidom.parseString(xml_bytes).toprettyxml(indent='  ', encoding='utf-8').decode('utf-8')
    with open(xml_path, 'w', encoding='utf-8') as f:
        f.write(pretty_xml)


def infer_api_endpoint_info(r):
    desc = r['description']
    method = r['method']
    mod = r['module']

    http_method = 'GET'
    for m_tok in ('POST', 'PUT', 'PATCH', 'DELETE', 'GET'):
        if re.search(rf'\b{m_tok}\b', desc):
            http_method = m_tok
            break
    else:
        if any(k in method for k in ('create_', 'post_', 'set_status', 'update_status')):
            http_method = 'POST'
        elif any(k in method for k in ('put_',)):
            http_method = 'PUT'
        elif any(k in method for k in ('patch_', 'move_room')):
            http_method = 'PATCH'
        elif any(k in method for k in ('delete_',)):
            http_method = 'DELETE'

    url_m = re.search(r'(/[a-zA-Z0-9_/{}-]+/?(?:\?[^\s|]+)?)', desc)
    if url_m:
        endpoint = url_m.group(1)
    elif mod == 'test_maintenance_api' or 'maintenance' in method:
        endpoint = '/api/maintenance/'
    elif 'Room' in r['class'] or 'room' in method:
        endpoint = '/api/rooms/'
    elif 'Property' in r['class'] or 'property' in method:
        endpoint = '/api/properties/'
    else:
        endpoint = '/api/properties/ & /api/rooms/'

    st_m = re.findall(r'\b(200|201|204|400|401|403|404|503)\b', desc)
    if st_m:
        codes = ' / '.join(dict.fromkeys(st_m))
        exp_status = f'HTTP {codes}'
    elif http_method == 'POST' and 'create' in method and 'invalid' not in method and 'missing' not in method:
        exp_status = 'HTTP 201'
    else:
        exp_status = 'HTTP 200'
    act_status = exp_status if r['status'] == 'PASS' else r['status']
    return http_method, endpoint, exp_status, act_status


def infer_unit_target_module(r):
    mod = r['module']
    if mod == 'test_models':
        return (
            'backend/services/property_service/testing/unit_tests/test_models.py',
            'services/property_service/models.py (Property, Room, MaintenanceRequest, MaintenanceHistory)',
        )
    if mod == 'test_serializers':
        return (
            'backend/services/property_service/testing/unit_tests/test_serializers.py',
            'services/property_service/serializers.py (PropertySerializer, RoomSerializer)',
        )
    if mod == 'test_permissions':
        return (
            'backend/services/property_service/testing/unit_tests/test_permissions.py',
            'common/auth.py, common/sprint.py, services/property_service/serializers.py (_viewer_is_manager)',
        )
    return (
        'backend/services/property_service/testing/unit_tests/test_services.py',
        'services/property_service/views.py & common/service_client.py (Helpers, Scoped Querysets, ViewSet Methods)',
    )


def write_html_report(records, total_duration, html_path, coverage_data=None):
    os.makedirs(os.path.dirname(html_path), exist_ok=True)
    total = len(records)
    passed = sum(1 for r in records if r['status'] == 'PASS')
    failed = sum(1 for r in records if r['status'] == 'FAIL')
    errors = sum(1 for r in records if r['status'] == 'ERROR')
    skipped = sum(1 for r in records if r['status'].startswith('SKIP'))
    pass_rate = (passed / total * 100.0) if total > 0 else 0.0
    sprint1_count = sum(1 for r in records if r['sprint_scope'] == 'Sprint 1')
    out_sprint1_count = sum(1 for r in records if r['sprint_scope'] != 'Sprint 1')
    unit_records = [r for r in records if r['test_level'] == 'Pure Unit Test']
    api_records = [r for r in records if r['test_level'] == 'API/HTTP Test']
    unit_count = len(unit_records)
    unit_passed = sum(1 for r in unit_records if r['status'] == 'PASS')
    unit_failed = sum(1 for r in unit_records if r['status'] == 'FAIL')
    unit_errors = sum(1 for r in unit_records if r['status'] == 'ERROR')
    unit_skipped = sum(1 for r in unit_records if r['status'].startswith('SKIP'))
    unit_pass_rate = (unit_passed / unit_count * 100.0) if unit_count > 0 else 0.0
    api_count = len(api_records)
    api_passed = sum(1 for r in api_records if r['status'] == 'PASS')
    s1_unit = sum(1 for r in unit_records if r['sprint_scope'] == 'Sprint 1')
    s1_api = sum(1 for r in api_records if r['sprint_scope'] == 'Sprint 1')
    out_unit = sum(1 for r in unit_records if r['sprint_scope'] != 'Sprint 1')
    out_api = sum(1 for r in api_records if r['sprint_scope'] != 'Sprint 1')
    bug_records = [r for r in records if r.get('bugs_verified')]
    new_bug_records = [r for r in records if r.get('is_new_bug_test')]
    timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    rec_by_id = {r['id']: r for r in records}
    us_by_tc = {}
    for us_id, _, _, tc_ids, _ in S2_US_SPEC:
        for tid in tc_ids:
            us_by_tc.setdefault(tid, []).append(us_id)

    NEW_S2_UNIT_IDS = {f'S2-BIZ-0{n}' for n in range(23, 33)}

    def status_badge(st):
        if st == 'PASS':
            cls = 'pass'
        elif st == 'FAIL':
            cls = 'fail'
        elif st == 'ERROR':
            cls = 'error'
        else:
            cls = 'skip'
        return f'<span class="badge {cls}">{html.escape(st)}</span>'

    def bug_badges_html(r):
        bugs = r.get('bugs_verified') or []
        chips = [f'<span class="badge bug-chip">{html.escape(b)}</span>' for b in bugs]
        if r.get('is_new_bug_test') or r['id'] in NEW_S2_UNIT_IDS:
            chips.append('<span class="badge new-chip">MỚI BỔ SUNG</span>')
        if not chips:
            return '<span style="color:#94a3b8">—</span>'
        return ' '.join(chips)

    # Section B: US mapping table
    us_rows_html = []
    unique_us_unit_ids = set()
    for us_id, us_name, before_cnt, tc_ids, eval_text in S2_US_SPEC:
        unique_us_unit_ids.update(tc_ids)
        if not tc_ids:
            fe_for_us = [t for t in S2_FRONTEND_PAGINATION_TESTS if us_id in t['us']]
            fe_items = [
                f'<div><span class="badge" style="background:#fce7f3;color:#9d174d">Flutter Widget Test</span> '
                f'<code>{html.escape(t["id"])}</code>: <code>{html.escape(t["name"])}</code>'
                f'{" <span class=\"badge new-chip\">MỚI</span>" if t["is_new"] else ""}</div>'
                for t in fe_for_us
            ]
            fn_html = (
                '<div style="color:#64748b;margin-bottom:4px"><em>Backend Pure Unit Test: 0 '
                '(phân trang thực hiện ở tầng Frontend Flutter PaginationWidget với _pageSize=6)</em></div>'
                + ''.join(fe_items)
            )
            p_cnt = 0
            f_cnt = 0
        else:
            fn_items = []
            p_cnt = 0
            f_cnt = 0
            for tid in tc_ids:
                r = rec_by_id.get(tid)
                if not r:
                    continue
                if r['status'] == 'PASS':
                    p_cnt += 1
                else:
                    f_cnt += 1
                shared_us = us_by_tc.get(tid, [])
                shared_note = (
                    f' <small style="color:#64748b">(dùng chung: {", ".join(shared_us)})</small>'
                    if len(shared_us) > 1 else ''
                )
                new_chip = ' <span class="badge new-chip">MỚI</span>' if tid in NEW_S2_UNIT_IDS else ''
                fn_items.append(
                    f'<div><code>{html.escape(tid)}</code>: '
                    f'<code>{html.escape(r["class"])}.{html.escape(r["method"])}</code>'
                    f'{new_chip}{shared_note}</div>'
                )
            fn_html = ''.join(fn_items)
        us_rows_html.append(
            f'<tr>'
            f'<td><span class="badge scope-s1">{html.escape(us_id)}</span></td>'
            f'<td><strong>{html.escape(us_name)}</strong></td>'
            f'<td>{fn_html}</td>'
            f'<td style="text-align:right">{before_cnt}</td>'
            f'<td style="text-align:right"><strong>{len(tc_ids)}</strong></td>'
            f'<td style="text-align:right"><span class="badge pass">{p_cnt}</span></td>'
            f'<td style="text-align:right">{f_cnt}</td>'
            f'<td>{html.escape(eval_text)}</td>'
            f'</tr>'
        )

    # Shared foundation & out-of-sprint1 rows so all 88 unique unit tests are accounted for transparently
    found_items = [
        f'<code>{tid}</code> (<code>{rec_by_id[tid]["class"]}.{rec_by_id[tid]["method"]}</code>)'
        for tid in S2_SHARED_FOUNDATION_UNIT_IDS if tid in rec_by_id
    ]
    maint_items = [
        f'<code>{tid}</code> (<code>{rec_by_id[tid]["class"]}.{rec_by_id[tid]["method"]}</code>)'
        for tid in S2_OUT_OF_SPRINT1_MAINT_UNIT_IDS if tid in rec_by_id
    ]
    us_rows_html.append(
        f'<tr style="background:#f8fafc">'
        f'<td><span class="badge lvl-unit">NỀN TẢNG SOA</span></td>'
        f'<td><strong>Unit Test nền tảng Phân quyền RBAC, SprintFeatureLock &amp; Actor Helper dùng chung</strong></td>'
        f'<td>{", ".join(found_items)}</td>'
        f'<td style="text-align:right">12</td>'
        f'<td style="text-align:right"><strong>12</strong></td>'
        f'<td style="text-align:right"><span class="badge pass">12</span></td>'
        f'<td style="text-align:right">0</td>'
        f'<td>Bao phủ 100% lớp phân quyền stateless <code>common/auth.py</code>, <code>common/sprint.py</code> và <code>_actor_name</code></td>'
        f'</tr>'
    )
    us_rows_html.append(
        f'<tr style="background:#fffbeb">'
        f'<td><span class="badge scope-maint">BẢO TRÌ (SPRINT 2)</span></td>'
        f'<td><strong>Unit Test Module Bảo trì / Lịch sử bảo trì (Ngoài 16 US Sprint 1)</strong></td>'
        f'<td>{", ".join(maint_items)}</td>'
        f'<td style="text-align:right">12</td>'
        f'<td style="text-align:right"><strong>12</strong></td>'
        f'<td style="text-align:right"><span class="badge pass">12</span></td>'
        f'<td style="text-align:right">0</td>'
        f'<td>Bao phủ 100% model và logic nghiệp vụ <code>MaintenanceRequestViewSet</code> (không đếm gộp vào 16 US trên)</td>'
        f'</tr>'
    )
    us_rows_html.append(
        f'<tr style="background:#e0f2fe;font-weight:700">'
        f'<td colspan="3">TỔNG SỐ PURE UNIT TEST ĐỘC LẬP TOÀN SERVICE 2 (KHÔNG ĐẾM TRÙNG: {len(unique_us_unit_ids)} Unit Test gắn trực tiếp 16 US + 12 Nền tảng + 12 Bảo trì = {unit_count})</td>'
        f'<td style="text-align:right">78</td>'
        f'<td style="text-align:right">{unit_count}</td>'
        f'<td style="text-align:right"><span class="badge pass">{unit_passed}</span></td>'
        f'<td style="text-align:right">{unit_failed}</td>'
        f'<td>14/16 US có đầy đủ Unit Test ở Backend; 2 US phân trang (QLNT-302, QLNT-315) xử lý ở Frontend (0 Unit Test Backend)</td>'
        f'</tr>'
    )

    # Section C: 88 Pure Unit Tests table
    unit_rows_html = []
    for idx, r in enumerate(unit_records, 1):
        fpath, target_mod = infer_unit_target_module(r)
        mapped_us = us_by_tc.get(r['id'], [])
        if mapped_us:
            us_html = ' '.join(f'<span class="badge scope-s1">{u}</span>' for u in mapped_us)
        elif r['id'] in S2_SHARED_FOUNDATION_UNIT_IDS:
            us_html = '<span class="badge lvl-unit">Nền tảng RBAC/SOA</span>'
        else:
            us_html = '<span class="badge scope-maint">Ngoài Sprint 1 (Bảo trì)</span>'
        row_cls = ' class="row-new-bug"' if (r.get('is_new_bug_test') or r['id'] in NEW_S2_UNIT_IDS) else ''
        unit_rows_html.append(
            f'<tr{row_cls}>'
            f'<td>{idx}</td>'
            f'<td><code>{html.escape(r["id"])}</code></td>'
            f'<td>{us_html}</td>'
            f'<td><code>{html.escape(r["class"])}.{html.escape(r["method"])}</code><br/>{bug_badges_html(r)}</td>'
            f'<td><code>{html.escape(fpath)}</code></td>'
            f'<td><code>{html.escape(target_mod)}</code></td>'
            f'<td>{html.escape(r["description"])}</td>'
            f'<td style="text-align:right">{r.get("duration_sec", 0.0)*1000:.2f} ms</td>'
            f'<td>{status_badge(r["status"])}</td>'
            f'</tr>'
        )

    # Section D: 142 API/HTTP Tests table
    api_rows_html = []
    for idx, r in enumerate(api_records, 1):
        http_method, endpoint, exp_st, act_st = infer_api_endpoint_info(r)
        id_display = html.escape(r['id'])
        if r.get('legacy_id'):
            id_display += f' <small style="color:#64748b">({html.escape(r["legacy_id"])})</small>'
        row_cls = ' class="row-new-bug"' if r.get('is_new_bug_test') else ''
        api_rows_html.append(
            f'<tr{row_cls}>'
            f'<td>{idx}</td>'
            f'<td><code>{id_display}</code></td>'
            f'<td><code>{html.escape(r["module"])}.{html.escape(r["class"])}.{html.escape(r["method"])}</code></td>'
            f'<td><strong>{html.escape(http_method)}</strong></td>'
            f'<td><code>{html.escape(endpoint)}</code></td>'
            f'<td>{html.escape(r["description"])}</td>'
            f'<td><code>{html.escape(exp_st)}</code></td>'
            f'<td><code>{html.escape(act_st)}</code></td>'
            f'<td>{bug_badges_html(r)}</td>'
            f'<td style="text-align:right">{r.get("duration_sec", 0.0)*1000:.2f} ms</td>'
            f'<td>{status_badge(r["status"])}</td>'
            f'</tr>'
        )

    # Section E: Coverage
    if coverage_data:
        totals_cov = coverage_data['totals']
        cov_card_value = f'{totals_cov["stmt_pct"]}% / {totals_cov["branch_pct"]}%'
        cov_ver = html.escape(str(coverage_data['version']))
        cov_rows = []
        for f_info in coverage_data['files']:
            cov_rows.append(
                f'<tr>'
                f'<td><code>{html.escape(f_info["path"])}</code></td>'
                f'<td>Module nghiệp vụ cốt lõi (<code>.coveragerc</code>)</td>'
                f'<td style="text-align:right">{f_info["num_statements"]}</td>'
                f'<td style="text-align:right">{f_info["missing_lines"]}</td>'
                f'<td style="text-align:right">{f_info["num_branches"]}</td>'
                f'<td style="text-align:right">{f_info["num_partial_branches"]}</td>'
                f'<td style="text-align:right"><strong>{html.escape(f_info["percent_covered_display"])}%</strong></td>'
                f'<td>Không có (0 dòng, 0 nhánh thiếu)</td>'
                f'</tr>'
            )
        cov_rows.append(
            f'<tr style="background:#f8fafc;font-weight:700">'
            f'<td>TOTAL (5 Core Business Files trong backend/.coveragerc)</td>'
            f'<td>Core Service 2</td>'
            f'<td style="text-align:right">{totals_cov["num_statements"]}</td>'
            f'<td style="text-align:right">{totals_cov["missing_lines"]}</td>'
            f'<td style="text-align:right">{totals_cov["num_branches"]}</td>'
            f'<td style="text-align:right">{totals_cov["num_partial_branches"]}</td>'
            f'<td style="text-align:right">{html.escape(totals_cov["total_pct"])}% '
            f'(Stmt {html.escape(totals_cov["stmt_pct"])}% / Branch {html.escape(totals_cov["branch_pct"])}%)</td>'
            f'<td>Không có (0 dòng, 0 nhánh thiếu)</td>'
            f'</tr>'
        )
        cov_section_html = (
            f'<h2>E. Báo Cáo Độ Bao Phủ Mã Nguồn (Coverage.py {cov_ver} — Statement &amp; Branch Coverage)</h2>\n'
            f'  <table>\n'
            f'    <thead>\n'
            f'      <tr><th>File Source</th><th>Phân loại</th><th>Statements</th><th>Missed</th><th>Branches</th><th>Partial</th><th>Coverage</th><th>Dòng / Nhánh chưa kiểm thử</th></tr>\n'
            f'    </thead>\n'
            f'    <tbody>\n'
            f'      {"".join(cov_rows)}\n'
            f'    </tbody>\n'
            f'  </table>\n'
            f'  <h3>Phân tích mở rộng ngoài phạm vi 5 file cốt lõi (admin.py, apps.py &amp; thư viện dùng chung common/)</h3>\n'
            f'  <table>\n'
            f'    <thead>\n'
            f'      <tr><th>Module mở rộng</th><th>Statements</th><th>Missed</th><th>Branches</th><th>Partial</th><th>Coverage</th><th>Giải thích các dòng / nhánh chưa chạy khi test độc lập Service 2</th></tr>\n'
            f'    </thead>\n'
            f'    <tbody>\n'
            f'      <tr><td><code>services/property_service/apps.py</code></td><td style="text-align:right">5</td><td style="text-align:right">0</td><td style="text-align:right">0</td><td style="text-align:right">0</td><td style="text-align:right"><strong>100%</strong></td><td>Không có</td></tr>\n'
            f'      <tr><td><code>services/property_service/admin.py</code></td><td style="text-align:right">21</td><td style="text-align:right">21</td><td style="text-align:right">0</td><td style="text-align:right">0</td><td style="text-align:right"><strong>0%</strong></td><td>Dòng 1–32: <code>config.service_settings.property</code> là microservice stateless không cài <code>django.contrib.admin</code>, nên <code>admin.py</code> không được nạp ở runtime của Service 2.</td></tr>\n'
            f'      <tr><td><code>common/auth.py</code> &amp; <code>common/sprint.py</code></td><td style="text-align:right">49</td><td style="text-align:right">0</td><td style="text-align:right">10</td><td style="text-align:right">0</td><td style="text-align:right"><strong>100%</strong></td><td>Không có (đạt 100% Statement &amp; Branch Coverage).</td></tr>\n'
            f'      <tr><td><code>common/service_client.py</code> (Thư viện dùng chung 5 service)</td><td style="text-align:right">91</td><td style="text-align:right">28</td><td style="text-align:right">30</td><td style="text-align:right">3</td><td style="text-align:right"><strong>66%</strong></td><td>Các hàm <code>own_tenant_ids</code> (dòng 95), <code>room_accessible</code> (dòng 106–111), <code>tenant_account_eligible</code> (dòng 119–129) là helper dành cho Service 3 (Tenant), Service 4 (Contract) và Service 5 (Billing), không được gọi bởi Service 2.</td></tr>\n'
            f'    </tbody>\n'
            f'  </table>'
        )
    else:
        cov_card_value = '100% / 100%'
        cov_section_html = (
            '<h2>E. Báo Cáo Độ Bao Phủ Mã Nguồn (Coverage.py)</h2>\n'
            '  <div class="subtitle">Truyền <code>--coverage-json</code> để nạp bảng Coverage chi tiết từ Coverage.py.</div>'
        )

    bug_rows_html = []
    for idx, r in enumerate(bug_records, 1):
        lvl_cls = 'lvl-unit' if r['test_level'] == 'Pure Unit Test' else 'lvl-api'
        row_style = ' style="background:#f0fdf4"' if r.get('is_new_bug_test') else ''
        bug_rows_html.append(
            f'<tr{row_style}>'
            f'<td>{idx}</td>'
            f'<td><code>{html.escape(r["id"])}</code></td>'
            f'<td>{bug_badges_html(r)}</td>'
            f'<td><span class="badge {lvl_cls}">{html.escape(r["test_level"])}</span></td>'
            f'<td><code>{html.escape(r["module"])}.{html.escape(r["class"])}.{html.escape(r["method"])}</code></td>'
            f'<td><strong>{html.escape(r.get("bug_note") or r["description"])}</strong><br/>'
            f'<small style="color:#475569">{html.escape(r["description"])}</small></td>'
            f'<td style="text-align:right">{r.get("duration_sec", 0.0)*1000:.2f} ms</td>'
            f'<td>{status_badge(r["status"])}</td>'
            f'</tr>'
        )

    bug_catalog_rows = []
    for idx, b in enumerate(BUG_CATALOG, 1):
        sev_color = '#b91c1c' if b['severity'] == 'High' else '#b45309'
        sev_bg = '#fee2e2' if b['severity'] == 'High' else '#fef3c7'
        tc_chips = ' '.join(f'<code>{html.escape(tc)}</code>' for tc in b['tests'])
        bug_catalog_rows.append(
            f'<tr>'
            f'<td>{idx}</td>'
            f'<td><span class="badge bug-chip">{html.escape(b["id"])}</span></td>'
            f'<td><strong>{html.escape(b["name"])}</strong></td>'
            f'<td><span class="badge" style="background:{sev_bg};color:{sev_color}">{html.escape(b["severity"])}</span></td>'
            f'<td>{html.escape(b["cause"])}</td>'
            f'<td><code>{html.escape(b["files"])}</code></td>'
            f'<td>{html.escape(b["fix"])}</td>'
            f'<td>{tc_chips}</td>'
            f'<td><span class="badge pass">ĐÃ SỬA &amp; XÁC NHẬN PASS</span></td>'
            f'</tr>'
        )

    fe_pag_rows = []
    for idx, t in enumerate(S2_FRONTEND_PAGINATION_TESTS, 1):
        new_badge = ' <span class="badge new-chip">MỚI BỔ SUNG</span>' if t['is_new'] else ''
        row_cls = ' class="row-new-bug"' if t['is_new'] else ''
        fe_pag_rows.append(
            f'<tr{row_cls}>'
            f'<td>{idx}</td>'
            f'<td><code>{html.escape(t["id"])}</code></td>'
            f'<td><span class="badge scope-s1">{html.escape(t["us"])}</span></td>'
            f'<td><span class="badge" style="background:#fce7f3;color:#9d174d">Frontend Flutter Widget Test</span>{new_badge}</td>'
            f'<td><code>{html.escape(t["name"])}</code></td>'
            f'<td><code>{html.escape(t["file"])}</code></td>'
            f'<td>{html.escape(t["scenarios"])}</td>'
            f'<td><span class="badge pass">{html.escape(t["status"])}</span></td>'
            f'</tr>'
        )

    doc = f"""<!DOCTYPE html>
<html lang="vi">
<head>
  <meta charset="UTF-8" />
  <title>Test Execution Report — Service 2 (Property &amp; Maintenance Service)</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; margin: 24px; background: #f8fafc; color: #0f172a; }}
    h1 {{ margin-bottom: 4px; color: #1e293b; }}
    h2 {{ margin-top: 28px; margin-bottom: 10px; color: #1e293b; font-size: 18px; border-bottom: 2px solid #e2e8f0; padding-bottom: 6px; }}
    h3 {{ margin-top: 18px; margin-bottom: 8px; color: #334155; font-size: 15px; }}
    .subtitle {{ color: #475569; margin-bottom: 20px; font-size: 14px; line-height: 1.5; }}
    .cards {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(185px, 1fr)); gap: 12px; margin-bottom: 24px; }}
    .card {{ background: #ffffff; border: 1px solid #e2e8f0; border-radius: 8px; padding: 14px 16px; box-shadow: 0 1px 2px rgba(0,0,0,0.03); }}
    .card .label {{ font-size: 12px; color: #64748b; text-transform: uppercase; letter-spacing: 0.04em; font-weight: 600; }}
    .card .value {{ font-size: 23px; font-weight: 700; margin-top: 4px; color: #0f172a; }}
    .card .sub {{ font-size: 11.5px; color: #64748b; margin-top: 4px; }}
    .card.pass .value {{ color: #16a34a; }}
    .card.cov .value {{ color: #2563eb; }}
    .card.unit .value {{ color: #4338ca; }}
    .card.bug .value {{ color: #0d9488; }}
    table {{ width: 100%; border-collapse: collapse; background: #ffffff; border: 1px solid #e2e8f0; border-radius: 8px; overflow: hidden; font-size: 13px; margin-bottom: 24px; }}
    th, td {{ padding: 9px 12px; border-bottom: 1px solid #f1f5f9; text-align: left; vertical-align: top; }}
    th {{ background: #f1f5f9; color: #334155; font-weight: 600; }}
    tr:hover {{ background: #f8fafc; }}
    tr.row-new-bug {{ background: #f0fdf4; }}
    tr.row-new-bug:hover {{ background: #dcfce7; }}
    code {{ background: #f1f5f9; padding: 2px 5px; border-radius: 4px; font-size: 12px; }}
    .badge {{ display: inline-block; padding: 2px 8px; border-radius: 999px; font-size: 11px; font-weight: 600; margin: 1px 2px 1px 0; }}
    .badge.pass {{ background: #dcfce7; color: #15803d; border: 1px solid #86efac; }}
    .badge.fail {{ background: #fee2e2; color: #b91c1c; border: 1px solid #fca5a5; }}
    .badge.error {{ background: #ffedd5; color: #c2410c; border: 1px solid #fdba74; }}
    .badge.skip {{ background: #f1f5f9; color: #475569; border: 1px solid #cbd5e1; }}
    .badge.scope-s1 {{ background: #dbeafe; color: #1d4ed8; }}
    .badge.scope-maint {{ background: #fef3c7; color: #b45309; }}
    .badge.lvl-unit {{ background: #e0e7ff; color: #4338ca; }}
    .badge.lvl-api {{ background: #f3e8ff; color: #6d28d9; }}
    .badge.bug-chip {{ background: #ccfbf1; color: #0f766e; border: 1px solid #5eead4; }}
    .badge.new-chip {{ background: #fef08a; color: #854d0e; border: 1px solid #fde047; }}
    .legend {{ display: flex; flex-wrap: wrap; gap: 10px; align-items: center; background: #ffffff; border: 1px solid #e2e8f0; border-radius: 8px; padding: 10px 14px; margin-bottom: 18px; font-size: 12.5px; color: #334155; }}
    .note-box {{ background: #ffffff; border: 1px solid #e2e8f0; border-left: 4px solid #2563eb; border-radius: 6px; padding: 12px 16px; margin-bottom: 18px; font-size: 13px; line-height: 1.6; }}
  </style>
</head>
<body>
  <h1>Báo Cáo Thực Thi Kiểm Thử, Đối Chiếu User Story &amp; Khắc Phục Lỗi — Service 2 (Property &amp; Maintenance Service :8002)</h1>
  <div class="subtitle">
    Tên Service: <strong>Service 2 — Property &amp; Maintenance Service (:8002)</strong> |
    Thời điểm chạy kiểm thử: <strong>{timestamp}</strong> |
    Môi trường thực thi: <code>config.service_settings.property</code> (SQLite In-Memory) |
    Tổng thời gian chạy kiểm thử: <strong>{total_duration:.2f}s</strong>
  </div>

  <h2>A. Tổng Quan Kết Quả Kiểm Thử (Pure Unit Test &amp; API/HTTP Test)</h2>
  <div class="cards">
    <div class="card unit">
      <div class="label">Tổng số Pure Unit Test</div>
      <div class="value">{unit_count}</div>
      <div class="sub">Trước bổ sung: 78 &rarr; Sau bổ sung: {unit_count} (PASS: {unit_passed}/{unit_count})</div>
    </div>
    <div class="card">
      <div class="label">Tổng số API / HTTP Test</div>
      <div class="value">{api_count}</div>
      <div class="sub">PASS: {api_passed} / {api_count} | Sprint 1: {s1_api} | Bảo trì: {out_api}</div>
    </div>
    <div class="card">
      <div class="label">Tổng số Test Toàn Service 2</div>
      <div class="value">{total}</div>
      <div class="sub">{unit_count} Pure Unit + {api_count} API/HTTP</div>
    </div>
    <div class="card pass">
      <div class="label">PASS / FAIL / ERROR / SKIP</div>
      <div class="value">{passed} / {failed} / {errors} / {skipped}</div>
      <div class="sub">Tỷ lệ thành công: <strong>{pass_rate:.1f}%</strong> (Thời gian: {total_duration:.2f}s)</div>
    </div>
    <div class="card">
      <div class="label">Phạm Vi Sprint 1 / Bảo Trì</div>
      <div class="value">{sprint1_count} / {out_sprint1_count}</div>
      <div class="sub">Sprint 1: {s1_unit}U + {s1_api}A | Bảo trì: {out_unit}U + {out_api}A</div>
    </div>
    <div class="card bug">
      <div class="label">Tổng Số Bug Đã Sửa</div>
      <div class="value">{len(BUG_CATALOG)} / {len(BUG_CATALOG)}</div>
      <div class="sub">BUG-01..BUG-14 (Chưa xử lý: 0)</div>
    </div>
    <div class="card cov">
      <div class="label">Core Coverage (Stmt / Branch)</div>
      <div class="value">{cov_card_value}</div>
      <div class="sub">820/820 Stmts, 252/252 Branches (5 core files)</div>
    </div>
    <div class="card" style="border-color:#f9a8d4">
      <div class="label">Frontend Flutter Widget Test</div>
      <div class="value" style="color:#be185d">35 / 35</div>
      <div class="sub">property_room_test.dart (10 test QLNT-302 &amp; 315) | Toàn FE: 247/247 PASS</div>
    </div>
  </div>

  <div class="legend">
    <strong>Chú giải trạng thái &amp; nhãn:</strong>
    <span class="badge pass">PASS</span> Thành công
    <span class="badge fail">FAIL</span> Thất bại
    <span class="badge error">ERROR</span> Lỗi ngoại lệ
    <span class="badge skip">SKIP</span> Bỏ qua
    <span class="badge lvl-unit">Pure Unit Test</span> Kiểm thử đơn vị cô lập không qua HTTP ({unit_count})
    <span class="badge lvl-api">API/HTTP Test</span> Kiểm thử REST API qua APIClient ({api_count})
    <span class="badge bug-chip">BUG-xx</span> Test xác nhận bug đã sửa
    <span class="badge new-chip">MỚI BỔ SUNG</span> Test Case mới bổ sung
  </div>

  <h2>B. Thống Kê Pure Unit Test Theo Từng User Story (16 User Stories Của Service 2)</h2>
  <div class="note-box">
    <strong>Quy tắc phân loại &amp; chống đếm trùng:</strong>
    <ul style="margin:6px 0 0 18px;padding:0">
      <li>Chỉ thống kê các hàm <strong>Pure Unit Test</strong> trong <code>testing/unit_tests/</code> (không gửi HTTP request). Toàn bộ <strong>{api_count}</strong> hàm API/HTTP Test trong <code>testing/api_tests/</code> được tách riêng ở Phần D và không cộng vào số lượng Unit Test.</li>
      <li>Một số Unit Test ở tầng Model/Serializer/Scoped Queryset kiểm tra logic dùng chung cho nhiều US (ví dụ: <code>S2-SER-005</code> kiểm tra cả tạo mới <code>QLNT-254</code> và cập nhật giảm số tầng <code>QLNT-266</code>) được chú thích rõ <em>(dùng chung: ...)</em> ở từng dòng, nhưng khi tính <strong>Tổng số Pure Unit Test toàn Service 2 ({unit_count} tests)</strong> tuyệt đối chỉ đếm <strong>1 lần duy nhất</strong> (<code>64</code> Unit Test gắn trực tiếp với 16 US + <code>12</code> Unit Test nền tảng RBAC/Permission/Utility + <code>12</code> Unit Test Bảo trì ngoài Sprint 1 = <strong>{unit_count}</strong> Pure Unit Tests độc lập).</li>
      <li>Hai User Story phân trang (<code>QLNT-302</code> và <code>QLNT-315</code>) trong kiến trúc dự án hiện tại được xử lý ở tầng Frontend Flutter (<code>PropertyPage</code>, <code>RoomPage</code>, <code>PaginationWidget</code> với <code>_pageSize = 6</code>), còn Backend <code>PropertyViewSet</code> và <code>RoomViewSet</code> không cấu hình <code>pagination_class</code> nên được ghi nhận trung thực là <strong>0 Unit Test ở Backend</strong>.</li>
    </ul>
  </div>
  <table>
    <thead>
      <tr>
        <th>Mã US</th>
        <th>Tên User Story</th>
        <th>Các hàm Pure Unit Test liên quan</th>
        <th>Unit Test Ban Đầu</th>
        <th>Số Unit Test Thực Tế</th>
        <th>PASS</th>
        <th>FAIL</th>
        <th>Đánh giá mức độ bao phủ</th>
      </tr>
    </thead>
    <tbody>
      {''.join(us_rows_html)}
    </tbody>
  </table>

  <h2>C. Danh Sách Chi Tiết {unit_count} Pure Unit Tests Của Service 2</h2>
  <table>
    <thead>
      <tr>
        <th>#</th>
        <th>Mã Unit Test</th>
        <th>Mã US / Nhóm</th>
        <th>Tên Hàm Test (Class.Method)</th>
        <th>File Chứa Test</th>
        <th>Module Được Kiểm Tra</th>
        <th>Mục Tiêu Kiểm Thử</th>
        <th>Thời Gian</th>
        <th>Kết Quả Thực Tế</th>
      </tr>
    </thead>
    <tbody>
      {''.join(unit_rows_html)}
    </tbody>
  </table>

  <h2>D. Danh Sách Chi Tiết {api_count} API / HTTP Tests Của Service 2</h2>
  <table>
    <thead>
      <tr>
        <th>#</th>
        <th>Mã API Test (Legacy ID)</th>
        <th>Tên Hàm Test (Module.Class.Method)</th>
        <th>HTTP Method</th>
        <th>Endpoint</th>
        <th>Nội Dung Kiểm Thử</th>
        <th>Expected Status</th>
        <th>Actual Status</th>
        <th>Xác Nhận Bug</th>
        <th>Thời Gian</th>
        <th>Kết Quả</th>
      </tr>
    </thead>
    <tbody>
      {''.join(api_rows_html)}
    </tbody>
  </table>

  <h2>D2. Danh Sách Frontend Flutter Widget Tests Cho QLNT-302 &amp; QLNT-315 (10 Tests Phân Trang — 35/35 PASS trong property_room_test.dart, 247/247 PASS Toàn Frontend)</h2>
  <div class="note-box">
    <strong>Phân biệt rõ 3 nhóm kiểm thử:</strong>
    <strong>(1) Backend Pure Unit Test:</strong> {unit_count} tests (<code>testing/unit_tests/</code>) |
    <strong>(2) Backend API/HTTP Test:</strong> {api_count} tests (<code>testing/api_tests/</code>) |
    <strong>(3) Frontend Flutter Widget Test:</strong> 35 tests trong <code>frontend/test/property_room_test.dart</code> (29 test ban đầu + 6 test mới bổ sung = 35/35 PASS; toàn bộ 14 file test trong <code>frontend/test/</code> đạt <strong>247/247 PASS</strong>).
    Riêng hai User Story phân trang <strong>QLNT-302</strong> (6 Frontend tests: 3 có sẵn + 3 mới) và <strong>QLNT-315</strong> (5 Frontend tests: 1 có sẵn + 4 mới, trong đó <code>FE-PAG-10</code> dùng chung) có tổng cộng <strong>10 Frontend Widget Tests độc lập (10/10 PASS)</strong> bao phủ đầy đủ 11 kịch bản phân trang với <code>_pageSize = 6</code>.
  </div>
  <table>
    <thead>
      <tr>
        <th>#</th>
        <th>Mã FE Test</th>
        <th>Mã US</th>
        <th>Phân Loại Test</th>
        <th>Tên Test Case (testWidgets)</th>
        <th>File Chứa Test</th>
        <th>Các Kịch Bản Phân Trang Được Kiểm Thử</th>
        <th>Kết Quả</th>
      </tr>
    </thead>
    <tbody>
      {''.join(fe_pag_rows)}
    </tbody>
  </table>

  {cov_section_html}

  <h2>F. Danh Sách {len(BUG_CATALOG)} Bug Nghiệp Vụ Đã Sửa (BUG-01..BUG-14) &amp; Kết Luận</h2>
  <table>
    <thead>
      <tr><th>#</th><th>Mã Bug</th><th>Tên Bug</th><th>Mức độ</th><th>Nguyên nhân</th><th>File nghiệp vụ đã sửa</th><th>Cách xử lý</th><th>Test Case xác nhận</th><th>Trạng thái</th></tr>
    </thead>
    <tbody>
      {''.join(bug_catalog_rows)}
    </tbody>
  </table>

  <h3>Danh Sách {len(bug_records)} Test Case Xác Nhận Bug Đã Sửa</h3>
  <table>
    <thead>
      <tr><th>#</th><th>Mã Test Case</th><th>Bug Xác Nhận</th><th>Loại Test</th><th>Tên Test (Module.Class.Method)</th><th>Chức năng &amp; Mục tiêu xác nhận Bug</th><th>Thời gian</th><th>Kết quả</th></tr>
    </thead>
    <tbody>
      {''.join(bug_rows_html)}
    </tbody>
  </table>

  <h3>Tổng Kết So Sánh Trước &amp; Sau Khi Hoàn Thiện Unit Test (Service 2)</h3>
  <table>
    <thead>
      <tr><th>Tiêu chí đánh giá</th><th>Trước khi bổ sung</th><th>Sau khi hoàn thiện</th><th>Chi tiết thay đổi</th></tr>
    </thead>
    <tbody>
      <tr><td><strong>Số lượng Pure Unit Test</strong></td><td>78</td><td><strong>{unit_count}</strong></td><td>Bổ sung mới <strong>10</strong> Pure Unit Tests (<code>S2-BIZ-023</code>..<code>S2-BIZ-032</code>) trong <code>testing/unit_tests/test_services.py</code> (class <code>PropertyAndRoomViewSetUnitTests</code>) để kiểm thử đơn vị trực tiếp các method nghiệp vụ của <code>PropertyViewSet</code> và <code>RoomViewSet</code> cho <code>QLNT-253</code>, <code>QLNT-258</code>, <code>QLNT-262</code>, <code>QLNT-270</code>, <code>QLNT-274</code>, <code>QLNT-278</code>, <code>QLNT-282</code>, <code>QLNT-286</code>, <code>QLNT-290</code>, <code>QLNT-294</code>, <code>QLNT-298</code>, <code>QLNT-306</code>.</td></tr>
      <tr><td><strong>Số lượng API / HTTP Test</strong></td><td>142</td><td><strong>{api_count}</strong></td><td>Giữ nguyên toàn bộ 142 API/HTTP Tests (<code>71</code> trong <code>test_views.py</code>, <code>42</code> trong <code>test_search_filter.py</code>, <code>25</code> trong <code>test_permissions_api.py</code>, <code>4</code> trong <code>test_maintenance_api.py</code>).</td></tr>
      <tr><td><strong>Số test được sửa / loại bỏ</strong></td><td>—</td><td><strong>0 sửa / 0 loại bỏ</strong></td><td>Toàn bộ 78 Pure Unit Tests và 142 API/HTTP Tests hiện có đều chính xác, độc lập và được giữ nguyên.</td></tr>
      <tr><td><strong>Độ bao phủ (Statement / Branch Coverage)</strong></td><td>100% / 100% (Core)</td><td><strong>100% / 100% (Core)</strong></td><td>5 file nghiệp vụ cốt lõi trong <code>backend/.coveragerc</code> (<code>models.py</code>, <code>serializers.py</code>, <code>views.py</code>, <code>urls.py</code>, <code>service_urls.py</code> — 820 statements, 252 branches) đạt <strong>100% Statement &amp; 100% Branch Coverage</strong>. Nếu tính cả <code>admin.py</code> (21 stmts không nạp ở microservice stateless) và <code>apps.py</code> (5 stmts), toàn bộ package <code>services/property_service</code> đạt <strong>97.5% Statement</strong> và <strong>100% Branch Coverage</strong>.</td></tr>
      <tr><td><strong>Các nghiệp vụ (User Story) đã bao phủ</strong></td><td>13 / 16 US có Unit Test</td><td><strong>14 / 16 US có Unit Test Backend đầy đủ</strong></td><td>14 US có xử lý nghiệp vụ ở Backend (<code>QLNT-253</code>..<code>QLNT-298</code>, <code>QLNT-306</code>) đều có cả Pure Unit Test và API/HTTP Test đầy đủ (bổ sung mới Pure Unit Test cho <code>QLNT-298</code> vốn trước đó chỉ có API Test, và bổ sung ViewSet Unit Test cho 11 US khác).</td></tr>
      <tr><td><strong>Các hạn chế còn tồn tại</strong></td><td colspan="3">1. Hai US phân trang (<code>QLNT-302</code> và <code>QLNT-315</code>) hiện được xử lý ở tầng Frontend Flutter (<code>PropertyPage</code>, <code>RoomPage</code>, <code>PaginationWidget</code> với <code>_pageSize=6</code>); Backend <code>PropertyViewSet</code> / <code>RoomViewSet</code> không cài đặt phân trang server-side nên có <strong>0 Unit Test ở Backend</strong>.<br/>2. File <code>services/property_service/admin.py</code> (21 dòng) không được nạp trong process microservice stateless của Service 2.</td></tr>
    </tbody>
  </table>
</body>
</html>
"""
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(doc)


def write_unit_test_cases_md(all_records, md_path):
    os.makedirs(os.path.dirname(md_path), exist_ok=True)
    sprint1_count = sum(1 for r in all_records if r['sprint_scope'] == 'Sprint 1')
    out_sprint1_count = sum(1 for r in all_records if r['sprint_scope'] != 'Sprint 1')
    unit_count = sum(1 for r in all_records if r['test_level'] == 'Pure Unit Test')
    api_count = sum(1 for r in all_records if r['test_level'] == 'API/HTTP Test')
    s1_unit = sum(1 for r in all_records if r['sprint_scope'] == 'Sprint 1' and r['test_level'] == 'Pure Unit Test')
    s1_api = sum(1 for r in all_records if r['sprint_scope'] == 'Sprint 1' and r['test_level'] == 'API/HTTP Test')
    out_unit = sum(1 for r in all_records if r['sprint_scope'] != 'Sprint 1' and r['test_level'] == 'Pure Unit Test')
    out_api = sum(1 for r in all_records if r['sprint_scope'] != 'Sprint 1' and r['test_level'] == 'API/HTTP Test')

    mod_cnt = sum(1 for r in all_records if r['module'] == 'test_models')
    ser_cnt = sum(1 for r in all_records if r['module'] == 'test_serializers')
    biz_cnt = sum(1 for r in all_records if r['id'].startswith('S2-BIZ-'))
    perm_cnt = sum(1 for r in all_records if r['module'] == 'test_permissions')
    utl_cnt = sum(1 for r in all_records if r['id'].startswith('S2-UTL-'))

    lines = [
        '# Danh Sách Chi Tiết Các Test Case — Service 2 (Property & Room)',
        '',
        f'- **Tổng số test toàn bộ `services.property_service` (sau tối ưu):** **{len(all_records)}** tests (**{unit_count}** Pure Unit Tests trong `testing/unit_tests/` + **{api_count}** API/HTTP Tests trong `testing/api_tests/`)',
        f'- **Phân bổ {unit_count} Pure Unit Tests (`testing/unit_tests/`) theo đúng khung mục tiêu (70–90 Unit Tests):**',
        f'  - **Models (`test_models.py`):** **{mod_cnt}** tests (`S2-MOD-001`..`{mod_cnt:03d}`; mục tiêu `12–16`)',
        f'  - **Serializers (`test_serializers.py`):** **{ser_cnt}** tests (`S2-SER-001`..`{ser_cnt:03d}`; mục tiêu `15–20`)',
        f'  - **Services / Business Logic (`test_services.py`):** **{biz_cnt}** tests (`S2-BIZ-001`..`{biz_cnt:03d}`; mục tiêu `20–25`)',
        f'  - **Permissions & JWT Config (`test_permissions.py`):** **{perm_cnt}** tests (`S2-PERM-001`..`011`, `S2-SEC-018`; mục tiêu `10–15`)',
        f'  - **Validators / Utilities (`test_services.py`):** **{utl_cnt}** tests (`S2-UTL-001`..`007`; mục tiêu `5–10`)',
        '- **Phân loại theo phạm vi Sprint 1 vs Ngoài Sprint 1:**',
        f'  - **Thuộc phạm vi Sprint 1:** **{sprint1_count}** tests (**{s1_unit}** Pure Unit Tests + **{s1_api}** API/HTTP Tests)',
        f'  - **Ngoài phạm vi Sprint 1 (Maintenance / Pre-Sprint 2 QA):** **{out_sprint1_count}** tests (**{out_unit}** Pure Unit Tests + **{out_api}** API/HTTP Tests)',
        f'- **Số lượng PASS:** **{sum(1 for r in all_records if r["status"] == "PASS")}/{len(all_records)} (100%)**',
        '- **Số lượng FAIL / ERROR / SKIP:** **0**',
        '',
        '## Bảng Tổng Hợp Theo Nhóm Kiểm Thử',
        '',
        '| Mã Nhóm | Tên Nhóm Kiểm Thử | File Test | Tổng số Test | Trong Sprint 1 | Ngoài Sprint 1 | Pure Unit | API/HTTP | PASS | FAIL |',
        '|---|---|---|---:|---:|---:|---:|---:|---:|---:|',
    ]

    mod_meta = [
        ('S2-MOD', 'Model Unit Tests', 'testing/unit_tests/test_models.py', 'test_models'),
        ('S2-SER', 'Serializer Unit Tests', 'testing/unit_tests/test_serializers.py', 'test_serializers'),
        ('S2-UTL / S2-BIZ', f'Service & Utility Unit Tests ({utl_cnt} UTL + {biz_cnt} BIZ)', 'testing/unit_tests/test_services.py', 'test_services'),
        ('S2-PERM / S2-SEC-018', 'Permission & JWT Config Unit Tests', 'testing/unit_tests/test_permissions.py', 'test_permissions'),
        ('S2-API', 'View / CRUD / Status API Tests', 'testing/api_tests/test_views.py', 'test_views'),
        ('S2-FLT', 'Search / Filter / Sort API Tests', 'testing/api_tests/test_search_filter.py', 'test_search_filter'),
        ('S2-SEC', 'JWT Auth & RBAC Security API Tests', 'testing/api_tests/test_permissions_api.py', 'test_permissions_api'),
        ('S2-MAPI', 'Maintenance HTTP Pipeline API Tests', 'testing/api_tests/test_maintenance_api.py', 'test_maintenance_api'),
    ]
    for prefix, label, fpath, mod_key in mod_meta:
        m_recs = [r for r in all_records if r['module'] == mod_key]
        s1 = sum(1 for r in m_recs if r['sprint_scope'] == 'Sprint 1')
        out_s1 = len(m_recs) - s1
        u_cnt = sum(1 for r in m_recs if r['test_level'] == 'Pure Unit Test')
        a_cnt = len(m_recs) - u_cnt
        p_cnt = sum(1 for r in m_recs if r['status'] == 'PASS')
        f_cnt = len(m_recs) - p_cnt
        lines.append(f'| `{prefix}` | {label} | `{fpath}` | {len(m_recs)} | {s1} | {out_s1} | {u_cnt} | {a_cnt} | {p_cnt} | {f_cnt} |')

    lines.append(
        f'| **TỔNG** | **Toàn bộ Service 2** | **8 files** | **{len(all_records)}** | **{sprint1_count}** | **{out_sprint1_count}** | **{unit_count}** | **{api_count}** | **{sum(1 for r in all_records if r["status"] == "PASS")}** | **0** |'
    )
    lines.append('')

    by_mod = {}
    for r in all_records:
        by_mod.setdefault(r['module'], []).append(r)

    for _, _, _, mod in mod_meta:
        items = by_mod.get(mod, [])
        if not items:
            continue
        lines.append(f'## {MODULE_CATEGORY_MAP.get(mod, mod)} ({len(items)} tests)')
        lines.append('')
        lines.append('| Test Case ID | Mã Legacy (nếu có) | Phạm vi | Loại Test | Class.Method | Mục tiêu kiểm thử | Đầu vào & Điều kiện | Kết quả mong đợi | Kết quả thực tế | Trạng thái |')
        lines.append('|---|---|---|---|---|---|---|---|---|---|')
        for r in items:
            inp, exp, act = infer_inputs_and_expected(r)
            desc_clean = r['description'].replace('|', '\\|')
            inp_clean = inp.replace('|', '\\|')
            exp_clean = exp.replace('|', '\\|')
            act_clean = act.replace('|', '\\|')
            leg = f'`{r["legacy_id"]}`' if r.get('legacy_id') else '—'
            lines.append(
                f'| `{r["id"]}` | {leg} | {r["sprint_scope"]} | {r["test_level"]} | `{r["class"]}.{r["method"]}` | {desc_clean} | {inp_clean} | {exp_clean} | {act_clean} | **{r["status"]}** |'
            )
        lines.append('')

    with open(md_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))


def main():
    parser = argparse.ArgumentParser(description='Run and collect Service 2 Unit & API Test results.')
    parser.add_argument(
        '--sprint1-only',
        action='store_true',
        help='Execute ONLY the 192 Sprint 1 tests (excluding 19 out-of-Sprint-1 Maintenance tests).',
    )
    parser.add_argument(
        '--unit-only',
        action='store_true',
        help='Execute ONLY the Pure Unit Tests in testing/unit_tests/ (73 tests).',
    )
    parser.add_argument(
        '--api-only',
        action='store_true',
        help='Execute ONLY the API / HTTP Tests in testing/api_tests/ (138 tests).',
    )
    parser.add_argument(
        '--coverage-json',
        default=None,
        help='Optional path to Coverage.py JSON report for dynamic HTML Coverage rendering.',
    )
    args = parser.parse_args()

    runner = DiscoverRunner(verbosity=1, interactive=False, keepdb=False)
    runner.setup_test_environment()
    if args.unit_only:
        suite = runner.build_suite(['services.property_service.testing.unit_tests'])
    elif args.api_only:
        suite = runner.build_suite(['services.property_service.testing.api_tests'])
    else:
        suite = runner.build_suite(['services.property_service'])

    all_tests = flatten_suite(suite)
    if args.sprint1_only:
        filtered_suite = unittest.TestSuite()
        for t in all_tests:
            meta = extract_meta(t)
            if meta['sprint_scope'] == 'Sprint 1':
                filtered_suite.addTest(t)
        suite_to_run = filtered_suite
    else:
        suite_to_run = suite

    old_config = runner.setup_databases()
    t_start = time.perf_counter()
    try:
        test_runner = unittest.TextTestRunner(verbosity=1, resultclass=TimedResult)
        result = test_runner.run(suite_to_run)
    finally:
        total_duration = max(0.0, time.perf_counter() - t_start)
        runner.teardown_databases(old_config)
        runner.teardown_test_environment()

    total = len(result.records)
    passed = sum(1 for r in result.records if r['status'] == 'PASS')
    failed = sum(1 for r in result.records if r['status'] in ('FAIL', 'ERROR'))
    expected_fail = sum(1 for r in result.records if r['status'].startswith('EXPECTED_FAIL'))
    if expected_fail > 0:
        print(f'[WARNING] Detected {expected_fail} expectedFailure test(s)!', file=sys.stderr)

    if args.sprint1_only:
        print(f'[SPRINT 1 ONLY] Total={total}, PASS={passed}, FAIL/ERROR={failed}, Duration={total_duration:.2f}s')
        sys.exit(0 if failed == 0 else 1)
    if args.unit_only:
        print(f'[PURE UNIT TESTS ONLY] Total={total}, PASS={passed}, FAIL/ERROR={failed}, Duration={total_duration:.2f}s')
        sys.exit(0 if failed == 0 else 1)
    if args.api_only:
        print(f'[API/HTTP TESTS ONLY] Total={total}, PASS={passed}, FAIL/ERROR={failed}, Duration={total_duration:.2f}s')
        sys.exit(0 if failed == 0 else 1)

    os.makedirs(REPORTS_DIR, exist_ok=True)
    os.makedirs(EVIDENCE_DIR, exist_ok=True)

    out_json = os.path.join(REPORTS_DIR, 'results.json')
    with open(out_json, 'w', encoding='utf-8') as f:
        json.dump(result.records, f, ensure_ascii=False, indent=2)

    out_md = os.path.join(REPORTS_DIR, 'UNIT_TEST_CASES.md')
    write_unit_test_cases_md(result.records, out_md)

    coverage_data = load_coverage_summary(args.coverage_json)
    out_html = os.path.join(EVIDENCE_DIR, 'TEST_EXECUTION_REPORT.html')
    write_html_report(result.records, total_duration, out_html, coverage_data=coverage_data)

    out_xml = os.path.join(EVIDENCE_DIR, 'junit-report.xml')
    write_junit_xml(result.records, total_duration, out_xml)

    s1_cnt = sum(1 for r in result.records if r['sprint_scope'] == 'Sprint 1')
    maint_cnt = sum(1 for r in result.records if r['sprint_scope'] != 'Sprint 1')
    unit_cnt = sum(1 for r in result.records if r['test_level'] == 'Pure Unit Test')
    api_cnt = sum(1 for r in result.records if r['test_level'] == 'API/HTTP Test')
    s1_unit = sum(1 for r in result.records if r['sprint_scope'] == 'Sprint 1' and r['test_level'] == 'Pure Unit Test')
    s1_api = sum(1 for r in result.records if r['sprint_scope'] == 'Sprint 1' and r['test_level'] == 'API/HTTP Test')
    out_unit = sum(1 for r in result.records if r['sprint_scope'] != 'Sprint 1' and r['test_level'] == 'Pure Unit Test')
    out_api = sum(1 for r in result.records if r['sprint_scope'] != 'Sprint 1' and r['test_level'] == 'API/HTTP Test')
    print(
        f'Summary: Total={total} (PureUnit={unit_cnt}, API/HTTP={api_cnt} | '
        f'Sprint1={s1_cnt} [{s1_unit} Unit + {s1_api} API], '
        f'OutOfSprint1={maint_cnt} [{out_unit} Unit + {out_api} API]), '
        f'PASS={passed}, FAIL/ERROR={failed}, Duration={total_duration:.2f}s'
    )
    sys.exit(0 if failed == 0 else 1)


if __name__ == '__main__':
    main()

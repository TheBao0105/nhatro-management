"""
API / HTTP Pipeline Tests for Maintenance workflows (Out-of-Sprint-1 Pre-Sprint 2 QA).

Migrated from `backend/services/property_service/tests.py` (Option A):
- S2-MAPI-001 (Legacy S2-LEG-018): Full Maintenance HTTP workflow & history endpoints.
- S2-MAPI-002 (Legacy S2-LEG-019): Maintenance start & complete restores previous OCCUPIED room status.
- S2-MAPI-003 (Legacy S2-LEG-020): Create maintenance with set_room_maintenance=False keeps room AVAILABLE.
- S2-MAPI-004 (Legacy S2-LEG-021): Tenant can report and cancel own maintenance request, but cannot manage (403).
"""
from django.test import TestCase, override_settings
from rest_framework import status

from common.testing import jwt_client, patch_tenant_links, tenant_link
from services.property_service.models import (
    MaintenanceStatus,
    Property,
    PropertyStatus,
    Room,
    RoomStatus,
)

LANDLORD_ID = 101


class MaintenanceAPIPipelineTests(TestCase):
    """HTTP pipeline tests for Maintenance endpoints when SPRINT_FEATURE_LOCK is disabled."""

    def setUp(self):
        self.client = jwt_client(LANDLORD_ID, 'LANDLORD')
        self.property = Property.objects.create(
            code='NT100',
            owner_id=LANDLORD_ID,
            name='Nhà trọ Thử Nghiệm',
            address='123 Đường Nguyễn Gia Trí',
            ward='Phường 25',
            district='Bình Thạnh',
            city='TP. Hồ Chí Minh',
            total_floors=2,
            status=PropertyStatus.ACTIVE,
        )
        self.room = Room.objects.create(
            code='NT100-A01',
            property=self.property,
            room_number='101',
            floor=1,
            area=20.0,
            rent_price=3000000,
            deposit_amount=3000000,
            max_occupants=2,
            status=RoomStatus.AVAILABLE,
        )

    @override_settings(SPRINT_FEATURE_LOCK=False)
    def test_maintenance_workflow_and_history(self):
        """S2-MAPI-001: [Ngoài Sprint 1] [Legacy S2-LEG-018] Luồng HTTP đầy đủ POST /api/maintenance/ -> update_status -> record_cost -> complete -> cancel (400) -> history"""
        res = self.client.post('/api/maintenance/', {
            'room': self.room.id, 'title': 'Phòng 101 hỏng điều hòa', 'estimated_cost': 500000,
            'priority': 'HIGH',
        }, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED, res.data)
        maint_id = res.data['id']
        self.assertEqual(res.data['reported_by_id'], LANDLORD_ID)
        self.room.refresh_from_db()
        self.assertEqual(self.room.status, RoomStatus.MAINTENANCE)

        res = self.client.post(f'/api/maintenance/{maint_id}/update_status/', {'status': 'IN_PROGRESS'},
                               format='json')
        self.assertEqual(res.data['maintenance_request']['status'], MaintenanceStatus.IN_PROGRESS)

        res = self.client.post(f'/api/maintenance/{maint_id}/record_cost/',
                               {'estimated_cost': 500000, 'actual_cost': 450000}, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        res = self.client.post(f'/api/maintenance/{maint_id}/complete/',
                               {'repair_info': 'Đã sửa xong điều hòa'}, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['maintenance_request']['status'], MaintenanceStatus.COMPLETED)
        self.room.refresh_from_db()
        self.assertEqual(self.room.status, RoomStatus.AVAILABLE)

        res = self.client.post(f'/api/maintenance/{maint_id}/cancel/')
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

        res = self.client.get('/api/maintenance-history/')
        self.assertGreaterEqual(len(res.data), 4)
        res = self.client.get(f'/api/maintenance/{maint_id}/history/')
        self.assertGreaterEqual(len(res.data), 4)

    @override_settings(SPRINT_FEATURE_LOCK=False)
    def test_maintenance_start_complete_restores_previous_status(self):
        """S2-MAPI-002: [Ngoài Sprint 1] [Legacy S2-LEG-019] HTTP POST /start/ và /complete/ khôi phục trạng thái phòng OCCUPIED ban đầu"""
        self.room.status = RoomStatus.OCCUPIED
        self.room.current_occupants = 1
        self.room.save()
        res = self.client.post('/api/maintenance/', {
            'room': self.room.id, 'title': 'Hỏng máy lạnh', 'mark_room_maintenance': True}, format='json')
        req_id = res.data['id']
        self.room.refresh_from_db()
        self.assertEqual(self.room.status, RoomStatus.MAINTENANCE)
        res = self.client.post(f'/api/maintenance/{req_id}/start/', {'assigned_to': 'Thợ A'}, format='json')
        self.assertEqual(res.data['maintenance_request']['technician_name'], 'Thợ A')
        res = self.client.post(f'/api/maintenance/{req_id}/complete/', {'cost': '350000'}, format='json')
        self.assertEqual(res.data['maintenance_request']['actual_cost'], '350000')
        self.room.refresh_from_db()
        self.assertEqual(self.room.status, RoomStatus.OCCUPIED)

    @override_settings(SPRINT_FEATURE_LOCK=False)
    def test_create_maintenance_without_locking_room(self):
        """S2-MAPI-003: [Ngoài Sprint 1] [Legacy S2-LEG-020] HTTP POST /api/maintenance/ với set_room_maintenance=False giữ phòng ở trạng thái AVAILABLE"""
        res = self.client.post('/api/maintenance/', {
            'room': self.room.id, 'title': 'Thay bóng đèn', 'set_room_maintenance': False}, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.room.refresh_from_db()
        self.assertEqual(self.room.status, RoomStatus.AVAILABLE)

    @override_settings(SPRINT_FEATURE_LOCK=False)
    def test_tenant_can_report_but_not_manage_maintenance(self):
        """S2-MAPI-004: [Ngoài Sprint 1] [Legacy S2-LEG-021] TENANT tạo và hủy được yêu cầu bảo trì của mình nhưng bị chặn 403 trên complete/start/record_cost/update_status"""
        patcher = patch_tenant_links({777: [tenant_link(1, 777, room_id=self.room.id, landlord_id=LANDLORD_ID)]})
        patcher.start()
        self.addCleanup(patcher.stop)
        tenant = jwt_client(777, 'TENANT')
        res = tenant.post('/api/maintenance/', {'room': self.room.id, 'title': 'Rò nước'}, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        req_id = res.data['id']
        self.room.refresh_from_db()
        self.assertEqual(self.room.status, RoomStatus.AVAILABLE)
        for path in ('complete', 'start', 'record_cost', 'update_status'):
            res = tenant.post(f'/api/maintenance/{req_id}/{path}/', {'status': 'COMPLETED'}, format='json')
            self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN, path)
        self.assertEqual(len(tenant.get('/api/maintenance/').data), 1)
        self.assertEqual(len(jwt_client(778, 'TENANT').get('/api/maintenance/').data), 0)
        self.assertEqual(len(jwt_client(778, 'TENANT').get('/api/maintenance-history/').data), 0)
        res = tenant.post(f'/api/maintenance/{req_id}/cancel/')
        self.assertEqual(res.status_code, status.HTTP_200_OK)

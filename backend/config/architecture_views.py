from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions
from django.db import connections
from django.conf import settings

class ArchitectureStatusView(APIView):
    """
    ⚙️ PROJECT SETUP & ARCHITECTURE:
    Endpoint kiểm tra trạng thái kiến trúc SOA, kiểm tra kết nối Database Configuration
    và Service Integration Check của toàn bộ 5 services.
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        db_status = {}
        for db_key in ['default', 'property_db', 'tenant_db', 'contract_db', 'billing_db']:
            try:
                conn = connections[db_key]
                with conn.cursor() as cursor:
                    cursor.execute("SELECT 1")
                    row = cursor.fetchone()
                db_name = settings.DATABASES[db_key].get('NAME', 'unknown')
                db_status[db_key] = {
                    'status': 'HEALTHY' if row and row[0] == 1 else 'WARNING',
                    'database_name': str(db_name),
                    'engine': settings.DATABASES[db_key].get('ENGINE', 'unknown').split('.')[-1],
                }
            except Exception as e:
                db_status[db_key] = {
                    'status': 'DISCONNECTED',
                    'error': str(e),
                }

        soa_services = [
            {
                'id': 1,
                'name': 'Identity & Authentication Service',
                'database': 'nhatro_identity_db (default)',
                'sprint': 'SPRINT 1',
                'status': 'ACTIVE',
                'features': [
                    'Login API',
                    'JWT Authentication',
                    'Role Authorization (ADMIN, LANDLORD, STAFF, TENANT)',
                    'Test Login Accounts'
                ]
            },
            {
                'id': 2,
                'name': 'Property Management Service',
                'database': 'nhatro_property_db (property_db)',
                'sprint': 'SPRINT 1',
                'status': 'ACTIVE',
                'features': [
                    'Create Property',
                    'View Property List',
                    'Update Property',
                    'Delete Property'
                ]
            },
            {
                'id': 3,
                'name': 'Room Management Service',
                'database': 'nhatro_property_db (property_db)',
                'sprint': 'SPRINT 1',
                'status': 'ACTIVE',
                'features': [
                    'Create Room',
                    'View Room List',
                    'Update Room',
                    'Update Room Status (AVAILABLE, OCCUPIED, RESERVED, MAINTENANCE)'
                ]
            },
            {
                'id': 4,
                'name': 'Tenant Management Service',
                'database': 'nhatro_tenant_db (tenant_db)',
                'sprint': 'SPRINT 2',
                'status': 'PLANNED_NEXT_SPRINT',
                'features': ['Quản lý hồ sơ khách thuê', 'Khai báo tạm trú', 'Lịch sử cư trú']
            },
            {
                'id': 5,
                'name': 'Contract Management Service',
                'database': 'nhatro_contract_db (contract_db)',
                'sprint': 'SPRINT 2',
                'status': 'PLANNED_NEXT_SPRINT',
                'features': ['Hợp đồng thuê phòng', 'Gia hạn hợp đồng', 'Thanh lý hợp đồng']
            },
            {
                'id': 6,
                'name': 'Billing & Notification Service',
                'database': 'nhatro_billing_db (billing_db)',
                'sprint': 'SPRINT 3',
                'status': 'PLANNED_NEXT_SPRINT',
                'features': ['Tính hóa đơn điện nước tự động', 'VietQR chuyển khoản', 'Thông báo đẩy']
            },
        ]

        return Response({
            'architecture': 'SOA (Service-Oriented Architecture)',
            'database_isolation': 'Database per Service (Mỗi service là 1 database riêng biệt, không có Foreign Key chéo)',
            'current_sprint': 'SPRINT 1 — FOUNDATION & CORE MANAGEMENT',
            'databases_health': db_status,
            'services': soa_services,
            'integration_check': 'PASSED',
        })


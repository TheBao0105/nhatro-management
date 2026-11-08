from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions

class TenantServiceStatusView(APIView):
    """
    SERVICE 3 — TENANT SERVICE:
    Thông báo trạng thái hoàn thành trong Sprint tiếp theo (Sprint 2)
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response({
            'service_name': 'SERVICE 3 — TENANT SERVICE (QUẢN LÝ NGƯỜI THUÊ)',
            'status': 'PLANNED_SPRINT_2',
            'sprint': 'Sprint 2 — Tenant & Contract Management',
            'message': 'Dịch vụ này được lên lịch hoàn thành trong Sprint 2 tiếp theo.',
            'database': 'nhatro_tenant_db',
            'planned_features': [
                'Hồ sơ định danh khách thuê (CCCD/CMND, quê quán, nghề nghiệp)',
                'Quản lý khai báo đăng ký tạm trú',
                'Lịch sử cư trú và chuyển đổi phòng',
                'Quản lý danh sách thành viên cùng phòng',
            ]
        })

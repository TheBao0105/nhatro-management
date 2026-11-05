from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions

class TenantServiceStatusView(APIView):
    """
    SERVICE 3 — TENANT SERVICE: Endpoint giới thiệu dịch vụ (Dành cho Sprint 2)
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response({
            'service': 'SERVICE 3 — TENANT SERVICE',
            'status': 'READY_FOR_SPRINT_2',
            'sprint': 'Sprint 2 — Tenant & Contract',
            'planned_features': [
                'Quản lý danh sách khách thuê',
                'Quản lý thông tin tạm trú, CCCD',
                'Lịch sử cư trú và đổi phòng',
                'Ghi nhận liên hệ khẩn cấp',
            ]
        })


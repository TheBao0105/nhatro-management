from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions

class ContractServiceStatusView(APIView):
    """
    SERVICE 4 — CONTRACT SERVICE: Endpoint giới thiệu dịch vụ (Dành cho Sprint 2)
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response({
            'service': 'SERVICE 4 — CONTRACT SERVICE',
            'status': 'READY_FOR_SPRINT_2',
            'sprint': 'Sprint 2 — Tenant & Contract',
            'planned_features': [
                'Tạo hợp đồng thuê phòng',
                'Gia hạn hợp đồng (Extension)',
                'Kết thúc / Thanh lý hợp đồng (Termination) & Hoàn cọc',
                'Xuất PDF và ký số hợp đồng',
            ]
        })


from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions

class ContractServiceStatusView(APIView):
    """
    SERVICE 4 — CONTRACT SERVICE:
    Thông báo trạng thái hoàn thành trong Sprint tiếp theo (Sprint 2)
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response({
            'service_name': 'SERVICE 4 — CONTRACT SERVICE (QUẢN LÝ HỢP ĐỒNG)',
            'status': 'PLANNED_SPRINT_2',
            'sprint': 'Sprint 2 — Tenant & Contract Management',
            'message': 'Dịch vụ này được lên lịch hoàn thành trong Sprint 2 tiếp theo.',
            'database': 'nhatro_contract_db',
            'planned_features': [
                'Tạo lập hợp đồng điện tử theo mẫu pháp lý chuẩn',
                'Quản lý gia hạn hợp đồng (Contract Extension)',
                'Thanh lý hợp đồng và hoàn trả cọc',
                'Xuất file PDF hợp đồng & Chữ ký điện tử',
            ]
        })

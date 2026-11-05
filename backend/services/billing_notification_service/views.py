from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions

class BillingServiceStatusView(APIView):
    """
    SERVICE 5 — BILLING & NOTIFICATION SERVICE: Giới thiệu dịch vụ
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response({
            'service': 'SERVICE 5 — BILLING & NOTIFICATION SERVICE',
            'status': 'READY_FOR_SPRINT_3',
            'sprint': 'Sprint 3 — Billing, Payments & Notification',
            'planned_features': [
                'Tính hóa đơn tiền phòng, tiền điện, tiền nước tự động',
                'Quản lý trạng thái thanh toán (Chưa trả, Đã thanh toán, Quá hạn)',
                'Tạo mã QR VietQR chuyển khoản ngân hàng tự động',
                'Gửi thông báo đẩy và email nhắc hạn đóng tiền',
            ]
        })


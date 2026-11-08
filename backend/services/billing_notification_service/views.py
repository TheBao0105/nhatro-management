from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions

class BillingServiceStatusView(APIView):
    """
    SERVICE 5 — BILLING & NOTIFICATION SERVICE:
    Thông báo trạng thái hoàn thành trong Sprint tiếp theo (Sprint 3)
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response({
            'service_name': 'SERVICE 5 — BILLING & NOTIFICATION SERVICE',
            'status': 'PLANNED_SPRINT_3',
            'sprint': 'Sprint 3 — Billing, Payments & Notification',
            'message': 'Dịch vụ này được lên lịch hoàn thành trong Sprint 3 tiếp theo.',
            'database': 'nhatro_billing_db',
            'planned_features': [
                'Tính tiền điện, nước tự động theo chỉ số công tơ tháng',
                'Tạo mã thanh toán VietQR ngân hàng kèm nội dung tự động',
                'Quản lý trạng thái phiếu thu / hóa đơn (Chưa thanh toán, Đã thanh toán, Quá hạn)',
                'Gửi thông báo nhắc tiền phòng qua Email / App Push Notification',
            ]
        })

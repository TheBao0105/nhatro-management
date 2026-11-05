from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Count, Q
from .models import Property, Room, RoomStatus, MaintenanceRequest
from .serializers import PropertySerializer, RoomSerializer, MaintenanceRequestSerializer
from services.identity_service.models import UserRole
from services.identity_service.permissions import IsLandlordOrAdmin

class PropertyViewSet(viewsets.ModelViewSet):
    """
    SERVICE 2: Quản lý Danh sách và Thông tin chi tiết Nhà trọ
    """
    serializer_class = PropertySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        queryset = Property.objects.all().prefetch_related('rooms')

        # Phân quyền: Landlord chỉ thấy nhà trọ của mình, Admin thấy toàn bộ
        if user.role == UserRole.LANDLORD and not user.is_superuser:
            queryset = queryset.filter(landlord=user)

        # Bộ lọc tìm kiếm
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) | 
                Q(address__icontains=search) | 
                Q(district__icontains=search)
            )

        return queryset

    @action(detail=True, methods=['get'], url_path='rooms')
    def rooms(self, request, pk=None):
        """
        Lấy danh sách toàn bộ phòng thuộc về nhà trọ này
        """
        property_obj = self.get_object()
        status_filter = request.query_params.get('status')
        rooms = property_obj.rooms.all()
        if status_filter:
            rooms = rooms.filter(status=status_filter)
        serializer = RoomSerializer(rooms, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'], url_path='stats')
    def stats(self, request, pk=None):
        """
        Thống kê tổng quan tỷ lệ phòng trống / đang thuê của nhà trọ
        """
        property_obj = self.get_object()
        total = property_obj.rooms.count()
        available = property_obj.rooms.filter(status=RoomStatus.AVAILABLE).count()
        occupied = property_obj.rooms.filter(status=RoomStatus.OCCUPIED).count()
        maintenance = property_obj.rooms.filter(status=RoomStatus.MAINTENANCE).count()
        reserved = property_obj.rooms.filter(status=RoomStatus.RESERVED).count()
        occupancy_rate = round((occupied / total * 100), 1) if total > 0 else 0.0

        return Response({
            'property_id': property_obj.id,
            'property_name': property_obj.name,
            'total_rooms': total,
            'available_rooms': available,
            'occupied_rooms': occupied,
            'maintenance_rooms': maintenance,
            'reserved_rooms': reserved,
            'occupancy_rate_percent': occupancy_rate,
        })


class RoomViewSet(viewsets.ModelViewSet):
    """
    SERVICE 2: Quản lý Phòng trọ (Thêm, sửa, xóa, lọc theo trạng thái)
    """
    serializer_class = RoomSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        queryset = Room.objects.select_related('property').all()

        if user.role == UserRole.LANDLORD and not user.is_superuser:
            queryset = queryset.filter(property__landlord=user)

        # Filters
        property_id = self.request.query_params.get('property_id')
        if property_id:
            queryset = queryset.filter(property_id=property_id)

        status_param = self.request.query_params.get('status')
        if status_param:
            queryset = queryset.filter(status=status_param)

        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(room_number__icontains=search)

        return queryset

    @action(detail=True, methods=['patch'], url_path='status')
    def update_status(self, request, pk=None):
        """
        Cập nhật nhanh trạng thái phòng (AVAILABLE / OCCUPIED / MAINTENANCE / RESERVED)
        """
        room = self.get_object()
        new_status = request.data.get('status')
        if new_status not in RoomStatus.values:
            return Response(
                {'error': f'Trạng thái không hợp lệ. Các giá trị được phép: {RoomStatus.values}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        room.status = new_status
        room.save()
        return Response(RoomSerializer(room).data)


class MaintenanceRequestViewSet(viewsets.ModelViewSet):
    """
    SERVICE 2: Quản lý Yêu cầu bảo trì / sửa chữa
    """
    serializer_class = MaintenanceRequestSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        queryset = MaintenanceRequest.objects.select_related('property', 'room', 'reported_by').all()

        if user.role == UserRole.LANDLORD and not user.is_superuser:
            queryset = queryset.filter(property__landlord=user)
        elif user.role == UserRole.TENANT:
            queryset = queryset.filter(reported_by=user)

        property_id = self.request.query_params.get('property_id')
        if property_id:
            queryset = queryset.filter(property_id=property_id)

        return queryset


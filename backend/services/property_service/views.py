from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q
from .models import Property, Room, RoomStatus
from .serializers import PropertySerializer, RoomSerializer

class PropertyViewSet(viewsets.ModelViewSet):
    """
    SPRINT 1 — PROPERTY MANAGEMENT:
    - Create Property
    - View Property List
    - Update Property
    - Delete Property
    - Thống kê tỷ lệ phòng (Stats) & Lấy danh sách phòng theo nhà trọ
    """
    serializer_class = PropertySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        queryset = Property.objects.all().prefetch_related('rooms')

        # Phân quyền SOA:
        # Nếu là LANDLORD, chỉ lấy nhà trọ do chính user đó sở hữu (owner_id)
        # Nếu là ADMIN hoặc superuser, xem toàn bộ hệ thống
        if hasattr(user, 'role') and user.role == 'LANDLORD' and not user.is_superuser:
            queryset = queryset.filter(owner_id=user.id)
        elif not user.is_superuser and getattr(user, 'role', '') not in ('ADMIN', 'STAFF'):
            # Khách thuê bình thường chỉ xem danh sách các nhà trọ có phòng trống
            queryset = queryset.filter(rooms__status=RoomStatus.AVAILABLE).distinct()

        # Tìm kiếm theo tên hoặc địa chỉ
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
        if status_filter and status_filter != 'ALL':
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
    SPRINT 1 — ROOM MANAGEMENT:
    - Create Room
    - View Room List
    - Update Room
    - Update Room Status (PATCH /status/)
    - Delete Room
    """
    serializer_class = RoomSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        queryset = Room.objects.select_related('property').all()

        # Phân quyền: Landlord chỉ quản lý phòng thuộc nhà trọ của mình
        if hasattr(user, 'role') and user.role == 'LANDLORD' and not user.is_superuser:
            queryset = queryset.filter(property__owner_id=user.id)

        # Bộ lọc theo property_id
        property_id = self.request.query_params.get('property_id')
        if property_id:
            queryset = queryset.filter(property_id=property_id)

        # Bộ lọc theo trạng thái phòng
        status_param = self.request.query_params.get('status')
        if status_param and status_param != 'ALL':
            queryset = queryset.filter(status=status_param)

        # Tìm kiếm theo số phòng
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
                {
                    'error': f'Trạng thái không hợp lệ. Các giá trị được phép: {RoomStatus.values}',
                    'allowed_statuses': RoomStatus.values
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        room.status = new_status
        room.save(update_fields=['status', 'updated_at'])
        return Response(RoomSerializer(room).data)

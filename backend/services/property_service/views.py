from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.db.models import Count, Q, Sum
from django.utils import timezone
from rest_framework import permissions, serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from common.auth import (
    IsManagerOrReadOnly, IsManagerRole, get_user_id, is_admin, is_landlord, is_manager,
)
from common.service_client import own_rented_room_ids, room_external_block_reason
from common.sprint import SprintFeatureLock
from .models import (
    RENTED_STATUSES,
    MaintenanceHistory,
    MaintenanceRequest,
    MaintenanceStatus,
    Property,
    PropertyStatus,
    Room,
    RoomStatus,
)
from .serializers import (
    MaintenanceHistorySerializer,
    MaintenanceRequestSerializer,
    PropertySerializer,
    RoomSerializer,
)


# ==============================================================================
# HELPERS
# ==============================================================================
def _actor_name(user):
    if not user or not user.is_authenticated:
        return 'Hệ thống'
    return getattr(user, 'full_name', '') or getattr(user, 'username', '') or f'User #{user.id}'


def _parse_decimal(value, field='detail'):
    """Chuyển tham số số (query/body) sang Decimal; giá trị sai -> 400 thay vì 500."""
    if value in (None, ''):
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        raise serializers.ValidationError({field: f'Giá trị số không hợp lệ: {value}'})


def _parse_number(value, cast, field):
    if value in (None, '', 'ALL'):
        return None
    try:
        return cast(value)
    except (TypeError, ValueError):
        raise serializers.ValidationError({field: f'Giá trị không hợp lệ: {value}'})


def scoped_properties(user):
    """
    Phân quyền dữ liệu nhà trọ dựa trên claims JWT (Identity Service):
    - ADMIN    : toàn bộ hệ thống
    - LANDLORD : nhà trọ mình sở hữu (owner_id)
    - TENANT (và STAFF legacy): chỉ nhà trọ chứa phòng mình ĐANG thuê
      (room_id lấy từ Tenant Service theo user_id trong JWT; không xác định được -> 503, không trả dữ liệu).
    """
    queryset = Property.objects.all()
    if is_admin(user):
        return queryset
    if is_landlord(user):
        return queryset.filter(owner_id=get_user_id(user))
    return queryset.filter(rooms__id__in=own_rented_room_ids(user)).distinct()


def scoped_rooms(user):
    queryset = Room.objects.select_related('property')
    if is_admin(user):
        return queryset
    if is_landlord(user):
        return queryset.filter(property__owner_id=get_user_id(user))
    # TENANT: chỉ phòng mình đang thuê (không còn xem toàn bộ phòng như chức năng tìm phòng).
    return queryset.filter(id__in=own_rented_room_ids(user))


def scoped_maintenance(user):
    queryset = MaintenanceRequest.objects.select_related('room', 'room__property')
    if is_admin(user):
        return queryset
    if is_landlord(user):
        return queryset.filter(room__property__owner_id=get_user_id(user))
    return queryset.filter(reported_by_id=get_user_id(user))


def _room_status_after_maintenance(req, requested=None):
    """Trạng thái phòng khi kết thúc bảo trì: theo yêu cầu > trạng thái trước bảo trì > theo số người ở."""
    room = req.room
    if requested:
        requested = requested.upper()
        if requested not in RoomStatus.values:
            raise serializers.ValidationError(
                {'room_status': f'Trạng thái phòng không hợp lệ. Chọn một trong: {RoomStatus.values}'})
        return requested
    if req.previous_room_status and req.previous_room_status != RoomStatus.MAINTENANCE:
        return req.previous_room_status
    return RoomStatus.AVAILABLE if room.current_occupants == 0 else RoomStatus.OCCUPIED


# ==============================================================================
# I. MODULE PROPERTY — QUẢN LÝ NHÀ TRỌ
# ==============================================================================
class PropertyViewSet(viewsets.ModelViewSet):
    """
    I. MODULE PROPERTY — QUẢN LÝ NHÀ TRỌ (qua Gateway: /api/properties/ hoặc /api/v1/properties/):
    1.1 Thêm nhà trọ (POST)
    1.2 Xem danh sách nhà trọ (GET)
    1.3 Xem chi tiết nhà trọ (GET /{id}/)
    1.4 Cập nhật thông tin nhà trọ (PUT/PATCH /{id}/)
    1.5 Xóa / Ngừng hoạt động nhà trọ (Soft Delete: ACTIVE / INACTIVE / DELETED)
    1.6 Tìm kiếm nhà trọ (?search= theo Tên, Mã, Địa chỉ, Khu vực)
    1.7 Lọc nhà trọ (?status=ACTIVE|INACTIVE|DELETED, ?district=, ?ward=)
    - /{id}/rooms/, /{id}/stats/, /{id}/room_matrix/
    - /summary/  thống kê tổng hợp theo phạm vi user (Dashboard qua Gateway)
    Ghi (POST/PUT/PATCH/DELETE) chỉ dành cho ADMIN/LANDLORD.
    """
    serializer_class = PropertySerializer
    permission_classes = [IsManagerOrReadOnly]

    def get_queryset(self):
        queryset = scoped_properties(self.request.user).prefetch_related('rooms')
        params = self.request.query_params

        # 1.7 Lọc theo trạng thái hoạt động (chỉ áp dụng cho list nhà trọ; action rooms dùng ?status= để lọc phòng)
        status_param = params.get('status')
        include_deleted = params.get('include_deleted') == 'true'
        if self.action == 'list' and status_param and status_param != 'ALL':
            queryset = queryset.filter(status=status_param.upper())
        elif not include_deleted and self.action == 'list' and status_param != 'ALL':
            queryset = queryset.exclude(status=PropertyStatus.DELETED)

        # 1.7 Lọc theo khu vực
        district = params.get('district')
        if district and district != 'ALL':
            queryset = queryset.filter(district__icontains=district.strip())

        ward = params.get('ward')
        if ward and ward != 'ALL':
            queryset = queryset.filter(ward__icontains=ward.strip())

        # 1.6 Tìm kiếm nhà trọ (Tên, Mã, Địa chỉ, Khu vực)
        search = params.get('search')
        if search:
            q = search.strip()
            queryset = queryset.filter(
                Q(name__icontains=q)
                | Q(code__icontains=q)
                | Q(address__icontains=q)
                | Q(ward__icontains=q)
                | Q(district__icontains=q)
                | Q(city__icontains=q)
            )

        return queryset

    def _room_data(self, rooms):
        return RoomSerializer(rooms, many=True, context=self.get_serializer_context()).data

    @staticmethod
    def _active_rooms_block_response(prop):
        """Chặn xóa nhà trọ khi còn phòng đang hoạt động (mọi trạng thái khác INACTIVE)."""
        active = prop.rooms.exclude(status=RoomStatus.INACTIVE)
        active_count = active.count()
        if active_count == 0:
            return None
        rented = active.filter(status__in=RENTED_STATUSES).count()
        detail = f' (trong đó {rented} phòng đang thuê)' if rented else ''
        return Response(
            {
                'error': f'Nhà trọ "{prop.name}" còn {active_count} phòng đang hoạt động{detail}. '
                         f'Hãy chuyển các phòng sang INACTIVE hoặc xóa phòng trước khi xóa nhà trọ.'
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    def destroy(self, request, *args, **kwargs):
        """
        1.5 Soft Delete nhà trọ:
        Chỉ cho xóa khi không còn phòng hoạt động. Nếu còn phòng INACTIVE (dữ liệu lịch sử),
        chuyển sang DELETED thay vì xóa cứng.
        """
        prop = self.get_object()
        blocked = self._active_rooms_block_response(prop)
        if blocked:
            return blocked

        if prop.rooms.exists():
            prop.status = PropertyStatus.DELETED
            prop.save(update_fields=['status', 'updated_at'])
            return Response({
                'message': f'Nhà trọ "{prop.name}" đang có {prop.rooms.count()} phòng nên đã được chuyển sang trạng thái '
                           f'DELETED (Soft Delete) để bảo toàn dữ liệu lịch sử.',
                'soft_deleted': True,
                'property': self.get_serializer(prop).data,
            })

        prop_name = prop.name
        prop.delete()
        return Response({'message': f'Đã xóa nhà trọ "{prop_name}" thành công.', 'soft_deleted': False})

    @action(detail=True, methods=['post', 'patch'], url_path='update_status')
    def update_status(self, request, pk=None):
        """1.5 Đổi nhanh trạng thái nhà trọ: ACTIVE / INACTIVE / DELETED."""
        prop = self.get_object()
        new_status = (request.data.get('status') or '').upper()
        if new_status not in PropertyStatus.values:
            return Response(
                {'error': f'Trạng thái không hợp lệ. Chọn một trong: {PropertyStatus.values}'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if new_status == PropertyStatus.DELETED:
            blocked = self._active_rooms_block_response(prop)
            if blocked:
                return blocked
        prop.status = new_status
        prop.save(update_fields=['status', 'updated_at'])
        return Response({
            'message': f'Đã cập nhật trạng thái nhà trọ "{prop.name}" thành {prop.get_status_display()}.',
            'property': self.get_serializer(prop).data,
        })

    @action(detail=True, methods=['get'], url_path='rooms')
    def rooms(self, request, pk=None):
        property_obj = self.get_object()
        rooms = scoped_rooms(request.user).filter(property=property_obj)
        status_filter = request.query_params.get('status')
        if status_filter and status_filter != 'ALL':
            rooms = rooms.filter(status=status_filter.upper())
        return Response(self._room_data(rooms))

    @action(detail=True, methods=['get'], url_path='stats', permission_classes=[IsManagerRole])
    def stats(self, request, pk=None):
        """Thống kê một nhà trọ (doanh thu, tỉ lệ lấp đầy) — chỉ ADMIN/LANDLORD."""
        property_obj = self.get_object()
        rooms = property_obj.rooms.all()
        counts = {row['status']: row['n'] for row in rooms.values('status').annotate(n=Count('id'))}
        total = sum(counts.values())
        occupied = counts.get(RoomStatus.OCCUPIED, 0)
        full = counts.get(RoomStatus.FULL, 0)
        rented_total = occupied + full
        occupancy_rate = round((rented_total / total * 100), 1) if total > 0 else 0.0
        monthly_revenue = rooms.filter(status__in=RENTED_STATUSES).aggregate(s=Sum('rent_price'))['s'] or 0

        return Response({
            'property_id': property_obj.id,
            'property_code': property_obj.code,
            'property_name': property_obj.name,
            'status': property_obj.status,
            'total_rooms': total,
            'available_rooms': counts.get(RoomStatus.AVAILABLE, 0),
            'occupied_rooms': occupied,
            'full_rooms': full,
            'reserved_rooms': counts.get(RoomStatus.RESERVED, 0),
            'maintenance_rooms': counts.get(RoomStatus.MAINTENANCE, 0),
            'inactive_rooms': counts.get(RoomStatus.INACTIVE, 0),
            'occupancy_rate_percent': occupancy_rate,
            'estimated_monthly_revenue': monthly_revenue,
        })

    @action(detail=True, methods=['get'], url_path='room_matrix')
    def room_matrix(self, request, pk=None):
        property_obj = self.get_object()
        rooms = scoped_rooms(request.user).filter(property=property_obj).order_by('floor', 'room_number')
        status_summary = {value: 0 for value in RoomStatus.values}
        matrix_by_floor = {}
        for room, data in zip(rooms, self._room_data(rooms)):
            status_summary[room.status] = status_summary.get(room.status, 0) + 1
            matrix_by_floor.setdefault(room.floor, []).append(data)

        floors_list = [
            {
                'floor_name': f'Tầng {floor}',
                'rooms_count': len(matrix_by_floor[floor]),
                'rooms': matrix_by_floor[floor],
            }
            for floor in sorted(matrix_by_floor.keys())
        ]

        return Response({
            'property_id': property_obj.id,
            'property_code': property_obj.code,
            'property_name': property_obj.name,
            'total_floors': property_obj.total_floors,
            'total_rooms': sum(status_summary.values()),
            'status_summary': status_summary,
            'floors': floors_list,
        })

    @action(detail=False, methods=['get'], url_path='summary')
    def summary(self, request):
        """Thống kê tổng hợp nhà trọ / phòng / bảo trì trong phạm vi của user hiện tại."""
        user = request.user
        properties = scoped_properties(user).exclude(status=PropertyStatus.DELETED)
        rooms = scoped_rooms(user).filter(property__in=properties)
        counts = {row['status']: row['n'] for row in rooms.values('status').annotate(n=Count('id'))}
        total_rooms = sum(counts.values())
        rented = counts.get(RoomStatus.OCCUPIED, 0) + counts.get(RoomStatus.FULL, 0)
        open_maintenance = scoped_maintenance(user).filter(
            room__in=rooms,
            status__in=[MaintenanceStatus.PENDING, MaintenanceStatus.IN_PROGRESS],
        ).count()
        data = {
            # "Tổng số tòa nhà" = cơ sở ĐANG VẬN HÀNH (ACTIVE); nhà tạm ngưng/đã xóa không tính.
            'total_properties': properties.filter(status=PropertyStatus.ACTIVE).count(),
            'total_rooms': total_rooms,
            'available_rooms': counts.get(RoomStatus.AVAILABLE, 0),
            # "Đang thuê" gồm cả phòng OCCUPIED và FULL (đã đủ người).
            'occupied_rooms': rented,
            'full_rooms': counts.get(RoomStatus.FULL, 0),
            'reserved_rooms': counts.get(RoomStatus.RESERVED, 0),
            'maintenance_rooms': counts.get(RoomStatus.MAINTENANCE, 0),
            'inactive_rooms': counts.get(RoomStatus.INACTIVE, 0),
            'occupancy_rate_percent': round(rented / total_rooms * 100, 1) if total_rooms else 0.0,
            'open_maintenance_requests': open_maintenance,
        }
        if is_manager(user):
            data['estimated_monthly_revenue'] = (
                rooms.filter(status__in=RENTED_STATUSES).aggregate(s=Sum('rent_price'))['s'] or 0)
        return Response(data)


# ==============================================================================
# II, III, IV, V, VI. MODULE ROOM — QUẢN LÝ PHÒNG, TRẠNG THÁI, TÌM KIẾM, LỌC, SẮP XẾP
# ==============================================================================
class RoomViewSet(viewsets.ModelViewSet):
    """
    II. MODULE ROOM — QUẢN LÝ PHÒNG TRỌ
    III. QUẢN LÝ TRẠNG THÁI PHÒNG (AVAILABLE, OCCUPIED, FULL, RESERVED, MAINTENANCE, INACTIVE)
    IV. TÌM KIẾM PHÒNG (Tên phòng, Mã phòng, Tên nhà trọ, Khu vực, Địa chỉ)
    V. LỌC PHÒNG (Giá phòng, Diện tích, Số người tối đa, Trạng thái, Vị trí/Khu vực)
    VI. SẮP XẾP DANH SÁCH PHÒNG (Giá tăng/giảm, Diện tích tăng/giảm, Tên phòng, Ngày tạo)
    Ghi chỉ dành cho ADMIN/LANDLORD; LANDLORD chỉ thao tác trên nhà trọ của mình.
    """
    serializer_class = RoomSerializer
    permission_classes = [IsManagerOrReadOnly]

    def get_queryset(self):
        queryset = scoped_rooms(self.request.user).prefetch_related('maintenance_requests')
        p = self.request.query_params

        # Phòng của nhà trọ đã xóa (DELETED) không được hiện trong các danh sách (tránh phòng mồ côi).
        # Xem chi tiết/sửa theo id vẫn được giữ để tra cứu lịch sử.
        if self.action in ('list', 'available_rooms', 'occupied_rooms', 'maintenance_rooms'):
            queryset = queryset.exclude(property__status=PropertyStatus.DELETED)

        # V.5 Lọc theo nhà trọ & vị trí / khu vực
        property_id = _parse_number(p.get('property_id') or p.get('property'), int, 'property_id')
        if property_id is not None:
            queryset = queryset.filter(property_id=property_id)

        district = p.get('district')
        if district and district != 'ALL':
            queryset = queryset.filter(property__district__icontains=district.strip())

        ward = p.get('ward')
        if ward and ward != 'ALL':
            queryset = queryset.filter(property__ward__icontains=ward.strip())

        address = p.get('address')
        if address:
            queryset = queryset.filter(property__address__icontains=address.strip())

        floor_param = _parse_number(p.get('floor'), int, 'floor')
        if floor_param is not None:
            queryset = queryset.filter(floor=floor_param)

        # V.4 Lọc theo trạng thái phòng
        status_param = p.get('status')
        if status_param and status_param != 'ALL':
            queryset = queryset.filter(status=status_param.upper())

        # V.1 Lọc theo khoảng giá phòng (VD: min_price=2000000&max_price=4000000)
        min_price = _parse_decimal(p.get('min_price'), 'min_price')
        if min_price is not None:
            queryset = queryset.filter(rent_price__gte=min_price)
        max_price = _parse_decimal(p.get('max_price'), 'max_price')
        if max_price is not None:
            queryset = queryset.filter(rent_price__lte=max_price)

        # V.2 Lọc theo khoảng diện tích (VD: min_area=15&max_area=30)
        min_area = _parse_number(p.get('min_area'), float, 'min_area')
        if min_area is not None:
            queryset = queryset.filter(area__gte=min_area)
        max_area = _parse_number(p.get('max_area'), float, 'max_area')
        if max_area is not None:
            queryset = queryset.filter(area__lte=max_area)

        # V.3 Lọc theo số người tối đa (VD: max_occupants=2)
        max_occupants = _parse_number(p.get('max_occupants'), int, 'max_occupants')
        if max_occupants is not None:
            queryset = queryset.filter(max_occupants=max_occupants)

        # IV. Tìm kiếm phòng (Tên phòng, Mã phòng, Tên nhà trọ, Khu vực, Địa chỉ)
        search = p.get('search')
        if search:
            q = search.strip()
            search_q = (
                Q(room_number__icontains=q)
                | Q(code__icontains=q)
                | Q(property__name__icontains=q)
                | Q(property__code__icontains=q)
                | Q(property__district__icontains=q)
                | Q(property__ward__icontains=q)
                | Q(property__address__icontains=q)
            )
            if is_manager(self.request.user):
                search_q |= Q(tenant_name__icontains=q)
            queryset = queryset.filter(search_q)

        # VI. Sắp xếp danh sách phòng
        sort_by = p.get('sort') or p.get('ordering') or ''
        sort_map = {
            'price_asc': ('rent_price', 'room_number'),
            'price_desc': ('-rent_price', 'room_number'),
            'area_asc': ('area', 'room_number'),
            'area_desc': ('-area', 'room_number'),
            'name_asc': ('room_number',),
            'name_desc': ('-room_number',),
            'created_desc': ('-created_at',),
            'created_asc': ('created_at',),
        }
        if sort_by in sort_map:
            queryset = queryset.order_by(*sort_map[sort_by])
        else:
            queryset = queryset.order_by('property_id', 'floor', 'room_number')

        return queryset

    def _check_property_ownership(self, serializer):
        prop = serializer.validated_data.get('property')
        if prop is not None and not scoped_properties(self.request.user).filter(pk=prop.pk).exists():
            raise serializers.ValidationError({'property': 'Bạn không có quyền quản lý nhà trọ này.'})

    def perform_create(self, serializer):
        self._check_property_ownership(serializer)
        serializer.save()

    def perform_update(self, serializer):
        self._check_property_ownership(serializer)
        serializer.save()

    def destroy(self, request, *args, **kwargs):
        """
        2.5 Xóa / ngừng sử dụng phòng:
        - Chặn xóa (400) nếu phòng đang thuê (OCCUPIED/FULL/current_occupants>0), đã đặt cọc (RESERVED),
          hoặc còn liên kết khách thuê / hợp đồng hiệu lực tại Tenant Service & Contract Service.
        - Chuyển sang INACTIVE (Soft Delete) nếu đã có lịch sử bảo trì.
        """
        room = self.get_object()
        if room.status in (*RENTED_STATUSES, RoomStatus.RESERVED) or room.current_occupants > 0:
            return Response(
                {'error': f'Phòng {room.room_number} đang có người thuê hoặc đã đặt cọc giữ chỗ, không thể xóa.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        external_reason = room_external_block_reason(request.user, room.id)
        if external_reason:
            return Response(
                {'error': f'Phòng {room.room_number} {external_reason}, không thể xóa.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if room.maintenance_requests.exists():
            room.status = RoomStatus.INACTIVE
            room.save(update_fields=['status', 'updated_at'])
            return Response({
                'message': f'Phòng {room.room_number} đã có lịch sử bảo trì nên được chuyển sang trạng thái '
                           f'INACTIVE (Ngừng hoạt động) để bảo toàn dữ liệu.',
                'soft_deleted': True,
                'room': self.get_serializer(room).data,
            })

        room_num = room.room_number
        room.delete()
        return Response({'message': f'Đã xóa phòng {room_num} thành công.', 'soft_deleted': False})

    # --- III. QUẢN LÝ TRẠNG THÁI PHÒNG (3.1 -> 3.6) ---------------------------
    @action(detail=True, methods=['get', 'patch', 'post'], url_path='status')
    def update_status(self, request, pk=None):
        """
        3.1 Xem trạng thái phòng (GET /rooms/{id}/status/)
        3.2 Cập nhật trạng thái phòng (PATCH/POST /rooms/{id}/status/) — chỉ quản lý
        """
        room = self.get_object()
        if request.method == 'GET':
            can_rent, reason = room.check_rentability()
            return Response({
                'room_id': room.id,
                'code': room.code,
                'room_number': room.room_number,
                'status': room.status,
                'status_display': room.get_status_display(),
                'current_occupants': room.current_occupants,
                'max_occupants': room.max_occupants,
                'is_rentable': can_rent,
                'rentability_reason': reason,
            })

        new_status = (request.data.get('status') or '').upper()
        if new_status not in RoomStatus.values:
            return Response(
                {
                    'error': f'Trạng thái không hợp lệ. Chọn một trong: {RoomStatus.values}',
                    'allowed_statuses': RoomStatus.values,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        occupants = _parse_number(request.data.get('current_occupants'), int, 'current_occupants')
        if occupants is not None:
            if occupants < 0 or occupants > room.max_occupants:
                return Response(
                    {'current_occupants': f'Số người đang ở phải từ 0 đến {room.max_occupants}.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            room.current_occupants = occupants

        tenant_name = request.data.get('tenant_name')
        tenant_phone = request.data.get('tenant_phone')

        if new_status == RoomStatus.AVAILABLE:
            room.current_occupants = 0
            room.tenant_name = ''
            room.tenant_phone = ''
        elif new_status == RoomStatus.FULL:
            room.current_occupants = room.max_occupants
        elif new_status == RoomStatus.OCCUPIED:
            if room.current_occupants <= 0:
                room.current_occupants = 1
            if room.current_occupants >= room.max_occupants:
                new_status = RoomStatus.FULL
        elif new_status == RoomStatus.INACTIVE:
            if room.current_occupants > 0 or room.status in RENTED_STATUSES:
                return Response(
                    {'error': f'Phòng {room.room_number} đang có khách thuê, không thể chuyển sang ngừng hoạt động.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        if tenant_name is not None:
            room.tenant_name = tenant_name
        if tenant_phone is not None:
            room.tenant_phone = tenant_phone

        room.status = new_status
        room.save()
        return Response({
            'message': f'Đã cập nhật trạng thái phòng {room.room_number} sang "{room.get_status_display()}".',
            'room': self.get_serializer(room).data,
        })

    @action(detail=True, methods=['get'], url_path='check_rentable')
    def check_rentable(self, request, pk=None):
        """3.3 Kiểm tra phòng có thể thuê hay không."""
        room = self.get_object()
        can_rent, reason = room.check_rentability()
        return Response({
            'room_id': room.id,
            'code': room.code,
            'room_number': room.room_number,
            'property_name': room.property.name,
            'status': room.status,
            'status_display': room.get_status_display(),
            'can_rent': can_rent,
            'reason': reason,
            'rent_price': room.rent_price,
            'area': room.area,
            'max_occupants': room.max_occupants,
            'current_occupants': room.current_occupants,
        })

    @action(detail=False, methods=['get'], url_path='available')
    def available_rooms(self, request):
        """3.4 Hiển thị danh sách phòng trống (AVAILABLE)."""
        qs = self.get_queryset().filter(status=RoomStatus.AVAILABLE)
        return Response(self.get_serializer(qs, many=True).data)

    @action(detail=False, methods=['get'], url_path='occupied')
    def occupied_rooms(self, request):
        """3.5 Hiển thị danh sách phòng đang được thuê (OCCUPIED & FULL)."""
        qs = self.get_queryset().filter(status__in=RENTED_STATUSES)
        return Response(self.get_serializer(qs, many=True).data)

    @action(detail=False, methods=['get'], url_path='maintenance')
    def maintenance_rooms(self, request):
        """3.6 Hiển thị danh sách phòng đang bảo trì (MAINTENANCE)."""
        qs = self.get_queryset().filter(status=RoomStatus.MAINTENANCE)
        return Response(self.get_serializer(qs, many=True).data)


# ==============================================================================
# VII. MODULE MAINTENANCE — QUẢN LÝ BẢO TRÌ / SỬA CHỮA
# ==============================================================================
class MaintenanceRequestViewSet(viewsets.ModelViewSet):
    """
    VII. MODULE MAINTENANCE — QUẢN LÝ BẢO TRÌ:
    7.1 Tạo yêu cầu bảo trì (POST /maintenance/) — mọi user đã đăng nhập, kể cả TENANT
    7.2 Xem danh sách yêu cầu bảo trì (GET /maintenance/?status=&priority=&room_id=&property_id=&search=)
    7.3 Xem chi tiết yêu cầu bảo trì (GET /maintenance/{id}/)
    7.4 Cập nhật yêu cầu bảo trì (PUT/PATCH /maintenance/{id}/) — quản lý
    7.5 Cập nhật trạng thái bảo trì (POST /maintenance/{id}/update_status/) — quản lý
        + lối tắt: /start/, /complete/ (quản lý), /cancel/ (quản lý hoặc người báo)
    7.6 Ghi nhận chi phí bảo trì (POST /maintenance/{id}/record_cost/) — quản lý
    7.7 Hoàn thành bảo trì (POST /maintenance/{id}/complete/) — quản lý
    7.8 Xem lịch sử bảo trì (GET /maintenance/{id}/history/ & /maintenance-history/)
    Phạm vi dữ liệu: ADMIN toàn bộ; LANDLORD nhà trọ của mình; TENANT yêu cầu do mình báo.

    Tạm khóa (quyết định D2 — quy trình bảo trì thuộc Sprint sau, source code giữ nguyên):
    mọi API GHI (7.1, 7.4–7.7, /start/, /cancel/). Chỉ còn GET danh sách / chi tiết / lịch sử.
    """
    serializer_class = MaintenanceRequestSerializer
    permission_classes = [permissions.IsAuthenticated]
    MANAGER_ACTIONS = ('update', 'partial_update', 'destroy', 'update_status', 'record_cost', 'start', 'complete')
    sprint_locked_actions = ('create', 'update', 'partial_update', 'destroy', 'update_status', 'record_cost',
                             'start', 'complete', 'cancel')

    def get_permissions(self):
        if self.action in self.MANAGER_ACTIONS:
            return [permissions.IsAuthenticated(), IsManagerRole(), SprintFeatureLock()]
        return [permissions.IsAuthenticated(), SprintFeatureLock()]

    def get_queryset(self):
        queryset = scoped_maintenance(self.request.user).prefetch_related('histories')
        p = self.request.query_params

        room_id = _parse_number(p.get('room_id') or p.get('room'), int, 'room_id')
        if room_id is not None:
            queryset = queryset.filter(room_id=room_id)

        property_id = _parse_number(p.get('property_id') or p.get('property'), int, 'property_id')
        if property_id is not None:
            queryset = queryset.filter(room__property_id=property_id)

        status_param = p.get('status')
        if status_param and status_param != 'ALL':
            queryset = queryset.filter(status=status_param.upper())

        priority = p.get('priority')
        if priority and priority != 'ALL':
            queryset = queryset.filter(priority=priority.upper())

        search = p.get('search')
        if search:
            q = search.strip()
            queryset = queryset.filter(
                Q(code__icontains=q)
                | Q(title__icontains=q)
                | Q(description__icontains=q)
                | Q(room__room_number__icontains=q)
                | Q(room__code__icontains=q)
                | Q(room__property__name__icontains=q)
            )

        return queryset

    def _history(self, req, action_label, previous_status, new_status, content):
        MaintenanceHistory.objects.create(
            maintenance_request=req,
            room=req.room,
            action=action_label,
            previous_status=previous_status,
            new_status=new_status,
            cost=req.actual_cost or req.estimated_cost or 0,
            repair_content=content,
            performed_by=_actor_name(self.request.user),
        )

    def _response(self, req, message):
        return Response({
            'message': message,
            'maintenance_request': self.get_serializer(req).data,
        })

    def _set_room_status(self, room, new_status):
        if room.status != new_status:
            room.status = new_status
            room.save(update_fields=['status', 'updated_at'])

    def _ensure_transition(self, req, allowed_from, target):
        if req.status not in allowed_from:
            raise serializers.ValidationError(
                {'error': f'Không thể chuyển yêu cầu {req.code} từ {req.status} sang {target}.'})

    @transaction.atomic
    def perform_create(self, serializer):
        """7.1 Tạo yêu cầu bảo trì + ghi lịch sử; quản lý có thể khóa phòng sang MAINTENANCE."""
        user = self.request.user
        room = serializer.validated_data['room']
        if not scoped_rooms(user).filter(pk=room.pk).exists():
            raise serializers.ValidationError({'room': 'Bạn không có quyền báo bảo trì cho phòng này.'})

        mark = serializer.validated_data.pop('mark_room_maintenance', True)
        # Tương thích tham số cũ của frontend/portal: set_room_maintenance=false
        legacy = self.request.data.get('set_room_maintenance')
        if legacy is not None and str(legacy).lower() in ('false', '0', 'no'):
            mark = False

        extra = {'reported_by_id': get_user_id(user)}
        if not serializer.validated_data.get('reported_by'):
            extra['reported_by'] = _actor_name(user)
        lock_room = mark and is_manager(user) and room.status != RoomStatus.MAINTENANCE
        if lock_room:
            extra['previous_room_status'] = room.status

        req = serializer.save(**extra)
        if lock_room:
            self._set_room_status(room, RoomStatus.MAINTENANCE)
        self._history(req, 'Tạo yêu cầu bảo trì mới', '', req.status, req.description or req.title)

    def perform_update(self, serializer):
        """7.4 Cập nhật thông tin yêu cầu bảo trì (không đổi trạng thái)."""
        serializer.validated_data.pop('mark_room_maintenance', None)
        room = serializer.validated_data.get('room')
        if room is not None and not scoped_rooms(self.request.user).filter(pk=room.pk).exists():
            raise serializers.ValidationError({'room': 'Bạn không có quyền quản lý phòng này.'})
        req = serializer.save()
        self._history(req, 'Cập nhật thông tin yêu cầu bảo trì', req.status, req.status,
                      req.repair_info or req.description)

    # ------------------------------------------------------------------
    # Các bước chuyển trạng thái (dùng chung cho update_status/start/complete/cancel)
    # ------------------------------------------------------------------
    def _do_start(self, req, technician=None, repair_info=None):
        self._ensure_transition(req, [MaintenanceStatus.PENDING], MaintenanceStatus.IN_PROGRESS)
        old = req.status
        req.status = MaintenanceStatus.IN_PROGRESS
        req.started_at = timezone.now()
        if technician:
            req.technician_name = technician
        if repair_info:
            req.repair_info = repair_info
        room = req.room
        if room.status != RoomStatus.MAINTENANCE:
            if not req.previous_room_status:
                req.previous_room_status = room.status
            self._set_room_status(room, RoomStatus.MAINTENANCE)
        req.save()
        self._history(req, f'Đổi trạng thái: {old} → {req.status}', old, req.status,
                      req.repair_info or 'Bắt đầu tiến hành sửa chữa')

    def _do_finish(self, req, target, room_status=None, actual_cost=None, repair_info=None):
        self._ensure_transition(req, [MaintenanceStatus.PENDING, MaintenanceStatus.IN_PROGRESS], target)
        old = req.status
        if actual_cost is not None:
            req.actual_cost = actual_cost
        if repair_info:
            req.repair_info = repair_info
        req.status = target
        if target == MaintenanceStatus.COMPLETED:
            req.completed_date = timezone.localdate()

        room = req.room
        old_room_status = room.status
        # Chỉ trả phòng về trạng thái khác khi phòng đang bị khóa bảo trì (hoặc quản lý chỉ định rõ).
        if room_status or room.status == RoomStatus.MAINTENANCE:
            self._set_room_status(room, _room_status_after_maintenance(req, room_status))
        req.save()

        if target == MaintenanceStatus.COMPLETED:
            label = 'Hoàn thành bảo trì & Bàn giao lại phòng'
            content = (f'{repair_info or req.repair_info or "Đã sửa chữa hoàn tất."} '
                       f'(Phòng {room.room_number}: {old_room_status} → {room.status})')
        else:
            label = f'Đổi trạng thái: {old} → {target}'
            content = repair_info or f'Hủy yêu cầu bảo trì (Phòng {room.room_number}: {old_room_status} → {room.status})'
        self._history(req, label, old, target, content)

    @action(detail=True, methods=['post', 'patch'], url_path='update_status')
    @transaction.atomic
    def update_status(self, request, pk=None):
        """7.5 Cập nhật trạng thái bảo trì: PENDING -> IN_PROGRESS -> COMPLETED (hoặc CANCELLED)."""
        req = self.get_object()
        new_status = (request.data.get('status') or '').upper()
        if new_status not in MaintenanceStatus.values or new_status == MaintenanceStatus.PENDING:
            return Response(
                {'error': f'Trạng thái không hợp lệ. Chọn một trong: '
                          f'{[s for s in MaintenanceStatus.values if s != MaintenanceStatus.PENDING]}'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        technician = request.data.get('technician_name')
        repair_info = request.data.get('repair_info')
        if new_status == MaintenanceStatus.IN_PROGRESS:
            self._do_start(req, technician, repair_info)
        else:
            if technician:
                req.technician_name = technician
            self._do_finish(req, new_status, request.data.get('room_status'), repair_info=repair_info)
        return self._response(req, f'Đã cập nhật trạng thái yêu cầu {req.code} sang {req.get_status_display()}.')

    @action(detail=True, methods=['post'])
    @transaction.atomic
    def start(self, request, pk=None):
        """Bắt đầu xử lý (PENDING -> IN_PROGRESS)."""
        req = self.get_object()
        self._do_start(req, request.data.get('technician_name') or request.data.get('assigned_to'),
                       request.data.get('repair_info'))
        return self._response(req, f'Đã bắt đầu xử lý yêu cầu {req.code}.')

    @action(detail=True, methods=['post'], url_path='record_cost')
    def record_cost(self, request, pk=None):
        """7.6 Ghi nhận chi phí bảo trì (Chi phí dự kiến & Chi phí thực tế)."""
        req = self.get_object()
        estimated_cost = _parse_decimal(request.data.get('estimated_cost'), 'estimated_cost')
        actual_cost = _parse_decimal(request.data.get('actual_cost'), 'actual_cost')
        for value, field in ((estimated_cost, 'estimated_cost'), (actual_cost, 'actual_cost')):
            if value is not None and value < 0:
                raise serializers.ValidationError({field: 'Chi phí không được âm.'})
        note = request.data.get('repair_info') or request.data.get('note') or ''

        if estimated_cost is not None:
            req.estimated_cost = estimated_cost
        if actual_cost is not None:
            req.actual_cost = actual_cost
        if note:
            req.repair_info = note
        req.save()

        self._history(
            req, 'Ghi nhận chi phí bảo trì', req.status, req.status,
            f'Chi phí dự kiến: {req.estimated_cost:,.0f} VNĐ | Chi phí thực tế: {req.actual_cost:,.0f} VNĐ. {note}'.strip(),
        )
        return self._response(req, f'Đã ghi nhận chi phí cho yêu cầu {req.code}.')

    @action(detail=True, methods=['post'], url_path='complete')
    @transaction.atomic
    def complete(self, request, pk=None):
        """
        7.7 Hoàn thành bảo trì:
        - Maintenance Status: PENDING/IN_PROGRESS -> COMPLETED
        - Room Status: MAINTENANCE -> room_status (nếu truyền) / trạng thái trước bảo trì / AVAILABLE|OCCUPIED
        Nhận actual_cost (hoặc cost) và repair_info (hoặc resolution_note).
        """
        req = self.get_object()
        actual_cost = request.data.get('actual_cost', request.data.get('cost'))
        actual_cost = _parse_decimal(actual_cost, 'actual_cost')
        if actual_cost is not None and actual_cost < 0:
            raise serializers.ValidationError({'actual_cost': 'Chi phí không được âm.'})
        repair_info = request.data.get('repair_info') or request.data.get('resolution_note') or ''
        self._do_finish(req, MaintenanceStatus.COMPLETED, request.data.get('room_status'),
                        actual_cost=actual_cost, repair_info=repair_info)
        return self._response(
            req, f'Đã hoàn thành bảo trì {req.code}. Phòng {req.room.room_number} đã chuyển sang '
                 f'{req.room.get_status_display()}.')

    @action(detail=True, methods=['post'])
    @transaction.atomic
    def cancel(self, request, pk=None):
        """Hủy yêu cầu (quản lý, hoặc chính người báo khi yêu cầu còn mở)."""
        req = self.get_object()
        user = request.user
        if not is_manager(user) and req.reported_by_id != get_user_id(user):
            return Response({'error': 'Bạn không có quyền hủy yêu cầu này.'}, status=status.HTTP_403_FORBIDDEN)
        room_status = request.data.get('room_status') if is_manager(user) else None
        self._do_finish(req, MaintenanceStatus.CANCELLED, room_status,
                        repair_info=request.data.get('repair_info') or request.data.get('reason'))
        return self._response(req, f'Đã hủy yêu cầu bảo trì {req.code}.')

    @action(detail=True, methods=['get'], url_path='history')
    def history(self, request, pk=None):
        """7.8 Xem lịch sử của 1 yêu cầu bảo trì."""
        req = self.get_object()
        return Response(MaintenanceHistorySerializer(req.histories.all(), many=True).data)


class MaintenanceHistoryViewSet(viewsets.ReadOnlyModelViewSet):
    """
    7.8 Xem toàn bộ lịch sử bảo trì (theo dõi các lần sửa chữa, ngày sửa chữa, chi phí, trạng thái, nội dung).
    Cùng phạm vi dữ liệu với yêu cầu bảo trì.
    """
    serializer_class = MaintenanceHistorySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = MaintenanceHistory.objects.select_related('maintenance_request', 'room', 'room__property').filter(
            maintenance_request__in=scoped_maintenance(self.request.user))
        params = self.request.query_params
        room_id = _parse_number(params.get('room_id') or params.get('room'), int, 'room_id')
        if room_id is not None:
            qs = qs.filter(room_id=room_id)
        property_id = _parse_number(params.get('property_id') or params.get('property'), int, 'property_id')
        if property_id is not None:
            qs = qs.filter(room__property_id=property_id)
        return qs

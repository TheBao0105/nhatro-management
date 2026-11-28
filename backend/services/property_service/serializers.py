from rest_framework import serializers

from common.auth import is_manager
from .models import (
    MaintenanceHistory,
    MaintenanceRequest,
    MaintenanceStatus,
    Property,
    PropertyStatus,
    Room,
    RoomStatus,
)


def _viewer_is_manager(serializer):
    request = serializer.context.get('request')
    return bool(request and is_manager(request.user))


class MaintenanceHistorySerializer(serializers.ModelSerializer):
    request_code = serializers.CharField(source='maintenance_request.code', read_only=True)
    request_title = serializers.CharField(source='maintenance_request.title', read_only=True)
    room_code = serializers.CharField(source='room.code', read_only=True)
    room_number = serializers.CharField(source='room.room_number', read_only=True)
    property_name = serializers.CharField(source='room.property.name', read_only=True)

    class Meta:
        model = MaintenanceHistory
        fields = [
            'id',
            'maintenance_request',
            'request_code',
            'request_title',
            'room',
            'room_code',
            'room_number',
            'property_name',
            'action',
            'previous_status',
            'new_status',
            'cost',
            'repair_content',
            'performed_by',
            'repair_date',
        ]
        read_only_fields = ['id', 'repair_date']


class MaintenanceRequestSerializer(serializers.ModelSerializer):
    room_code = serializers.CharField(source='room.code', read_only=True)
    room_number = serializers.CharField(source='room.room_number', read_only=True)
    room_status = serializers.CharField(source='room.status', read_only=True)
    property_id = serializers.IntegerField(source='room.property_id', read_only=True)
    property_code = serializers.CharField(source='room.property.code', read_only=True)
    property_name = serializers.CharField(source='room.property.name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    priority_display = serializers.CharField(source='get_priority_display', read_only=True)
    histories = MaintenanceHistorySerializer(many=True, read_only=True)
    # Tạo yêu cầu: có chuyển phòng sang MAINTENANCE trong lúc xử lý hay không.
    # Mặc định True (giữ hành vi cũ); chỉ quản lý mới được khóa phòng.
    mark_room_maintenance = serializers.BooleanField(write_only=True, required=False, default=True)

    class Meta:
        model = MaintenanceRequest
        fields = [
            'id',
            'code',
            'room',
            'room_code',
            'room_number',
            'room_status',
            'property_id',
            'property_code',
            'property_name',
            'title',
            'description',
            'repair_info',
            'priority',
            'priority_display',
            'status',
            'status_display',
            'estimated_cost',
            'actual_cost',
            'reported_by',
            'reported_by_id',
            'technician_name',
            'previous_room_status',
            'mark_room_maintenance',
            'requested_date',
            'started_at',
            'completed_date',
            'histories',
            'created_at',
            'updated_at',
        ]
        # Trạng thái chỉ đổi qua các action (update_status/start/complete/cancel)
        # để luôn đồng bộ trạng thái phòng và ghi lịch sử.
        read_only_fields = ['id', 'code', 'status', 'reported_by_id', 'previous_room_status',
                            'started_at', 'completed_date', 'created_at', 'updated_at']


class RoomSerializer(serializers.ModelSerializer):
    property_code = serializers.CharField(source='property.code', read_only=True)
    property_name = serializers.CharField(source='property.name', read_only=True)
    property_address = serializers.CharField(source='property.full_address', read_only=True)
    property_district = serializers.CharField(source='property.district', read_only=True)
    property_ward = serializers.CharField(source='property.ward', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    room_type_display = serializers.CharField(source='get_room_type_display', read_only=True)
    is_rentable = serializers.BooleanField(read_only=True)
    rentability_reason = serializers.SerializerMethodField()
    maintenance_requests = MaintenanceRequestSerializer(many=True, read_only=True)
    active_maintenance_count = serializers.SerializerMethodField()

    # Thông tin cá nhân người đang thuê chỉ hiển thị cho ADMIN/LANDLORD.
    PRIVATE_FIELDS = ('tenant_name', 'tenant_phone', 'maintenance_requests')

    class Meta:
        model = Room
        fields = [
            'id',
            'code',
            'property',
            'property_code',
            'property_name',
            'property_address',
            'property_district',
            'property_ward',
            'room_number',
            'floor',
            'room_type',
            'room_type_display',
            'area',
            'rent_price',
            'deposit_amount',
            'max_occupants',
            'current_occupants',
            'status',
            'status_display',
            'is_rentable',
            'rentability_reason',
            'tenant_name',
            'tenant_phone',
            'amenities',
            'description',
            'initial_electric_reading',
            'initial_water_reading',
            'active_maintenance_count',
            'maintenance_requests',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
        validators = []

    def validate(self, attrs):
        prop = attrs.get('property', getattr(self.instance, 'property', None))
        if prop is not None and prop.status == PropertyStatus.DELETED:
            raise serializers.ValidationError(
                {'property': f'Nhà trọ "{prop.name}" đã bị xóa, không thể thêm hoặc chuyển phòng vào.'}
            )
        room_num = (attrs.get('room_number', getattr(self.instance, 'room_number', '')) or '').strip()
        dup_qs = Room.objects.filter(property=prop, room_number__iexact=room_num)
        if self.instance is not None:
            dup_qs = dup_qs.exclude(pk=self.instance.pk)
        if dup_qs.exists():
            raise serializers.ValidationError(
                {'room_number': f'Phòng "{room_num}" đã tồn tại trong nhà trọ này.'}
            )

        floor = attrs.get('floor', getattr(self.instance, 'floor', 1))
        if prop is not None and (floor < 1 or floor > prop.total_floors):
            raise serializers.ValidationError(
                {'floor': f'Số tầng ({floor}) phải từ 1 đến tổng số tầng của nhà trọ ({prop.total_floors}).'}
            )

        max_occ = attrs.get('max_occupants', getattr(self.instance, 'max_occupants', 2))
        current = attrs.get('current_occupants', getattr(self.instance, 'current_occupants', 0))
        if current > max_occ:
            raise serializers.ValidationError(
                {'current_occupants': f'Số người đang ở ({current}) vượt quá tối đa ({max_occ}).'})

        new_status = attrs.get('status')
        if new_status == RoomStatus.INACTIVE and self.instance is not None:
            if self.instance.current_occupants > 0 or self.instance.status in (RoomStatus.OCCUPIED, RoomStatus.FULL):
                raise serializers.ValidationError(
                    {'status': f'Phòng {self.instance.room_number} đang có khách thuê, không thể chuyển sang ngừng hoạt động.'}
                )
        elif new_status == RoomStatus.AVAILABLE:
            attrs['current_occupants'] = 0
            attrs['tenant_name'] = ''
            attrs['tenant_phone'] = ''
        elif new_status == RoomStatus.FULL:
            attrs['current_occupants'] = max_occ
        elif new_status == RoomStatus.OCCUPIED:
            if current <= 0:
                current = 1
                attrs['current_occupants'] = 1
            if current >= max_occ:
                attrs['status'] = RoomStatus.FULL
        return attrs

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if not _viewer_is_manager(self):
            for field in self.PRIVATE_FIELDS:
                data.pop(field, None)
        return data

    def get_rentability_reason(self, obj):
        _, reason = obj.check_rentability()
        return reason

    def get_active_maintenance_count(self, obj):
        return obj.maintenance_requests.filter(
            status__in=[MaintenanceStatus.PENDING, MaintenanceStatus.IN_PROGRESS]
        ).count()


class PropertySerializer(serializers.ModelSerializer):
    full_address = serializers.CharField(read_only=True)
    area_location = serializers.CharField(read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    total_rooms_count = serializers.IntegerField(read_only=True)
    available_rooms_count = serializers.IntegerField(read_only=True)
    occupied_rooms_count = serializers.IntegerField(read_only=True)
    full_rooms_count = serializers.IntegerField(read_only=True)
    maintenance_rooms_count = serializers.IntegerField(read_only=True)
    inactive_rooms_count = serializers.IntegerField(read_only=True)
    rooms = RoomSerializer(many=True, read_only=True)

    class Meta:
        model = Property
        fields = [
            'id',
            'code',
            'owner_id',
            'name',
            'address',
            'ward',
            'district',
            'city',
            'full_address',
            'area_location',
            'total_floors',
            'electricity_rate',
            'water_rate',
            'internet_rate',
            'description',
            'rules',
            'image_url',
            'status',
            'status_display',
            'total_rooms_count',
            'available_rooms_count',
            'occupied_rooms_count',
            'full_rooms_count',
            'maintenance_rooms_count',
            'inactive_rooms_count',
            'rooms',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'owner_id', 'created_at', 'updated_at']

    def validate_status(self, value):
        if (
            value == PropertyStatus.DELETED
            and self.instance is not None
            and self.instance.rooms.exclude(status=RoomStatus.INACTIVE).exists()
        ):
            raise serializers.ValidationError(
                f'Nhà trọ "{self.instance.name}" còn phòng đang hoạt động. '
                f'Hãy chuyển các phòng sang INACTIVE hoặc xóa phòng trước khi xóa nhà trọ.'
            )
        return value

    def validate_total_floors(self, value):
        if self.instance is not None:
            over_floor = self.instance.rooms.filter(floor__gt=value).order_by('-floor').first()
            if over_floor is not None:
                raise serializers.ValidationError(
                    f'Không thể giảm số tầng xuống {value} vì phòng "{over_floor.room_number}" đang ở tầng {over_floor.floor}.'
                )
        return value

    def create(self, validated_data):
        # owner_id luôn lấy từ claim user_id của JWT (Identity Service), không nhận từ client.
        request = self.context.get('request')
        if request and hasattr(request, 'user') and request.user.is_authenticated:
            validated_data['owner_id'] = int(request.user.id)
        return super().create(validated_data)

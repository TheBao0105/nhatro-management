from rest_framework import serializers
from .models import Property, Room, MaintenanceRequest

class RoomSerializer(serializers.ModelSerializer):
    property_name = serializers.CharField(source='property.name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = Room
        fields = [
            'id',
            'property',
            'property_name',
            'room_number',
            'floor',
            'area',
            'rent_price',
            'deposit_amount',
            'max_occupants',
            'status',
            'status_display',
            'amenities',
            'description',
            'initial_electric_reading',
            'initial_water_reading',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class PropertySerializer(serializers.ModelSerializer):
    landlord_name = serializers.CharField(source='landlord.full_name', read_only=True)
    full_address = serializers.CharField(read_only=True)
    total_rooms_count = serializers.IntegerField(read_only=True)
    available_rooms_count = serializers.IntegerField(read_only=True)
    occupied_rooms_count = serializers.IntegerField(read_only=True)
    rooms = RoomSerializer(many=True, read_only=True)

    class Meta:
        model = Property
        fields = [
            'id',
            'landlord',
            'landlord_name',
            'name',
            'address',
            'ward',
            'district',
            'city',
            'full_address',
            'total_floors',
            'electricity_rate',
            'water_rate',
            'internet_rate',
            'description',
            'rules',
            'image_url',
            'total_rooms_count',
            'available_rooms_count',
            'occupied_rooms_count',
            'rooms',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'landlord', 'created_at', 'updated_at']

    def create(self, validated_data):
        # Tự động gán landlord là user đang đăng nhập
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            validated_data['landlord'] = request.user
        return super().create(validated_data)


class MaintenanceRequestSerializer(serializers.ModelSerializer):
    property_name = serializers.CharField(source='property.name', read_only=True)
    room_number = serializers.CharField(source='room.room_number', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    priority_display = serializers.CharField(source='get_priority_display', read_only=True)
    reported_by_name = serializers.CharField(source='reported_by.full_name', read_only=True)

    class Meta:
        model = MaintenanceRequest
        fields = [
            'id',
            'property',
            'property_name',
            'room',
            'room_number',
            'reported_by',
            'reported_by_name',
            'title',
            'description',
            'priority',
            'priority_display',
            'status',
            'status_display',
            'cost',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'reported_by', 'created_at', 'updated_at']

    def create(self, validated_data):
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            validated_data['reported_by'] = request.user
        return super().create(validated_data)


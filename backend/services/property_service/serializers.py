from rest_framework import serializers
from .models import Property, Room

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
    full_address = serializers.CharField(read_only=True)
    total_rooms_count = serializers.IntegerField(read_only=True)
    available_rooms_count = serializers.IntegerField(read_only=True)
    occupied_rooms_count = serializers.IntegerField(read_only=True)
    rooms = RoomSerializer(many=True, read_only=True)

    class Meta:
        model = Property
        fields = [
            'id',
            'owner_id',
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
        read_only_fields = ['id', 'owner_id', 'created_at', 'updated_at']

    def create(self, validated_data):
        # Tự động gán owner_id từ ID của user đăng nhập
        request = self.context.get('request')
        if request and hasattr(request, 'user') and request.user.is_authenticated:
            validated_data['owner_id'] = request.user.id
        return super().create(validated_data)

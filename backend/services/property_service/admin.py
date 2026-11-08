from django.contrib import admin
from .models import Property, Room

@admin.register(Property)
class PropertyAdmin(admin.ModelAdmin):
    list_display = ('name', 'owner_id', 'full_address', 'total_floors', 'electricity_rate', 'water_rate', 'created_at')
    search_fields = ('name', 'address', 'ward', 'district', 'city')
    list_filter = ('city', 'district')

@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ('room_number', 'property', 'floor', 'rent_price', 'status', 'area', 'max_occupants')
    list_filter = ('status', 'property', 'floor')
    search_fields = ('room_number', 'property__name')

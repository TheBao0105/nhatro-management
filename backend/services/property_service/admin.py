from django.contrib import admin
from .models import Property, Room, MaintenanceRequest

@admin.register(Property)
class PropertyAdmin(admin.ModelAdmin):
    list_display = ('name', 'landlord', 'full_address', 'total_floors', 'electricity_rate', 'water_rate', 'created_at')
    search_fields = ('name', 'address', 'ward', 'district', 'city')
    list_filter = ('city', 'district')

@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ('room_number', 'property', 'floor', 'rent_price', 'status', 'area', 'max_occupants')
    list_filter = ('status', 'property', 'floor')
    search_fields = ('room_number', 'property__name')

@admin.register(MaintenanceRequest)
class MaintenanceRequestAdmin(admin.ModelAdmin):
    list_display = ('title', 'property', 'room', 'priority', 'status', 'cost', 'reported_by', 'created_at')
    list_filter = ('status', 'priority', 'property')
    search_fields = ('title', 'description')


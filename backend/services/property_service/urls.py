from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import PropertyViewSet, RoomViewSet, MaintenanceRequestViewSet

router = DefaultRouter()
router.register(r'properties', PropertyViewSet, basename='property')
router.register(r'rooms', RoomViewSet, basename='room')
router.register(r'maintenance', MaintenanceRequestViewSet, basename='maintenance')

urlpatterns = [
    path('', include(router.urls)),
]


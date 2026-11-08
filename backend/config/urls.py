from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView
from .architecture_views import ArchitectureStatusView

urlpatterns = [
    path('admin/', admin.site.urls),

    # OpenAPI Schema & Swagger Docs
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),

    # SPRINT 1 — ARCHITECTURE & SERVICE INTEGRATION CHECK
    path('api/v1/architecture/status/', ArchitectureStatusView.as_view(), name='architecture_status'),

    # SPRINT 1 — SERVICE 1: IDENTITY & AUTHENTICATION
    path('api/v1/', include('services.identity_service.urls')),

    # SPRINT 1 — SERVICE 2: PROPERTY & ROOM MANAGEMENT
    path('api/v1/', include('services.property_service.urls')),

    # SPRINT 2 (LỘ TRÌNH TIẾP THEO) — SERVICE 3: TENANT SERVICE
    path('api/v1/tenants/', include('services.tenant_service.urls')),

    # SPRINT 2 (LỘ TRÌNH TIẾP THEO) — SERVICE 4: CONTRACT SERVICE
    path('api/v1/contracts/', include('services.contract_service.urls')),

    # SPRINT 3 (LỘ TRÌNH TIẾP THEO) — SERVICE 5: BILLING & NOTIFICATION SERVICE
    path('api/v1/billing/', include('services.billing_notification_service.urls')),
]

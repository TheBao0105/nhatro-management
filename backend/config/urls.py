from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView

urlpatterns = [
    path('admin/', admin.site.urls),

    # OpenAPI Schema & Swagger Docs
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),

    # SERVICE 1 — IDENTITY SERVICE
    path('api/v1/', include('services.identity_service.urls')),

    # SERVICE 2 — PROPERTY & MAINTENANCE SERVICE
    path('api/v1/', include('services.property_service.urls')),

    # SERVICE 3 — TENANT SERVICE (Sprint 2)
    path('api/v1/tenants/', include('services.tenant_service.urls')),

    # SERVICE 4 — CONTRACT SERVICE (Sprint 2)
    path('api/v1/contracts/', include('services.contract_service.urls')),

    # SERVICE 5 — BILLING & NOTIFICATION SERVICE (Sprint 3)
    path('api/v1/billing/', include('services.billing_notification_service.urls')),
]


from django.urls import path
from .views import TenantServiceStatusView

urlpatterns = [
    path('status/', TenantServiceStatusView.as_view(), name='tenant_service_status'),
]


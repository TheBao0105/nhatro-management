from django.urls import path
from .views import BillingServiceStatusView

urlpatterns = [
    path('status/', BillingServiceStatusView.as_view(), name='billing_service_status'),
]


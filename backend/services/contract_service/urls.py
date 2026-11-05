from django.urls import path
from .views import ContractServiceStatusView

urlpatterns = [
    path('status/', ContractServiceStatusView.as_view(), name='contract_service_status'),
]


from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ChangePasswordView,
    CurrentUserView,
    CustomLoginView,
    CustomTokenRefreshView,
    LogoutView,
    RegisterView,
    TestAccountsView,
    UserViewSet,
)

router = DefaultRouter()
router.register(r'users', UserViewSet, basename='user')

urlpatterns = [
    # Auth endpoints
    path('auth/login/', CustomLoginView.as_view(), name='auth_login'),
    path('auth/refresh/', CustomTokenRefreshView.as_view(), name='auth_refresh'),
    path('auth/register/', RegisterView.as_view(), name='auth_register'),
    path('auth/me/', CurrentUserView.as_view(), name='auth_me'),
    path('auth/logout/', LogoutView.as_view(), name='auth_logout'),
    path('auth/change-password/', ChangePasswordView.as_view(), name='auth_change_password'),
    # Chỉ hoạt động khi DEBUG=True (tài khoản mẫu cho môi trường dev)
    path('auth/test-users/', TestAccountsView.as_view(), name='auth_test_users'),

    # User management
    path('', include(router.urls)),
]


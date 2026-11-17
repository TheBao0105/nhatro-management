from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (CustomLoginView, CustomRefreshView, RegisterView,
                    CurrentUserView, UserViewSet, ChangePasswordView, LogoutView)

router = DefaultRouter()
router.register(r'users', UserViewSet, basename='user')

urlpatterns = [
    # Auth endpoints
    path('auth/login/', CustomLoginView.as_view(), name='auth_login'),
    path('auth/refresh/', CustomRefreshView.as_view(), name='auth_refresh'),
    path('auth/logout/', LogoutView.as_view(), name='auth_logout'),
    path('auth/change-password/', ChangePasswordView.as_view(), name='auth_change_password'),
    path('auth/register/', RegisterView.as_view(), name='auth_register'),
    path('auth/me/', CurrentUserView.as_view(), name='auth_me'),

    # User management
    path('', include(router.urls)),
]


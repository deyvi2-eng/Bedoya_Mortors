from django.urls import path

from .views import (
    CustomLoginView,
    LogoutView,
    UserManagementView,
    UserCreateAPI,
    UserToggleActiveAPI,
    UserDeleteAPI
)

app_name = 'accounts'

urlpatterns = [
    path('login/', CustomLoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('manage/', UserManagementView.as_view(), name='manage'),
    path('api/create/', UserCreateAPI.as_view(), name='api-create'),
    # Nuevas rutas para control visual de usuarios
    path('api/toggle-status/<int:user_id>/', UserToggleActiveAPI.as_view(), name='api-toggle-status'),
    path('api/delete/<int:user_id>/', UserDeleteAPI.as_view(), name='api-delete'),
]
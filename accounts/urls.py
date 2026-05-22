from django.urls import path

from .views import (
    CustomLoginView,
    LogoutView,
    UserManagementView,
    UserCreateAPI
)

app_name = 'accounts'

urlpatterns = [

    path(
        'login/',
        CustomLoginView.as_view(),
        name='login'
    ),

    path(
        'logout/',
        LogoutView.as_view(),
        name='logout'
    ),

    path(
        'manage/',
        UserManagementView.as_view(),
        name='manage'
    ),

    path(
        'api/create/',
        UserCreateAPI.as_view(),
        name='api-create'
    ),
]
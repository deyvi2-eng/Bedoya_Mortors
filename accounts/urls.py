from django.urls import path
from django.contrib.auth.views import LogoutView
from .views import CustomLoginView, UserManagementView, UserCreateAPI

app_name = 'accounts'

urlpatterns = [
    path('login/', CustomLoginView.as_view(), name='login'),
    # Cierra sesión y redirige al login visual
    path('logout/', LogoutView.as_view(next_page='/accounts/login/'), name='logout'), 
    path('manage/', UserManagementView.as_view(), name='manage'),
    path('api/create/', UserCreateAPI.as_view(), name='api-create'),
]
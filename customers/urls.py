from django.urls import path
from .views import CustomerDashboardView, CustomerCreateAPI

app_name = 'customers'

urlpatterns = [
    path('manage/', CustomerDashboardView.as_view(), name='manage'),
    path('api/create/', CustomerCreateAPI.as_view(), name='api-create'),
]
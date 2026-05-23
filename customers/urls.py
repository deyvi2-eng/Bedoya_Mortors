from django.urls import path
from .views import CustomerManagementView, CustomerCreateAPI, CustomerToggleAPI, CustomerHistoryAPI

app_name = 'customers'

urlpatterns = [
    path('manage/', CustomerManagementView.as_view(), name='manage'),
    path('api/create/', CustomerCreateAPI.as_view(), name='api-create'),
    path('api/toggle/<int:customer_id>/', CustomerToggleAPI.as_view(), name='api-toggle'),
    # Nueva ruta para el historial
    path('api/history/<int:customer_id>/', CustomerHistoryAPI.as_view(), name='api-history'),
]
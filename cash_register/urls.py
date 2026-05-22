from django.urls import path
from .views import CashDashboardView, OpenCashSessionAPI, CloseCashSessionAPI

app_name = 'cash_register'

urlpatterns = [
    path('dashboard/', CashDashboardView.as_view(), name='dashboard'),
    path('api/open/', OpenCashSessionAPI.as_view(), name='api-open'),
    path('api/close/', CloseCashSessionAPI.as_view(), name='api-close'),
]
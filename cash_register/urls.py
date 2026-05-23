from django.urls import path
from .views import (
    CashDashboardView, 
    OpenCashAPI, 
    CloseCashAPI, 
    CashSessionDetailAPI,    # <-- Agregado
    CashSessionReportView    # <-- Agregado
)

app_name = 'cash_register'

urlpatterns = [
    # Vista principal
    path('dashboard/', CashDashboardView.as_view(), name='dashboard'),
    
    # APIs de funcionalidad
    path('api/open/', OpenCashAPI.as_view(), name='api-open'),
    path('api/close/', CloseCashAPI.as_view(), name='api-close'),
    
    # APIs para Detalles y Reportes
    path('api/detail/<int:session_id>/', CashSessionDetailAPI.as_view(), name='api-detail'),
    path('report/<int:session_id>/', CashSessionReportView.as_view(), name='report'),
]
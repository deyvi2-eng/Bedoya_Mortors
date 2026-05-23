from django.urls import path
from .views import (
    POSDashboardView, 
    POSProductSearchAPI, 
    POSCustomerSearchAPI, 
    ProcessSaleAPI,
    InvoicePDFView  # <-- Importar la nueva vista
)

app_name = 'sales'

urlpatterns = [
    # Interfaz visual del Punto de Venta
    path('pos/', POSDashboardView.as_view(), name='pos'),
    
    # APIs para JavaScript
    path('api/search-products/', POSProductSearchAPI.as_view(), name='api-search-products'),
    path('api/search-customers/', POSCustomerSearchAPI.as_view(), name='api-search-customers'),
    path('api/process/', ProcessSaleAPI.as_view(), name='api-process-sale'),
    
    # URL para generar y visualizar la factura
    path('invoice/<str:invoice_number>/', InvoicePDFView.as_view(), name='invoice-pdf'),
]
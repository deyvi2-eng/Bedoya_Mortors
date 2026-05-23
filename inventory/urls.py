from django.urls import path
from .views import (
    InventoryDashboardView, 
    ProductCreateAPI, 
    AddStockAPI, 
    ProductToggleAPI,
    StockMovementLogView,  # <-- Agregado para el Kardex General
    ProductKardexAPI       # <-- Agregado para el Kardex por Producto
)

app_name = 'inventory'

urlpatterns = [
    # Vista principal (Dashboard del inventario)
    path('manage/', InventoryDashboardView.as_view(), name='manage'),
    
    # Vista del Kardex General (Historial de movimientos)
    path('movements/', StockMovementLogView.as_view(), name='movements'),
    
    # APIs para manejar productos y stock
    path('api/product/create/', ProductCreateAPI.as_view(), name='api-product-create'),
    path('api/product/add-stock/', AddStockAPI.as_view(), name='api-product-add-stock'),
    path('api/product/toggle/<int:product_id>/', ProductToggleAPI.as_view(), name='api-product-toggle'),
    
    # API para ver el Kardex específico de un producto en el Modal
    path('api/product/kardex/<int:product_id>/', ProductKardexAPI.as_view(), name='api-product-kardex'),
]
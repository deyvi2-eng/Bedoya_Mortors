from django.urls import path
from .views import (
    # Vistas base y de productos
    InventoryDashboardView, 
    ProductCreateAPI, 
    AddStockAPI, 
    ProductToggleAPI,
    ProductDetailAPI,  # <--- IMPORTACIÓN AÑADIDA PARA LEER EL PRODUCTO
    ProductUpdateAPI,  # Importación para edición (Soporta Fotos)
    ProductDeleteAPI,  # Importación para eliminación
    
    # Kardex y Movimientos
    StockMovementLogView,
    ProductKardexAPI,
    
    # Creación de Catálogos (Desde modales)
    CategoryCreateAPI,
    SupplierCreateAPI,

    # NUEVAS VISTAS: Pantalla de ajustes y edición de Catálogos
    InventorySettingsView,
    CategoryUpdateAPI,
    CategoryToggleAPI,
    SupplierUpdateAPI,
    SupplierToggleAPI
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
    
    # ==========================================
    # NUEVOS ENDPOINTS: Lectura, Edición y Eliminación
    # ==========================================
    # Esta ruta es vital para cargar la foto en el Modal
    path('api/products/<int:pk>/', ProductDetailAPI.as_view(), name='api-product-detail'),
    # Esta ruta procesa los cambios de texto y la nueva imagen
    path('api/products/update/<int:pk>/', ProductUpdateAPI.as_view(), name='api-product-update'), 
    path('api/product/delete/<int:pk>/', ProductDeleteAPI.as_view(), name='api-product-delete'),
    
    # API para ver el Kardex específico de un producto en el Modal
    path('api/product/kardex/<int:product_id>/', ProductKardexAPI.as_view(), name='api-product-kardex'),
    
    # APIs para creación rápida desde el inventario
    path('api/category/create/', CategoryCreateAPI.as_view(), name='api-category-create'),
    path('api/supplier/create/', SupplierCreateAPI.as_view(), name='api-supplier-create'),
    
    # ==========================================
    # RUTAS DE ADMINISTRACIÓN DE CATÁLOGOS
    # ==========================================
    # Pantalla visual de Catálogos
    path('settings/', InventorySettingsView.as_view(), name='settings'),
    
    # Endpoints de Edición y Estado (Categorías)
    path('api/category/update/<int:pk>/', CategoryUpdateAPI.as_view(), name='api-category-update'),
    path('api/category/toggle/<int:pk>/', CategoryToggleAPI.as_view(), name='api-category-toggle'),
    
    # Endpoints de Edición y Estado (Proveedores)
    path('api/supplier/update/<int:pk>/', SupplierUpdateAPI.as_view(), name='api-supplier-update'),
    path('api/supplier/toggle/<int:pk>/', SupplierToggleAPI.as_view(), name='api-supplier-toggle'),
]
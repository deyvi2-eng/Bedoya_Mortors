from django.urls import path
from .views import InventoryDashboardView, ProductCreateAPI, AddStockAPI

app_name = 'inventory'

urlpatterns = [
    path('manage/', InventoryDashboardView.as_view(), name='manage'),
    path('api/product/create/', ProductCreateAPI.as_view(), name='api-product-create'),
    path('api/product/add-stock/', AddStockAPI.as_view(), name='api-product-add-stock'),
]
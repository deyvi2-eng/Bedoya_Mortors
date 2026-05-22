from django.urls import path

from .views import (
    InventoryDashboardView,
    ProductCreateAPI,
    AddStockAPI
)

urlpatterns = [

    path(
        'manage/',
        InventoryDashboardView.as_view(),
        name='manage'
    ),

    path(
        'api/create/',
        ProductCreateAPI.as_view(),
        name='api-create'
    ),

    path(
        'api/add-stock/',
        AddStockAPI.as_view(),
        name='api-add-stock'
    ),
]
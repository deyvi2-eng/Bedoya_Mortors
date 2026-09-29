from django.urls import path
from . import views

app_name = 'furniture'

urlpatterns = [
    path('', views.home, name='home'),

    # Clientes
    path('clientes/', views.client_list, name='clients'),
    path('clientes/<int:pk>/', views.client_detail, name='client_detail'),
    path('clientes/<int:pk>/eliminar/', views.client_delete, name='client_delete'),
    path('api/clientes/', views.client_search_api, name='client_search_api'),
    path('api/clientes/guardar/', views.client_save_api, name='client_create_api'),
    path('api/clientes/<int:pk>/guardar/', views.client_save_api, name='client_update_api'),

    # Hojas de entrada
    path('ordenes/', views.order_list, name='orders'),
    path('ordenes/nueva/', views.order_create, name='order_create'),
    path('ordenes/<int:pk>/', views.order_detail, name='order_detail'),
    path('ordenes/<int:pk>/estado/', views.order_status, name='order_status'),
    path('ordenes/<int:pk>/abono/', views.order_payment, name='order_payment'),
    path('ordenes/<int:pk>/fotos/', views.order_add_photos, name='order_add_photos'),
    path('ordenes/<int:pk>/eliminar/', views.order_delete, name='order_delete'),
    path('ordenes/<int:pk>/pdf/', views.order_pdf, name='order_pdf'),

    # Proformas
    path('proformas/', views.quote_list, name='quotes'),
    path('proformas/nueva/', views.quote_create, name='quote_create'),
    path('proformas/<int:pk>/', views.quote_detail, name='quote_detail'),
    path('proformas/<int:pk>/estado/', views.quote_status, name='quote_status'),
    path('proformas/<int:pk>/eliminar/', views.quote_delete, name='quote_delete'),
    path('proformas/<int:pk>/pdf/', views.quote_pdf, name='quote_pdf'),

    # Enlaces públicos para el cliente (WhatsApp), no requieren sesión
    path('d/o/<uuid:token>/', views.public_order_pdf, name='public_order_pdf'),
    path('d/p/<uuid:token>/', views.public_quote_pdf, name='public_quote_pdf'),
]

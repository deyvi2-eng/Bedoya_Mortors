from django.urls import path
from . import views

app_name = 'workshop'

urlpatterns = [
    path('', views.workshop_dashboard, name='workshop_dashboard'),
    path('recepcion/nueva/', views.create_intake, name='create_intake'),
    path('recepcion/<int:order_id>/pdf/', views.generate_entry_pdf, name='generate_entry_pdf'),
    path('orden/<int:order_id>/estado/<str:new_status>/', views.change_status, name='change_status'),
    path('orden/<int:order_id>/liquidar/', views.service_checkout, name='service_checkout'),
    path('orden/<int:order_id>/facturar/', views.finalize_service_order, name='finalize_service_order'),
    
    # AGREGAR ESTA LÍNEA EXACTAMENTE:
    path('orden/<int:order_id>/eliminar/', views.delete_order, name='delete_order'),
]
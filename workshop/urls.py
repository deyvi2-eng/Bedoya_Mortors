from django.urls import path
from . import views

app_name = 'workshop' # ESTO ES VITAL PARA LOS ENLACES DE LOS BOTONES

urlpatterns = [
    path('dashboard/', views.workshop_dashboard, name='workshop_dashboard'),
    path('recepcion/nueva/', views.create_intake, name='create_intake'),
    path('recepcion/<int:order_id>/pdf/', views.generate_entry_pdf, name='generate_entry_pdf'),
    path('estado/<int:order_id>/<str:new_status>/', views.change_status, name='change_status'),
    
    # NUEVA RUTA: Liquidación y repuestos
    path('liquidacion/<int:order_id>/', views.service_checkout, name='service_checkout'),
    path('facturar/<int:order_id>/', views.finalize_service_order, name='finalize_service_order'), 
]
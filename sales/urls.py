from django.urls import path
from . import views

app_name = 'sales'

urlpatterns = [
    path('pos/', views.POSDashboardView.as_view(), name='pos_dashboard'),
    path('proformas/', views.ProformaListView.as_view(), name='proforma_list'),
    
    path('api/products/search/', views.POSProductSearchAPI.as_view(), name='api_product_search'),
    path('api/customers/search/', views.POSCustomerSearchAPI.as_view(), name='api_customer_search'),
    
    path('api/pending/', views.PendingDocumentsAPI.as_view(), name='api_pending_documents'),
    path('api/load/<int:sale_id>/', views.LoadDocumentAPI.as_view(), name='api_load_document'),
    path('api/delete/<int:sale_id>/', views.DeleteDocumentAPI.as_view(), name='api_delete_document'), # NUEVA RUTA
    
    path('api/process/', views.ProcessSaleAPI.as_view(), name='api_process_sale'),
    path('api/<int:sale_id>/pay/', views.RegisterPaymentAPI.as_view(), name='api_register_payment'),
    
    path('invoice/<str:invoice_number>/pdf/', views.InvoicePDFView.as_view(), name='invoice_pdf'),
]
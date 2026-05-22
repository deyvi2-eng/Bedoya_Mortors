from django.urls import path
from .views import ProcessCheckoutAPIView, InvoicePDFView, POSView

app_name = 'sales'

urlpatterns = [
path('pos/', POSView.as_view(), name='pos'),
path('api/checkout/', ProcessCheckoutAPIView.as_view(), name='api-checkout'),
path('invoice//pdf/', InvoicePDFView.as_view(), name='invoice-pdf'),
]
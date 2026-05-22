from django.urls import path
from .views import ExportSalesExcelView

app_name = 'reports'

urlpatterns = [
    path('export/sales/excel/', ExportSalesExcelView.as_view(), name='export-sales-excel'),
]
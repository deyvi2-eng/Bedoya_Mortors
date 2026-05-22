from django.urls import path
from .views import AuditLogView

app_name = 'audits'

urlpatterns = [
    path('logs/', AuditLogView.as_view(), name='logs'),
]
from django.urls import path
from .views import DashboardView

app_name = 'core'

urlpatterns = [
    # Usamos tu DashboardView que contiene toda la lógica y datos
    path('', DashboardView.as_view(), name='dashboard'),
]
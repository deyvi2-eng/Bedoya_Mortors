from django.urls import path
from django.views.generic import TemplateView
from django.contrib.auth.decorators import login_required

app_name = 'core'

urlpatterns = [
    # Esto cargará automáticamente tu plantilla de dashboard y exigirá iniciar sesión
    path('', login_required(TemplateView.as_view(template_name='dashboard/index.html')), name='dashboard'),
]
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from core.views import DashboardView

urlpatterns = [
    path('', DashboardView.as_view(), name='dashboard'),

    path('admin/', admin.site.urls),

    # LOGIN Y USUARIOS
    path('accounts/', include('accounts.urls')),

    # MODULOS
    path('sales/', include('sales.urls')),
    path('cash/', include('cash_register.urls')),
    path('reports/', include('reports.urls')),
    path('inventory/', include('inventory.urls')),
    path('customers/', include('customers.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
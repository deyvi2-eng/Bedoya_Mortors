from django.contrib import admin
from django.urls import path, include
from django.conf import settings # Importar settings
from django.conf.urls.static import static # Importar static
from core.views import DashboardView

urlpatterns = [
    path('', DashboardView.as_view(), name='dashboard'),
    path('admin/', admin.site.urls),
    path('sales/', include('sales.urls')),
    path('cash/', include('cash_register.urls')),
    path('reports/', include('reports.urls')),
    # Añadiremos la ruta del inventario en el siguiente paso
    path('inventory/', include('inventory.urls')), 
    
]

# Habilitar archivos multimedia (imágenes) en modo local
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
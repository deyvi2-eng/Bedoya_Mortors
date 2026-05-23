from django.contrib import admin
from django.urls import path, include
from django.http import HttpResponse
from django.core.management import call_command
from django.contrib.auth import get_user_model

# ==========================================
# SCRIPT TEMPORAL DE RESETEO
# ==========================================
def secret_reset_db(request):
    try:
        # 1. Borra absolutamente toda la base de datos sin preguntar
        call_command('flush', interactive=False)
        
        # 2. Crea automáticamente tu nuevo superusuario administrador
        User = get_user_model()
        User.objects.create_superuser(
            username='admin', 
            email='admin@bedoya.com', 
            password='admin123'
        )
        
        return HttpResponse("""
            <div style="font-family: sans-serif; padding: 40px;">
                <h1 style="color: #0d9488;">¡Base de datos formateada con éxito! ✅</h1>
                <p>Todo el sistema está en cero.</p>
                <h3>Nuevos datos de acceso:</h3>
                <ul>
                    <li><b>Usuario:</b> admin</li>
                    <li><b>Contraseña:</b> admin123</li>
                </ul>
                <h2 style="color: red; margin-top: 30px;">⚠️ IMPORTANTE: Borra este código de tu archivo config/urls.py inmediatamente y vuelve a subir a GitHub por seguridad.</h2>
                <a href="/accounts/login/">Ir a Iniciar Sesión</a>
            </div>
        """)
    except Exception as e:
        return HttpResponse(f"Hubo un error: {str(e)}")

# ==========================================
# TUS RUTAS ORIGINALES
# ==========================================
urlpatterns = [
    path('admin/', admin.site.urls),
    path('resetear-mi-sistema-secreto/', secret_reset_db), # <--- NUEVA RUTA TEMPORAL
    
    # ... Tus otras rutas (accounts, inventory, sales, etc.) ...
    path('', include('core.urls')),
    path('accounts/', include('accounts.urls')),
    path('inventory/', include('inventory.urls')),
    path('sales/', include('sales.urls')),
    path('cash/', include('cash_register.urls')),
    path('customers/', include('customers.urls')),
    path('audits/', include('audits.urls')),
]
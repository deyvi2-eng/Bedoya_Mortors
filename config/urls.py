from django.contrib import admin
from django.urls import path, include, re_path
from django.http import HttpResponse
from django.core.management import call_command
from django.contrib.auth import get_user_model
from django.conf import settings
from django.conf.urls.static import static

# ==========================================
# SCRIPT DE SUSPENSIÓN POR FALTA DE PAGO
# ==========================================
def suspension_view(request):
    html = """
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Sistema Suspendido</title>
        <style>
            body {
                display: flex;
                justify-content: center;
                align-items: center;
                height: 100vh;
                margin: 0;
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background-color: #f8d7da;
                color: #721c24;
                text-align: center;
            }
            .container {
                background: white;
                padding: 40px;
                border-radius: 10px;
                box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                max-width: 500px;
            }
            h1 { font-size: 24px; margin-bottom: 20px; }
            p { font-size: 16px; margin-bottom: 30px; }
            .whatsapp-btn {
                display: inline-block;
                padding: 12px 24px;
                background-color: #25D366;
                color: white;
                text-decoration: none;
                border-radius: 5px;
                font-weight: bold;
                font-size: 16px;
                transition: background-color 0.3s;
            }
            .whatsapp-btn:hover { background-color: #128C7E; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Este sistema está suspendido por falta de pago</h1>
            <p>Comuníquese con el desarrollador <strong>Deyvi Rivera</strong> para regularizar la situación.</p>
            <a href="https://wa.me/593987408528" class="whatsapp-btn" target="_blank">Contactar por WhatsApp</a>
        </div>
    </body>
    </html>
    """
    return HttpResponse(html, status=402)

# ==========================================
# RUTAS ACTIVAS (BLOQUEO TOTAL)
# ==========================================
urlpatterns = [
    # Intercepta absolutamente cualquier URL ingresada y muestra la pantalla de bloqueo
    re_path(r'^.*$', suspension_view),
]

# ==========================================
# CÓDIGO ORIGINAL COMENTADO (DESACTIVADO)
# ==========================================
'''
# SCRIPT TEMPORAL DE RESETEO
def secret_reset_db(request):
    try:
        # 1. Borra absolutamente toda la base de datos sin preguntar
        call_command('flush', interactive=False)
        
        # 2. Crea automaticamente el nuevo superusuario administrador
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
                <h2 style="color: red; margin-top: 30px;">⚠️ IMPORTANTE: Borrar este código del archivo config/urls.py inmediatamente y volver a subir a GitHub por seguridad.</h2>
                <a href="/accounts/login/">Ir a Iniciar Sesión</a>
            </div>
        """)
    except Exception as e:
        return HttpResponse(f"Hubo un error: {str(e)}")

# RUTAS ORIGINALES
# urlpatterns = [
#     path('admin/', admin.site.urls),
#     path('', include('core.urls')),
#     path('accounts/', include('accounts.urls')),
#     path('inventory/', include('inventory.urls')),
#     path('sales/', include('sales.urls')),
#     path('cash/', include('cash_register.urls')),
#     path('customers/', include('customers.urls')),
#     path('audits/', include('audits.urls')),
#     path('reports/', include('reports.urls')),
#     path('taller/', include('workshop.urls')),
# ]

# if settings.DEBUG:
#     urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
'''
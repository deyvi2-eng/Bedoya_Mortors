import os
from pathlib import Path
import environ
from decouple import config

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env(DEBUG=(bool, False))
environ.Env.read_env(os.path.join(BASE_DIR, '.env'))

SECRET_KEY = env('SECRET_KEY')
#DEBUG = env('DEBUG')
DEBUG = True 
ALLOWED_HOSTS = ['localhost', '127.0.0.1', '.onrender.com']

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # --- AÑADE ESTAS DOS LÍNEAS ---
    'cloudinary_storage',
    'cloudinary',

    # Tus aplicaciones
    'accounts',
    'core',
    'inventory',
    'sales',
    'customers',
    'cash_register',
    'reports',
    'audits',
    'notifications',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'audits.middleware.SecurityAuditMiddleware'
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

DATABASES = {
    'default': env.db('DATABASE_URL')
}

AUTH_USER_MODEL = 'accounts.User'

LANGUAGE_CODE = 'es-ec'
TIME_ZONE = 'America/Guayaquil'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = env('EMAIL_HOST_USER', default='correo_falso@gmail.com')
EMAIL_HOST_PASSWORD = env('EMAIL_HOST_PASSWORD', default='clave')

# Correo que recibirá las alertas de inventario
ADMIN_ALERTS_EMAIL = env('ADMIN_ALERTS_EMAIL', default=EMAIL_HOST_USER)
# Al final de config/settings.py agregue o modifique:
LOGIN_URL = '/accounts/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/accounts/login/'

# ==========================================
# CONFIGURACIONES DE SEGURIDAD EXTREMA (PRODUCCIÓN)
# ==========================================
# Nota: Si pruebas en local (127.0.0.1), asegúrate de que DEBUG=True en tu .env para que el sistema no te bloquee por no tener HTTPS.
if not DEBUG:
    # 1. Fuerza que todo el tráfico pase por HTTPS (Candado verde)
    SECURE_SSL_REDIRECT = True
    
    # 2. Protege las cookies para que no puedan ser robadas (Session Hijacking)
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    CSRF_COOKIE_HTTPONLY = True
    
    # 3. Previene ataques de Clickjacking (que metan tu web en un iframe oculto)
    X_FRAME_OPTIONS = 'DENY'
    
    # 4. Protección contra Cross-Site Scripting (XSS) y MIME-Sniffing
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    
    # 5. HSTS (Fuerza conexiones seguras por 1 año)
    SECURE_HSTS_SECONDS = 31536000  # 1 año
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True

# La sesión caduca automáticamente si cierran el navegador (Seguridad en Puntos de Venta físicos)
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SESSION_COOKIE_AGE = 43200  # Sesión expira a las 12 horas de inactividad
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'



# ==========================================
# CONFIGURACIÓN DE CLOUDINARY (FOTOS GRATIS)
# ==========================================

CLOUDINARY_STORAGE = {
    'CLOUD_NAME': env('CLOUD_NAME'),
    'API_KEY': env('API_KEY'),
    'API_SECRET': env('API_SECRET'),
    'SECURE': True
}
STORAGES = {
    "default": {
        "BACKEND": "cloudinary_storage.storage.MediaCloudinaryStorage",
    },
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
}

# Mantenemos las URLs base por si acaso
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'
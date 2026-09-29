from django.conf import settings
from django.shortcuts import redirect

FURNITURE_PREFIX = '/muebles/'

# Rutas que cualquier usuario puede visitar sin importar su empresa
ALWAYS_ALLOWED = ('/accounts/login/', '/accounts/logout/', '/static/', '/media/', '/favicon.ico')


class BusinessAccessMiddleware:
    """
    Separa los entornos de cada negocio:
    - Usuarios con rol MUEBLES solo pueden navegar dentro de /muebles/.
    - Usuarios de Bedoya Motors (no administradores) no pueden entrar a /muebles/.
    - El administrador (ADMIN) puede ver ambos sistemas.
    - Los enlaces públicos /muebles/d/... (PDF para el cliente) no requieren sesión.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path
        user = getattr(request, 'user', None)

        if user is not None and user.is_authenticated and not path.startswith(ALWAYS_ALLOWED):
            role = getattr(user, 'role', '')
            is_public_doc = path.startswith(FURNITURE_PREFIX + 'd/')

            if role == 'MUEBLES' and not path.startswith(FURNITURE_PREFIX):
                return redirect(FURNITURE_PREFIX)

            if role not in ('MUEBLES', 'ADMIN') and not user.is_superuser \
                    and path.startswith(FURNITURE_PREFIX) and not is_public_doc:
                return redirect(settings.LOGIN_REDIRECT_URL)

        return self.get_response(request)

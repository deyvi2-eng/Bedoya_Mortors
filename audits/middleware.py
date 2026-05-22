from .models import AuditLog

class SecurityAuditMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Monitorear únicamente peticiones que modifican datos
        if request.method in ['POST', 'PUT', 'PATCH', 'DELETE']:
            # Ignorar rutas públicas o de login para no saturar los logs
            if not request.path.startswith('/admin/login/'):
                
                # Obtener la IP real del usuario
                x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
                if x_forwarded_for:
                    ip = x_forwarded_for.split(',')[0]
                else:
                    ip = request.META.get('REMOTE_ADDR')

                user = request.user if request.user.is_authenticated else None

                # Registrar la acción asíncronamente (en producción) o sincrónicamente
                AuditLog.objects.create(
                    user=user,
                    action=request.method,
                    path=request.path,
                    ip_address=ip
                )

        response = self.get_response(request)
        return response
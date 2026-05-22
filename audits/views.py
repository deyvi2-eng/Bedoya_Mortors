from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from .models import AuditLog

class AuditLogView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'audits/logs.html'

    def test_func(self):
        # Validación de seguridad: Solo el ADMIN puede ver la auditoría
        return self.request.user.role == 'ADMIN'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Traemos los últimos 300 movimientos para mantener la carga rápida
        context['logs'] = AuditLog.objects.select_related('user').order_by('-timestamp')[:300]
        return context
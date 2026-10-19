from core.pagination import paginate
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from datetime import datetime

from django.contrib.auth import get_user_model

from .models import AuditLog

User = get_user_model()

class AuditLogView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    template_name = 'audits/logs.html'

    def test_func(self):
        # Validación de seguridad: Solo el ADMIN puede ver la auditoría
        return self.request.user.role == 'ADMIN'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        logs = AuditLog.objects.select_related('user').order_by('-timestamp')

        # Filtros en el servidor (fecha y colaborador) para que funcionen con la paginación
        selected_date = self.request.GET.get('fecha', '').strip()
        if selected_date:
            try:
                logs = logs.filter(timestamp__date=datetime.strptime(selected_date, '%Y-%m-%d').date())
            except ValueError:
                selected_date = ''
        selected_user = self.request.GET.get('usuario', '').strip()
        if selected_user.isdigit():
            logs = logs.filter(user_id=int(selected_user))
        else:
            selected_user = ''

        # Paginado para mantener la carga rápida sin perder el historial antiguo
        context['logs'] = paginate(self.request, logs, per_page=50)
        context['selected_date'] = selected_date
        context['selected_user'] = selected_user
        context['log_users'] = User.objects.filter(
            id__in=AuditLog.objects.exclude(user=None).values('user_id').distinct()
        ).order_by('first_name', 'username')
        return context
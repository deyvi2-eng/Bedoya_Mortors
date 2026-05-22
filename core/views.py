from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Sum, Count
from django.utils.timezone import now
from sales.models import Sale
from inventory.models import Product
from customers.models import Customer
import json

class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'dashboard/index.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today = now().date()
        
        # KPI Cards
        ventas_hoy = Sale.objects.filter(created_at__date=today, is_voided=False)
        context['ingresos_hoy'] = ventas_hoy.aggregate(Sum('total'))['total__sum'] or 0.00
        context['operaciones_hoy'] = ventas_hoy.count()
        context['total_clientes'] = Customer.objects.filter(is_active=True).count()
        
        # Alertas de Stock
        context['stock_critico'] = Product.objects.filter(stock_actual__lte=2, is_active=True).count()

        # Datos para Gráfico de Ventas (Últimos 7 días)
        # Para simplificar, enviaremos datos estáticos estructurados. En producción se agrupa por fecha.
        context['chart_labels'] = json.dumps(["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"])
        context['chart_data'] = json.dumps([120, 250, 180, 320, 450, 600, 210])

        # Últimas transacciones
        context['recent_sales'] = Sale.objects.filter(is_voided=False).order_by('-created_at')[:5]

        return context
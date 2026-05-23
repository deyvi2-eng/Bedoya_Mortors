from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Sum
from django.db.models.functions import TruncDate
from django.utils.timezone import now
from datetime import datetime, time, timedelta
from sales.models import Sale
from inventory.models import Product
from customers.models import Customer
import json

class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'dashboard/index.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # 1. Obtener parámetros de fecha del selector visual
        start_date_str = self.request.GET.get('start_date')
        end_date_str = self.request.GET.get('end_date')
        
        # Filtramos ventas procesadas (no anuladas)
        ventas_base = Sale.objects.filter(is_voided=False)
        
        # Seguridad: Si es vendedor, solo ve sus propias ventas
        if self.request.user.role == 'SELLER':
            ventas_base = ventas_base.filter(seller=self.request.user)

        # 2. Configurar el rango de fechas
        if start_date_str and end_date_str:
            try:
                start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
                end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
            except ValueError:
                start_date = end_date = now().date()
        else:
            start_date = end_date = now().date()

        # Mantener los filtros en la vista
        context['start_date'] = start_date.strftime("%Y-%m-%d")
        context['end_date'] = end_date.strftime("%Y-%m-%d")

        # 3. Calcular KPI según las fechas seleccionadas
        ventas_rango = ventas_base.filter(
            created_at__gte=datetime.combine(start_date, time.min),
            created_at__lte=datetime.combine(end_date, time.max)
        )
        
        context['ingresos_hoy'] = ventas_rango.aggregate(Sum('total'))['total__sum'] or 0.00
        context['operaciones_hoy'] = ventas_rango.count()
        context['total_clientes'] = Customer.objects.filter(is_active=True).count()
        context['stock_critico'] = Product.objects.filter(stock_actual__lte=2, is_active=True).count()
        context['recent_sales'] = ventas_base.order_by('-created_at')[:5]

        # 4. Datos reales para el Gráfico (Últimos 7 días respecto a la fecha final)
        chart_start = end_date - timedelta(days=6)
        ventas_chart = ventas_base.filter(
            created_at__gte=datetime.combine(chart_start, time.min),
            created_at__lte=datetime.combine(end_date, time.max)
        ).annotate(date=TruncDate('created_at')).values('date').annotate(diario=Sum('total')).order_by('date')

        # Estructurar diccionario para evitar días en blanco sin ventas
        fechas_dict = { (chart_start + timedelta(days=i)): 0.00 for i in range(7) }
        for v in ventas_chart:
            if v['date'] in fechas_dict:
                fechas_dict[v['date']] = float(v['diario'])

        dias_semana = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]
        labels = [f"{dias_semana[d.weekday()]} {d.day}" for d in fechas_dict.keys()]
        data = list(fechas_dict.values())

        context['chart_labels'] = json.dumps(labels)
        context['chart_data'] = json.dumps(data)

        return context
from decimal import Decimal
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
# Se añaden Case, When y Value para la condicional en base de datos
from django.db.models import Sum, F, ExpressionWrapper, DecimalField, Case, When, Value
from django.db.models.functions import TruncDate
from django.utils.timezone import now
from datetime import datetime, time, timedelta

from sales.models import Sale, SaleDetail
from inventory.models import Product
from customers.models import Customer
from cash_register.models import CashSession
import json

class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'dashboard/index.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        start_date_str = self.request.GET.get('start_date')
        end_date_str = self.request.GET.get('end_date')
        
        ventas_base = Sale.objects.filter(is_voided=False)
        
        if getattr(self.request.user, 'role', '') == 'SELLER':
            ventas_base = ventas_base.filter(seller=self.request.user)

        if start_date_str and end_date_str:
            try:
                start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
                end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
            except ValueError:
                start_date = end_date = now().date()
        else:
            start_date = end_date = now().date()

        context['start_date'] = start_date.strftime("%Y-%m-%d")
        context['end_date'] = end_date.strftime("%Y-%m-%d")

        ventas_rango = ventas_base.filter(
            created_at__gte=datetime.combine(start_date, time.min),
            created_at__lte=datetime.combine(end_date, time.max)
        )
        
        context['ingresos_hoy'] = ventas_rango.aggregate(Sum('total'))['total__sum'] or Decimal('0.00')
        context['operaciones_hoy'] = ventas_rango.count()
        context['total_clientes'] = Customer.objects.filter(is_active=True).count()
        context['stock_critico'] = Product.objects.filter(stock_actual__lte=2, is_active=True).count()
        context['recent_sales'] = ventas_base.order_by('-created_at')[:5]

        is_admin = getattr(self.request.user, 'role', '') == 'ADMIN' or self.request.user.is_superuser
        context['is_admin'] = is_admin

        if is_admin:
            # 1. Efectivo Físico Seguro
            # Se suma el fondo de las cajas abiertas y TODA venta en efectivo del día
            cajas_abiertas = CashSession.objects.filter(is_open=True)
            fondo_inicial = cajas_abiertas.aggregate(Sum('opening_balance'))['opening_balance__sum'] or Decimal('0.00')
            
            efectivo_ventas = Sale.objects.filter(
                payment_method='CASH',
                is_voided=False,
                created_at__date=now().date()
            ).aggregate(Sum('total'))['total__sum'] or Decimal('0.00')
            
            context['dinero_actual_caja'] = fondo_inicial + efectivo_ventas

            # INVENTARIO
            productos_en_stock = Product.objects.filter(stock_actual__gt=0)

            # 2. Capital Stock (Costo * Cantidad Física)
            # Evalúa si es ML (Líquido) para dividir entre 1000, caso contrario multiplica normal
            capital = productos_en_stock.aggregate(
                total=Sum(
                    Case(
                        When(unit_type='ML', then=ExpressionWrapper(
                            (F('stock_actual') / Value(Decimal('1000.00'))) * F('purchase_price'),
                            output_field=DecimalField()
                        )),
                        default=ExpressionWrapper(
                            F('stock_actual') * F('purchase_price'),
                            output_field=DecimalField()
                        ),
                        output_field=DecimalField()
                    )
                )
            )['total'] or Decimal('0.00')
            context['capital_invertido'] = capital

            # 3. Total Público (Precio Venta * Cantidad Física)
            publico = productos_en_stock.aggregate(
                total=Sum(
                    Case(
                        When(unit_type='ML', then=ExpressionWrapper(
                            (F('stock_actual') / Value(Decimal('1000.00'))) * F('sale_price'),
                            output_field=DecimalField()
                        )),
                        default=ExpressionWrapper(
                            F('stock_actual') * F('sale_price'),
                            output_field=DecimalField()
                        ),
                        output_field=DecimalField()
                    )
                )
            )['total'] or Decimal('0.00')
            context['valor_publico'] = publico

            # 4. Ganancia Proyectada (Resta Directa)
            context['ganancia_proyectada'] = publico - capital

        # Gráfico de 7 días
        chart_start = end_date - timedelta(days=6)
        ventas_chart = ventas_base.filter(
            created_at__gte=datetime.combine(chart_start, time.min),
            created_at__lte=datetime.combine(end_date, time.max)
        ).annotate(date=TruncDate('created_at')).values('date').annotate(diario=Sum('total')).order_by('date')

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
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated  # <-- ESTA ES LA IMPORTACIÓN QUE FALTABA
from django.db.models import Sum
from django.utils.timezone import now
from django.shortcuts import get_object_or_404

from .models import CashSession
from sales.models import Sale  # <-- IMPORTACIÓN DE VENTAS

# ==========================================
# DASHBOARD DE CAJA DIARIA
# ==========================================
class CashDashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'cash_register/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        active_session = CashSession.objects.filter(user=user, is_open=True).first()
        context['active_session'] = active_session
        
        # SI HAY CAJA ABIERTA, CALCULAMOS EL RESUMEN EN VIVO
        if active_session:
            sales = Sale.objects.filter(cash_session=active_session, is_voided=False)
            
            context['current_cash'] = sales.filter(payment_method='CASH').aggregate(Sum('total'))['total__sum'] or 0.00
            context['current_transfer'] = sales.filter(payment_method='TRANSFER').aggregate(Sum('total'))['total__sum'] or 0.00
            context['current_card'] = sales.filter(payment_method='CARD').aggregate(Sum('total'))['total__sum'] or 0.00
            
            # El efectivo esperado es SOLO el dinero en billetes y monedas
            context['expected_cash'] = float(active_session.opening_balance) + float(context['current_cash'])
            context['total_sales_count'] = sales.count()
        
        history = CashSession.objects.filter(is_open=False)
        if user.role != 'ADMIN':
            history = history.filter(user=user)
            
        context['history'] = history.order_by('-closing_time')[:10]
        return context

# ==========================================
# API: ABRIR CAJA
# ==========================================
class OpenCashAPI(APIView):
    def post(self, request, *args, **kwargs):
        user = request.user
        if CashSession.objects.filter(user=user, is_open=True).exists():
            return Response({"error": "Ya tienes una caja abierta. Ciérrala primero."}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            opening_balance = float(request.data.get('opening_balance', 0))
            if opening_balance < 0:
                raise ValueError()
        except:
            return Response({"error": "Monto inicial inválido."}, status=status.HTTP_400_BAD_REQUEST)

        CashSession.objects.create(user=user, opening_balance=opening_balance)
        return Response({"message": "Caja abierta exitosamente."}, status=status.HTTP_201_CREATED)

# ==========================================
# API: CERRAR CAJA
# ==========================================
class CloseCashAPI(APIView):
    def post(self, request, *args, **kwargs):
        user = request.user
        session = CashSession.objects.filter(user=user, is_open=True).first()
        
        if not session:
            return Response({"error": "No hay ninguna caja abierta para cerrar."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            actual_balance = float(request.data.get('actual_balance', 0))
            observations = request.data.get('observations', '')
        except:
            return Response({"error": "Monto físico reportado es inválido."}, status=status.HTTP_400_BAD_REQUEST)

        # Agrupar ventas
        sales = Sale.objects.filter(cash_session=session, is_voided=False)
        
        cash_sales = sales.filter(payment_method='CASH').aggregate(Sum('total'))['total__sum'] or 0.00
        transfer_sales = sales.filter(payment_method='TRANSFER').aggregate(Sum('total'))['total__sum'] or 0.00
        card_sales = sales.filter(payment_method='CARD').aggregate(Sum('total'))['total__sum'] or 0.00
        
        expected_balance = float(session.opening_balance) + float(cash_sales)
        difference = actual_balance - expected_balance

        # Guardar el cierre
        session.closing_time = now()
        session.total_cash = cash_sales
        session.total_transfer = transfer_sales
        session.total_card = card_sales
        session.expected_balance = expected_balance
        session.actual_balance = actual_balance
        session.difference = difference
        session.observations = observations
        session.is_open = False
        session.save()

        return Response({"message": "Caja cerrada correctamente.", "difference": difference}, status=status.HTTP_200_OK)

# ==========================================
# API: DETALLES DE VENTAS PARA EL MODAL
# ==========================================
class CashSessionDetailAPI(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, session_id, *args, **kwargs):
        session = get_object_or_404(CashSession, id=session_id)
        
        if request.user.role != 'ADMIN' and session.user != request.user:
            return Response({"error": "Acceso denegado"}, status=status.HTTP_403_FORBIDDEN)
        
        sales = Sale.objects.filter(cash_session=session, is_voided=False).select_related('customer').order_by('created_at')
        
        sales_data = [{
            "invoice": s.invoice_number,
            "time": s.created_at.strftime("%H:%M"),
            "customer": f"{s.customer.first_name} {s.customer.last_name}",
            "method": s.get_payment_method_display(),
            "total": float(s.total)
        } for s in sales]

        return Response({"sales": sales_data})

# ==========================================
# VISTA: GENERADOR DE REPORTE PDF/IMPRESIÓN
# ==========================================
class CashSessionReportView(LoginRequiredMixin, TemplateView):
    template_name = 'cash_register/report.html'

    def get_context_data(self, session_id, **kwargs):
        context = super().get_context_data(**kwargs)
        session = get_object_or_404(CashSession, id=session_id)
        
        if self.request.user.role != 'ADMIN' and session.user != self.request.user:
            raise PermissionError("Acceso denegado")
            
        context['session'] = session
        context['sales'] = Sale.objects.filter(cash_session=session, is_voided=False).order_by('created_at')
        return context
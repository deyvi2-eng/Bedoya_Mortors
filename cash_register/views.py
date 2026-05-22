from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from django.db import transaction
from .models import CashSession

class CashDashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'cash_register/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Buscar si el usuario actual tiene una caja abierta
        context['active_session'] = CashSession.objects.filter(
            user=self.request.user, 
            status=CashSession.Status.OPEN
        ).first()
        
        # Historial de las últimas 5 cajas de este usuario
        context['history'] = CashSession.objects.filter(
            user=self.request.user
        ).order_by('-opening_time')[:5]
        
        return context

class OpenCashSessionAPI(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        opening_balance = request.data.get('opening_balance', 0)
        
        # Verificar que no tenga ya una caja abierta
        if CashSession.objects.filter(user=request.user, status=CashSession.Status.OPEN).exists():
            return Response({"error": "Ya tienes una sesión de caja abierta."}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            CashSession.objects.create(
                user=request.user,
                opening_balance=float(opening_balance),
                system_balance=0.00
            )
            return Response({"message": "Caja abierta exitosamente."}, status=status.HTTP_201_CREATED)
        except ValueError:
            return Response({"error": "Monto de apertura inválido."}, status=status.HTTP_400_BAD_REQUEST)

class CloseCashSessionAPI(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        declared_balance = request.data.get('declared_balance')
        observations = request.data.get('observations', '')

        if declared_balance is None:
            return Response({"error": "Debe ingresar el dinero físico contado."}, status=status.HTTP_400_BAD_REQUEST)

        session = CashSession.objects.filter(user=request.user, status=CashSession.Status.OPEN).first()
        if not session:
            return Response({"error": "No tienes ninguna sesión de caja abierta."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            with transaction.atomic():
                declared_balance = float(declared_balance)
                # El total esperado es el saldo inicial + las ventas netas en efectivo/general
                expected_total = float(session.opening_balance) + float(session.system_balance)
                
                # Calcular diferencia (Sobrante o Faltante)
                discrepancy = declared_balance - expected_total

                # Cerrar la caja
                session.closing_time = timezone.now()
                session.declared_balance = declared_balance
                session.discrepancy = discrepancy
                session.status = CashSession.Status.CLOSED
                session.observations = observations
                session.save()

                return Response({
                    "message": "Arqueo realizado y caja cerrada correctamente.",
                    "discrepancy": discrepancy
                }, status=status.HTTP_200_OK)
        except ValueError:
            return Response({"error": "Formato de dinero inválido."}, status=status.HTTP_400_BAD_REQUEST)
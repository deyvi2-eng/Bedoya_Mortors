from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404
from .models import Customer
from sales.models import Sale, SaleDetail

class CustomerManagementView(LoginRequiredMixin, TemplateView):
    template_name = 'customers/manage.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['customers'] = Customer.objects.all().order_by('-created_at')
        return context

class CustomerCreateAPI(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        try:
            data = request.data
            
            # CRÍTICO: Si la cédula viene vacía, la convertimos en None para evitar el choque de unique=True
            cedula_input = data.get('cedula', '').strip()
            if not cedula_input:
                cedula_input = None

            # Crear instancia
            customer = Customer(
                cedula=cedula_input,
                first_name=data.get('first_name'),
                last_name=data.get('last_name'),
                phone=data.get('phone'),
                whatsapp=data.get('whatsapp', ''),
                email=data.get('email', ''),
                address=data.get('address', ''),
                city=data.get('city', ''),
                observations=data.get('observations', '')
            )
            
            # Ejecuta clean() para disparar validadores
            customer.full_clean() 
            customer.save()

            return Response({
                "message": "Cliente registrado exitosamente.",
                "id": customer.id
            }, status=status.HTTP_201_CREATED)

        except ValidationError as e:
            error_msg = list(e.message_dict.values())[0][0] if hasattr(e, 'message_dict') else str(e.messages[0])
            return Response({"error": error_msg}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            if 'unique constraint' in str(e).lower() or 'unique' in str(e).lower():
                return Response({"error": "Ya existe un cliente con esta cédula registrada."}, status=status.HTTP_400_BAD_REQUEST)
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class CustomerToggleAPI(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, customer_id, *args, **kwargs):
        # SOLO ADMIN puede desactivar clientes
        if request.user.role != 'ADMIN':
            return Response({"error": "Acceso denegado. Solo administradores pueden eliminar/desactivar clientes."}, status=status.HTTP_403_FORBIDDEN)
            
        customer = get_object_or_404(Customer, id=customer_id)
        customer.is_active = not customer.is_active
        customer.save()
        
        return Response({"message": "Estado del cliente actualizado."})
    
class CustomerHistoryAPI(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, customer_id, *args, **kwargs):
        customer = get_object_or_404(Customer, id=customer_id)
        # Buscar todas las ventas del cliente, ordenadas por la más reciente
        sales = Sale.objects.filter(customer=customer).order_by('-created_at')
        
        history = []
        for sale in sales:
            details = SaleDetail.objects.filter(sale=sale)
            items = [{
                "product": d.product.name,
                "code": d.product.code,
                "qty": d.quantity,
                "price": float(d.unit_price),
                "subtotal": float(d.subtotal)
            } for d in details]
            
            history.append({
                "invoice": sale.invoice_number,
                "date": sale.created_at.strftime("%d %b %Y, %H:%M"),
                "total": float(sale.total),
                "method": sale.get_payment_method_display(),
                "status": "ANULADA" if sale.is_voided else "PROCESADA",
                "items": items
            })
        
        return Response({
            "customer": f"{customer.first_name} {customer.last_name}",
            "ci": customer.cedula,
            "total_spent": sum(s['total'] for s in history if s['status'] == "PROCESADA"),
            "total_orders": len(history),
            "history": history
        })
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.db import transaction
from .models import Sale, SaleDetail
from inventory.models import Product
from customers.models import Customer
from cash_register.models import CashSession
import uuid
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from .services import generate_invoice_pdf
from django.views.generic import TemplateView
from sales.services import generate_invoice_pdf
from notifications.services import send_invoice_email_async

class ProcessCheckoutAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        data = request.data
        customer_id = data.get('customer_id')
        payment_method = data.get('payment_method', 'CASH')
        items = data.get('items', [])

        if not items:
            return Response({"error": "El carrito está vacío."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            with transaction.atomic():
                # 1. Validar Caja Abierta del usuario
                cash_session = CashSession.objects.filter(user=request.user, status=CashSession.Status.OPEN).first()
                if not cash_session:
                    return Response({"error": "Debe abrir caja antes de registrar ventas."}, status=status.HTTP_403_FORBIDDEN)

                # 2. Obtener Cliente
                customer = Customer.objects.get(id=customer_id)

                # 3. Crear cabecera de la factura temporalmente
                # Generamos un invoice provisorio. En un caso real, puede usar secuencias de base de datos.
                temp_invoice = f"FAC-{uuid.uuid4().hex[:6].upper()}"
                
                sale = Sale.objects.create(
                    invoice_number=temp_invoice,
                    customer=customer,
                    seller=request.user,
                    cash_session=cash_session,
                    payment_method=payment_method
                )

                total_sale = 0
                
                # 4. Procesar cada item recalculando precios en backend (Seguridad)
                for item in items:
                    # Bloqueamos el producto específico contra concurrencia
                    product = Product.objects.select_for_update().get(id=item['product_id'])
                    quantity = int(item['quantity'])

                    if product.stock_actual < quantity:
                        raise ValueError(f"Stock insuficiente para {product.name}. Disponible: {product.stock_actual}")

                    unit_price = product.sale_price
                    subtotal = unit_price * quantity
                    total_sale += subtotal

                    # Esto dispara el Signal que descuenta stock automáticamente
                    SaleDetail.objects.create(
                        sale=sale,
                        product=product,
                        quantity=quantity,
                        unit_price=unit_price,
                        subtotal=subtotal
                    )

                # 5. Actualizar totales de la factura
                sale.subtotal = total_sale # Sin IVA temporalmente
                sale.total = total_sale
                sale.save()

                # 6. Actualizar el saldo de la caja en sistema
                cash_session.system_balance += sale.total
                cash_session.save()




                    # -- NUEVO: Generar PDF y Enviar Correo en Segundo Plano --
                try:
                    pdf_bytes = generate_invoice_pdf(sale)
                    send_invoice_email_async(
                        customer_email=customer.email,
                        customer_name=f"{customer.first_name} {customer.last_name}",
                        invoice_number=sale.invoice_number,
                        pdf_bytes=pdf_bytes
                    )
                except Exception as e:
                        # Si falla el envío de correo, la venta igual se completa
                    print(f"Alerta: Venta guardada pero correo no enviado. {e}")

                    # Retorno exitoso al Frontend
                return Response({
                    "message": "Venta procesada exitosamente.",
                    "invoice_number": sale.invoice_number,
                    "total": str(sale.total)
                }, status=status.HTTP_201_CREATED)


        except Customer.DoesNotExist:
            return Response({"error": "Cliente no encontrado."}, status=status.HTTP_404_NOT_FOUND)
        except Product.DoesNotExist:
            return Response({"error": "Un producto del carrito no existe."}, status=status.HTTP_404_NOT_FOUND)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": "Ocurrió un error inesperado al procesar la venta."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class InvoicePDFView(LoginRequiredMixin, View):
    """
    Vista para generar y retornar el PDF de una factura específica.
    Solo accesible para usuarios autenticados.
    """
    def get(self, request, invoice_number, *args, **kwargs):
        # Obtener la venta asegurando que existe
        sale = get_object_or_404(Sale, invoice_number=invoice_number)
        
        # Llamar al servicio de generación
        pdf_file = generate_invoice_pdf(sale, request)
        
        # Configurar la respuesta HTTP para servir el archivo PDF
        response = HttpResponse(pdf_file, content_type='application/pdf')
        # Use 'attachment; filename=...' para forzar la descarga, 
        # o 'inline; filename=...' para abrirlo en el navegador.
        response['Content-Disposition'] = f'inline; filename="Factura_{sale.invoice_number}.pdf"'
        
        return response
    
class POSView(LoginRequiredMixin, TemplateView):
    template_name = 'sales/pos.html'

def get_context_data(self, **kwargs):
    context = super().get_context_data(**kwargs)
    # Solo enviamos clientes activos y productos que tengan stock disponible
    context['customers'] = Customer.objects.filter(is_active=True).order_by('last_name')
    context['products'] = Product.objects.filter(is_active=True, stock_actual__gt=0).order_by('name')
    return context
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db import transaction
from django.db.models import Q
from django.utils.timezone import now
import uuid
from django.shortcuts import get_object_or_404

# Importaciones de otras apps
from inventory.models import Product, StockMovement
from customers.models import Customer
from cash_register.models import CashSession  # <-- IMPORTACIÓN CLAVE DE LA CAJA
from .models import Sale, SaleDetail

# ==========================================
# VISTA PRINCIPAL DEL PUNTO DE VENTA (UI)
# ==========================================
class POSDashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'sales/pos.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context

# ==========================================
# API: BUSCAR PRODUCTOS PARA EL POS
# ==========================================
class POSProductSearchAPI(APIView):
    def get(self, request, *args, **kwargs):
        query = request.GET.get('q', '').strip()
        
        if not query:
            return Response({"products": []})

        products = Product.objects.filter(
            Q(code__iexact=query) | 
            Q(barcode__iexact=query) | 
            Q(name__icontains=query),
            is_active=True
        ).order_by('name')[:20]

        results = []
        for p in products:
            results.append({
                "id": p.id,
                "code": p.code,
                "name": p.name,
                "price": float(p.sale_price),
                "stock": p.stock_actual
            })
            
        return Response({"products": results}, status=status.HTTP_200_OK)

# ==========================================
# API: BUSCAR CLIENTES PARA EL POS
# ==========================================
class POSCustomerSearchAPI(APIView):
    def get(self, request, *args, **kwargs):
        query = request.GET.get('q', '').strip()
        
        if not query:
            return Response({"customers": []})

        customers = Customer.objects.filter(
            Q(cedula__startswith=query) | 
            Q(first_name__icontains=query) | 
            Q(last_name__icontains=query),
            is_active=True
        )[:10]

        results = [{"id": c.id, "cedula": c.cedula, "name": f"{c.first_name} {c.last_name}"} for c in customers]
        return Response({"customers": results}, status=status.HTTP_200_OK)

# ==========================================
# API: PROCESAR LA VENTA (CHECKOUT)
# ==========================================
class ProcessSaleAPI(APIView):
    def post(self, request, *args, **kwargs):
        # 1. VERIFICACIÓN CRÍTICA: ¿Tiene el vendedor una caja abierta?
        active_session = CashSession.objects.filter(user=request.user, is_open=True).first()
        
        if not active_session:
            return Response(
                {"error": "Debe aperturar su caja diaria antes de poder facturar. Vaya al módulo de Caja."}, 
                status=status.HTTP_403_FORBIDDEN
            )

        data = request.data
        customer_id = data.get('customer_id')
        payment_method = data.get('payment_method', 'CASH')
        items = data.get('items', [])
        
        if not items or not customer_id:
            return Response({"error": "Faltan datos de la venta o cliente."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            with transaction.atomic():
                customer = Customer.objects.get(id=customer_id)
                
                # Generar número de factura único provisional
                invoice_number = f"DOC-{now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:6].upper()}"

                # 2. Crear Venta Cabecera (Enlazada a la caja abierta)
                sale = Sale.objects.create(
                    invoice_number=invoice_number,
                    customer=customer,
                    seller=request.user,
                    payment_method=payment_method,
                    cash_session=active_session,  # <--- VINCULACIÓN CON LA CAJA
                    subtotal=0, iva=0, total=0
                )

                subtotal_calc = 0
                
                # 3. Procesar Detalles y Descontar Stock
                for item in items:
                    # select_for_update bloquea la fila para evitar ventas concurrentes que rompan el stock
                    product = Product.objects.select_for_update().get(id=item['id'])
                    qty = int(item['quantity'])
                    
                    if product.stock_actual < qty:
                        raise ValueError(f"Stock insuficiente para {product.name}. Disponible: {product.stock_actual}")

                    # Descuento de inventario
                    product.stock_actual -= qty
                    product.save()

                    # Registro de movimiento de salida
                    StockMovement.objects.create(
                        product=product, movement_type='OUT', quantity=qty,
                        description=f"Venta Factura: {invoice_number}", user=request.user
                    )

                    line_total = float(product.sale_price) * qty
                    subtotal_calc += line_total

                    SaleDetail.objects.create(
                        sale=sale, product=product, quantity=qty,
                        unit_price=product.sale_price, subtotal=line_total
                    )

                # 4. Actualizar Totales de la Venta (IVA 15% - Ecuador)
                iva_calc = subtotal_calc * 0.15
                total_calc = subtotal_calc + iva_calc

                sale.subtotal = subtotal_calc
                sale.iva = iva_calc
                sale.total = total_calc
                sale.save()

            return Response({
                "message": "Venta procesada con éxito",
                "invoice": sale.invoice_number,
                "total": sale.total
            }, status=status.HTTP_201_CREATED)

        except ValueError as ve:
            # Captura errores controlados (ej: falta de stock)
            return Response({"error": str(ve)}, status=status.HTTP_400_BAD_REQUEST)
        except Customer.DoesNotExist:
            return Response({"error": "Cliente no válido."}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            # Captura cualquier otro error de base de datos
            return Response({"error": f"Error interno al procesar la venta: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
class InvoicePDFView(LoginRequiredMixin, TemplateView):
    template_name = 'sales/invoice_pdf.html'

    def get_context_data(self, invoice_number, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Obtener la venta y sus detalles
        sale = get_object_or_404(Sale, invoice_number=invoice_number)
        
        context['sale'] = sale
        context['customer'] = sale.customer
        context['details'] = SaleDetail.objects.filter(sale=sale)
        
        # Datos estáticos de la empresa (se pueden mover a un modelo en el futuro)
        context['company'] = {
            "name": "BEDOYA MOTORS",
            "ruc": "17XXXXXXXX001",
            "address": "Sangolquí",
            "city": "Pichincha, Ecuador",
            "phone": "099 999 9999",
            "email": "contacto@bedoyamotors.com"
        }
        
        return context
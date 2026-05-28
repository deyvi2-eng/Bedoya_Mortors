from decimal import Decimal
import uuid

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils.timezone import now
from django.views.generic import TemplateView

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

# Importaciones de otras apps
from inventory.models import Product, StockMovement
from customers.models import Customer
from cash_register.models import CashSession

# Modelos de ventas
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
            Q(name__icontains=query) |
            Q(description__icontains=query), # Buscamos también por descripción
            is_active=True
        ).order_by('name')[:24] # Traemos hasta 24 para llenar bien la pantalla

        results = []
        for p in products:
            results.append({
                "id": p.id,
                "code": p.code,
                "name": p.name,
                "description": p.description or "Sin descripción adicional.",
                "price": float(p.sale_price),
                "stock": float(p.stock_actual),
                "unit_type": p.unit_type, # 'U' o 'ML'
                "image": p.image.url if p.image else None
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
                invoice_number = f"DOC-{now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:6].upper()}"

                sale = Sale.objects.create(
                    invoice_number=invoice_number,
                    customer=customer,
                    seller=request.user,
                    payment_method=payment_method,
                    cash_session=active_session,
                    subtotal=0, iva=0, total=0
                )

                subtotal_calc = Decimal('0.00')
                
                for item in items:
                    qty = Decimal(str(item.get('quantity', 1)))
                    is_service = item.get('is_service', False)

                    if is_service:
                        # LOGICA PARA MANO DE OBRA (SERVICIOS)
                        desc = item.get('name', 'Mano de obra')
                        unit_price = Decimal(str(item.get('price', 0)))
                        line_total = unit_price * qty
                        subtotal_calc += line_total

                        SaleDetail.objects.create(
                            sale=sale, 
                            product=None, 
                            is_service=True,
                            service_description=desc, 
                            quantity=qty,
                            unit_price=unit_price, 
                            subtotal=line_total
                        )
                    else:
                        # LOGICA NORMAL PARA PRODUCTOS E INVENTARIO
                        product = Product.objects.select_for_update().get(id=item['id'])
                        
                        if product.stock_actual < qty:
                            raise ValueError(f"Stock insuficiente para {product.name}. Disponible: {product.stock_actual}")

                        # Descuento exacto de inventario (Líquidos o Unidades)
                        product.stock_actual -= qty
                        product.save()

                        # Movimiento de salida en Kardex
                        unidad_str = "ml" if product.unit_type == 'ML' else "u"
                        StockMovement.objects.create(
                            product=product, movement_type='OUT', quantity=qty,
                            description=f"Venta de {qty}{unidad_str} | Factura: {invoice_number}", user=request.user
                        )

                        # ===== CORRECCIÓN CRÍTICA DE LÍQUIDOS =====
                        # Si es líquido, sacamos el precio por cada mililitro dividiendo para 1000
                        if product.unit_type == 'ML':
                            precio_unitario_real = product.sale_price / Decimal('1000.00')
                        else:
                            precio_unitario_real = product.sale_price

                        line_total = precio_unitario_real * qty
                        subtotal_calc += line_total

                        SaleDetail.objects.create(
                            sale=sale, product=product, quantity=qty,
                            unit_price=precio_unitario_real, subtotal=line_total
                        )

                # Cálculos finales de la venta
                iva_calc = subtotal_calc * Decimal('0.15')
                total_calc = subtotal_calc + iva_calc

                sale.subtotal = subtotal_calc
                sale.iva = iva_calc
                sale.total = total_calc
                sale.save()

            return Response({
                "message": "Venta procesada con éxito",
                "invoice": sale.invoice_number,
                "total": float(sale.total)
            }, status=status.HTTP_201_CREATED)

        except ValueError as ve:
            return Response({"error": str(ve)}, status=status.HTTP_400_BAD_REQUEST)
        except Customer.DoesNotExist:
            return Response({"error": "Cliente no válido."}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": f"Error interno: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
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
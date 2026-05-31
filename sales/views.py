from decimal import Decimal
import uuid

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils.timezone import now
from django.views.generic import TemplateView, ListView

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

# Importaciones de otras apps
from inventory.models import Product, StockMovement
from customers.models import Customer
from cash_register.models import CashSession

# Modelos de ventas
from .models import Sale, SaleDetail, Payment

# ==========================================
# VISTAS DE INTERFAZ (UI)
# ==========================================
class POSDashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'sales/pos.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context

class ProformaListView(LoginRequiredMixin, ListView):
    """Vista para gestionar las proformas pendientes."""
    model = Sale
    template_name = 'sales/proforma_list.html'
    context_object_name = 'proformas'

    def get_queryset(self):
        return Sale.objects.filter(status='PROFORMA').order_by('-created_at')

class InvoicePDFView(LoginRequiredMixin, TemplateView):
    template_name = 'sales/invoice_pdf.html'

    def get_context_data(self, invoice_number, **kwargs):
        context = super().get_context_data(**kwargs)
        sale = get_object_or_404(Sale, invoice_number=invoice_number)
        
        details = SaleDetail.objects.filter(sale=sale)
        for item in details:
            item.unit_price_iva = float(item.unit_price) * 1.15
            item.subtotal_iva = float(item.subtotal) * 1.15

        context['sale'] = sale
        context['customer'] = sale.customer
        context['details'] = details
        context['company'] = {
            "name": "BEDOYA MOTORS",
            "ruc": "17XXXXXXXX001",
            "address": "Sangolquí",
            "city": "Pichincha, Ecuador",
            "phone": "0964016581",
            "email": "mateobedoyaa89@gmail.com"
        }
        return context


# ==========================================
# APIs DEL PUNTO DE VENTA (POS)
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
            Q(description__icontains=query),
            is_active=True
        ).order_by('name')[:24]

        results = [{"id": p.id, "code": p.code, "name": p.name, "description": p.description, "price": float(p.sale_price), "stock": float(p.stock_actual), "unit_type": p.unit_type, "image": p.image.url if p.image else None} for p in products]
        return Response({"products": results}, status=status.HTTP_200_OK)

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

        results = [{"id": c.id, "cedula": c.cedula, "name": f"{c.first_name} {c.last_name}", "phone": getattr(c, 'phone', '')} for c in customers]
        return Response({"customers": results}, status=status.HTTP_200_OK)

class PendingDocumentsAPI(APIView):
    """Devuelve los documentos abiertos (Proformas y Pedidos) para el modal del POS."""
    def get(self, request, *args, **kwargs):
        docs = Sale.objects.filter(status__in=['PROFORMA', 'DRAFT']).order_by('-created_at')[:50]
        results = []
        for d in docs:
            results.append({
                "id": d.id,
                "invoice_number": d.invoice_number,
                "status": d.status,
                "customer_name": f"{d.customer.first_name} {d.customer.last_name}" if d.customer else "Consumidor Final",
                "total": float(d.total),
                "date": d.created_at.strftime('%d %b %H:%M')
            })
        return Response({"documents": results}, status=status.HTTP_200_OK)

class LoadDocumentAPI(APIView):
    """Carga un documento abierto específico en el carrito del POS."""
    def get(self, request, sale_id, *args, **kwargs):
        sale = get_object_or_404(Sale, id=sale_id)
        if sale.status == 'INVOICED':
            return Response({"error": "Documento ya facturado. No se puede editar."}, status=status.HTTP_400_BAD_REQUEST)
            
        items = []
        for detail in sale.details.all():
            items.append({
                "id": detail.product.id if detail.product else f"srv_{detail.id}",
                "is_service": detail.is_service,
                "name": detail.service_description if detail.is_service else detail.product.name,
                "code": "SERV" if detail.is_service else detail.product.code,
                "price": float(detail.unit_price),
                "quantity": float(detail.quantity),
                "stock": float(detail.product.stock_actual) if detail.product else 999999,
                "unit_type": detail.product.unit_type if detail.product else 'U'
            })
            
        customer_data = {"id": "", "name": "", "phone": ""}
        if sale.customer:
            customer_data = {
                "id": sale.customer.id,
                "name": f"{sale.customer.first_name} {sale.customer.last_name}",
                "phone": getattr(sale.customer, 'phone', '')
            }
            
        return Response({
            "sale_id": sale.id, 
            "status": sale.status, 
            "payment_method": sale.payment_method,
            "apply_discount": sale.discount > Decimal('0.00'),
            "customer": customer_data, 
            "items": items
        }, status=status.HTTP_200_OK)

class DeleteDocumentAPI(APIView):
    """API para eliminar una proforma o borrador pendiente."""
    def delete(self, request, sale_id, *args, **kwargs):
        sale = get_object_or_404(Sale, id=sale_id)
        if sale.status == 'INVOICED':
            return Response({"error": "No puede eliminar una factura ya emitida y contabilizada."}, status=status.HTTP_400_BAD_REQUEST)
        
        sale.delete()
        return Response({"message": "Documento eliminado con éxito."}, status=status.HTTP_200_OK)

class ProcessSaleAPI(APIView):
    """Procesa la venta, proforma o borrador. Descuenta stock solo si es INVOICED."""
    def post(self, request, *args, **kwargs):
        active_session = CashSession.objects.filter(user=request.user, is_open=True).first()
        
        if not active_session:
            return Response({"error": "Debe aperturar su caja diaria antes de operar."}, status=status.HTTP_403_FORBIDDEN)

        data = request.data
        sale_id = data.get('sale_id')
        customer_id = data.get('customer_id') 
        payment_method = data.get('payment_method', 'CASH')
        doc_status = data.get('status', 'PROFORMA') 
        apply_discount = data.get('apply_discount', False)
        items = data.get('items', [])
        
        if not items:
            return Response({"error": "El carrito está vacío."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            with transaction.atomic():
                customer = Customer.objects.get(id=customer_id) if customer_id else None
                
                # 1. RECUPERAR O CREAR DOCUMENTO
                if sale_id:
                    sale = Sale.objects.select_for_update().get(id=sale_id)
                    if sale.status == 'INVOICED':
                        raise ValueError("Este documento ya fue facturado y no puede ser editado.")
                    sale.customer = customer
                    sale.payment_method = payment_method
                    sale.status = doc_status
                    sale.details.all().delete()
                else:
                    invoice_number = f"DOC-{now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:6].upper()}"
                    sale = Sale.objects.create(
                        invoice_number=invoice_number,
                        customer=customer,
                        seller=request.user,
                        payment_method=payment_method,
                        cash_session=active_session,
                        status=doc_status,
                        subtotal=0, iva=0, total=0, balance_due=0
                    )

                subtotal_calc = Decimal('0.00')
                
                # 2. PROCESAR ÍTEMS
                for item in items:
                    qty = Decimal(str(item.get('quantity', 1)))
                    is_service = item.get('is_service', False)

                    if is_service:
                        desc = item.get('name', 'Mano de obra')
                        unit_price = Decimal(str(item.get('price', 0)))
                        line_total = unit_price * qty
                        subtotal_calc += line_total

                        SaleDetail.objects.create(
                            sale=sale, product=None, is_service=True,
                            service_description=desc, quantity=qty,
                            unit_price=unit_price, subtotal=line_total
                        )
                    else:
                        product_id = item.get('id')
                        product = Product.objects.select_for_update().filter(id=product_id).first()
                        
                        if product is None:
                            raise ValueError(f"El artículo '{item.get('name')}' ya no existe.")

                        if doc_status == 'INVOICED' and product.stock_actual < qty:
                            raise ValueError(f"Stock insuficiente para {product.name}.")

                        precio_unitario_real = product.sale_price / Decimal('1000.00') if product.unit_type == 'ML' else product.sale_price
                        line_total = precio_unitario_real * qty
                        subtotal_calc += line_total

                        SaleDetail.objects.create(
                            sale=sale, product=product, is_service=False,
                            quantity=qty, unit_price=precio_unitario_real, subtotal=line_total
                        )

                        # Afectar inventario solo si se factura
                        if doc_status == 'INVOICED':
                            product.stock_actual -= qty
                            product.save()

                            unidad_str = "ml" if product.unit_type == 'ML' else "u"
                            StockMovement.objects.create(
                                product=product, movement_type='OUT', quantity=qty,
                                description=f"Venta de {qty}{unidad_str} | Doc: {sale.invoice_number}", 
                                user=request.user
                            )

                # ==========================================
                # 3. LÓGICA DE DESCUENTO E IMPUESTOS
                # ==========================================
                discount_calc = Decimal('0.00')
                
                if apply_discount and customer:
                    discount_calc = subtotal_calc * Decimal('0.05')

                base_imponible = subtotal_calc - discount_calc
                iva_calc = base_imponible * Decimal('0.15')
                total_calc = base_imponible + iva_calc

                sale.subtotal = subtotal_calc
                sale.discount = discount_calc
                sale.iva = iva_calc
                sale.total = total_calc
                
                if doc_status == 'INVOICED':
                    # Corrección: El saldo pendiente siempre se registra en 0.00
                    sale.balance_due = Decimal('0.00')

                sale.save()

            return Response({
                "message": "Procesado con éxito",
                "invoice": sale.invoice_number,
                "status": sale.status,
                "total": float(sale.total)
            }, status=status.HTTP_201_CREATED if not sale_id else status.HTTP_200_OK)

        except ValueError as ve:
            return Response({"error": str(ve)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": f"Error interno: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class RegisterPaymentAPI(APIView):
    """Registra abonos a facturas a crédito."""
    def post(self, request, sale_id, *args, **kwargs):
        amount = request.data.get('amount')
        method = request.data.get('method', 'TRANSFER')
        reference = request.data.get('reference_number', '')
        
        if not amount:
            return Response({"error": "Debe especificar el monto a abonar."}, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            with transaction.atomic():
                sale = get_object_or_404(Sale, id=sale_id)
                amount_decimal = Decimal(str(amount))
                
                if sale.status != 'INVOICED':
                    return Response({"error": "Solo se permite abonar a documentos facturados."}, status=status.HTTP_400_BAD_REQUEST)
                    
                if amount_decimal <= 0 or amount_decimal > sale.balance_due:
                    return Response({"error": f"Monto inválido. Saldo máximo es ${sale.balance_due}."}, status=status.HTTP_400_BAD_REQUEST)
                    
                payment = Payment.objects.create(
                    sale=sale, amount=amount_decimal, method=method, reference_number=reference,
                    is_verified=False if method == 'TRANSFER' else True 
                )
                
                return Response({
                    "message": "Abono registrado correctamente.", "payment_id": payment.id, "new_balance": float(sale.balance_due)
                }, status=status.HTTP_201_CREATED)
                
        except Exception as e:
            return Response({"error": f"Error interno: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
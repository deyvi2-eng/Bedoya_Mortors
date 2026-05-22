from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser
from .models import Product, Category, Supplier
from django.db import transaction
from inventory.models import StockMovement


class InventoryDashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'inventory/manage.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['products'] = Product.objects.all().order_by('-created_at')
        context['categories'] = Category.objects.filter(is_active=True)
        context['suppliers'] = Supplier.objects.filter(is_active=True)
        return context

class ProductCreateAPI(APIView):
    # MultiPartParser es vital para poder recibir archivos de imagen
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request, *args, **kwargs):
        try:
            # Extraer datos del formulario
            category_id = request.data.get('category')
            supplier_id = request.data.get('supplier')
            name = request.data.get('name')
            purchase_price = request.data.get('purchase_price')
            sale_price = request.data.get('sale_price')
            stock_minimo = request.data.get('stock_minimo')
            image = request.FILES.get('image') # Capturar la imagen

            # Validaciones básicas
            if not all([category_id, name, purchase_price, sale_price]):
                return Response({"error": "Faltan campos obligatorios."}, status=status.HTTP_400_BAD_REQUEST)

            category = Category.objects.get(id=category_id)
            supplier = Supplier.objects.get(id=supplier_id) if supplier_id else None

            # Crear el producto (el código BED-XXX se genera automáticamente por el modelo)
            product = Product.objects.create(
                category=category,
                supplier=supplier,
                name=name,
                purchase_price=purchase_price,
                sale_price=sale_price,
                stock_minimo=stock_minimo,
                image=image
            )

            return Response({
                "message": "Producto registrado exitosamente.",
                "code": product.code
            }, status=status.HTTP_201_CREATED)

        except Category.DoesNotExist:
            return Response({"error": "La categoría seleccionada no existe."}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        

class AddStockAPI(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        product_id = request.data.get('product_id')
        quantity = request.data.get('quantity')
        invoice_ref = request.data.get('invoice_ref', 'Sin referencia')

        if not product_id or not quantity or int(quantity) <= 0:
            return Response({"error": "Datos inválidos o cantidad en cero."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            with transaction.atomic():
                # 1. Bloquear y obtener el producto
                product = Product.objects.select_for_update().get(id=product_id)
                
                # 2. Sumar el stock
                product.stock_actual += int(quantity)
                product.save()

                # 3. Registrar el movimiento de entrada
                StockMovement.objects.create(
                    product=product,
                    movement_type='IN',
                    quantity=int(quantity),
                    description=f"Ingreso de mercadería. Ref: {invoice_ref}",
                    user=request.user
                )

            return Response({"message": "Stock actualizado correctamente.", "new_stock": product.stock_actual}, status=status.HTTP_200_OK)

        except Product.DoesNotExist:
            return Response({"error": "Producto no encontrado."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": "Ocurrió un error al procesar el ingreso."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
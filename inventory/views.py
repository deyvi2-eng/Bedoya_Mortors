from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.core.paginator import Paginator
from django.shortcuts import render
from django.db.models import Q
from decimal import Decimal, InvalidOperation


from .models import Product, Category, Supplier, StockMovement

# ==========================================
# VISTA PRINCIPAL DEL DASHBOARD DE INVENTARIO
# ==========================================
class InventoryDashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'inventory/manage.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # 1. Capturar parámetros
        search_query = self.request.GET.get('q', '').strip()
        category_filter = self.request.GET.get('category', 'ALL')
        per_page = self.request.GET.get('per_page', '15') # <-- NUEVO PARÁMETRO
        
        queryset = Product.objects.select_related('category', 'supplier').all().order_by('-created_at')
        
        if search_query:
            queryset = queryset.filter(
                Q(code__icontains=search_query) |
                Q(name__icontains=search_query) |
                Q(description__icontains=search_query) |
                Q(brand__icontains=search_query)
            )
            
        if category_filter != 'ALL':
            queryset = queryset.filter(category__name=category_filter)

        # 2. LÓGICA DE "VER TODOS"
        if per_page == 'all':
            limit = max(queryset.count(), 1) # Muestra todos los existentes
        else:
            limit = int(per_page)

        paginator = Paginator(queryset, limit)
        page_number = self.request.GET.get('page', 1)
        page_obj = paginator.get_page(page_number)

        context['products'] = page_obj
        context['categories'] = Category.objects.filter(is_active=True)
        context['suppliers'] = Supplier.objects.filter(is_active=True)
        
        context['current_q'] = search_query
        context['current_cat'] = category_filter
        context['current_per_page'] = per_page # <-- Para mantener la selección en el HTML
        
        return context

# ==========================================
# API: CREAR PRODUCTO (SOLO ADMIN)
# ==========================================
class ProductCreateAPI(APIView):
    parser_classes = (MultiPartParser, FormParser)
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        if request.user.role != 'ADMIN':
            return Response({"error": "Acceso denegado. Solo el administrador puede crear productos."}, status=status.HTTP_403_FORBIDDEN)

        try:
            category_id = request.data.get('category')
            name = request.data.get('name')
            purchase_price = request.data.get('purchase_price')
            sale_price = request.data.get('sale_price')
            
            supplier_id = request.data.get('supplier')
            
            barcode = request.data.get('barcode', '').strip()
            if not barcode:  
                barcode = None
                
            brand = request.data.get('brand', '')
            model_compatibility = request.data.get('model_compatibility', '')
            location = request.data.get('location', '')
            stock_minimo = request.data.get('stock_minimo', 5)
            unit_type = request.data.get('unit_type', 'U')
            image = request.FILES.get('image')

            if not all([category_id, name, purchase_price, sale_price]):
                return Response({"error": "Faltan campos obligatorios."}, status=status.HTTP_400_BAD_REQUEST)

            category = Category.objects.get(id=category_id)
            supplier = Supplier.objects.get(id=supplier_id) if supplier_id else None

            product = Product.objects.create(
                category=category,
                supplier=supplier,
                name=name,
                barcode=barcode,
                brand=brand,
                unit_type=unit_type,
                model_compatibility=model_compatibility,
                location=location,
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
            return Response({"error": "La categoría no existe."}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# ==========================================
# API: AÑADIR STOCK (SOLO ADMIN)
# ==========================================
class AddStockAPI(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        if getattr(request.user, 'role', '') != 'ADMIN':
            return Response({"error": "Acceso denegado. Solo el administrador puede modificar el stock."}, status=status.HTTP_403_FORBIDDEN)

        product_id = request.data.get('product_id')
        quantity_raw = request.data.get('quantity')
        invoice_ref = request.data.get('invoice_ref', 'Sin referencia')

        # 1. LIMPIEZA EXTREMA DEL NÚMERO
        try:
            # Reemplaza comas por puntos por si el usuario teclea "1000,50"
            quantity_str = str(quantity_raw).strip().replace(',', '.')
            quantity = Decimal(quantity_str)
            
            if quantity <= Decimal('0.00'):
                return Response({"error": "La cantidad a ingresar debe ser mayor a 0."}, status=status.HTTP_400_BAD_REQUEST)
        except (InvalidOperation, TypeError, ValueError):
            return Response({"error": "La cantidad debe ser numérica exacta (ej. 1000 o 1000.50)."}, status=status.HTTP_400_BAD_REQUEST)

        # 2. PROCESO DE GUARDADO
        try:
            with transaction.atomic():
                product = Product.objects.select_for_update().get(id=product_id)
                
                # SOLUCIÓN AL BUG DE SQLITE: Forzamos el stock viejo a Decimal antes de sumar
                stock_actual_db = Decimal(str(product.stock_actual))
                
                # Suma matemática perfecta
                product.stock_actual = stock_actual_db + quantity
                product.save()

                StockMovement.objects.create(
                    product=product,
                    movement_type='IN',
                    quantity=quantity,
                    description=f"Ingreso de mercadería. Ref: {invoice_ref}",
                    user=request.user
                )

            return Response({"message": "Stock actualizado correctamente.", "new_stock": product.stock_actual}, status=status.HTTP_200_OK)

        except Product.DoesNotExist:
            return Response({"error": "Producto no encontrado."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            # Ahora, si falla, el cartel rojo te dirá EXACTAMENTE qué código de Python falló
            return Response({"error": f"Error técnico: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)  

# ==========================================
# API: DESACTIVAR/ACTIVAR PRODUCTO (SOLO ADMIN)
# ==========================================
class ProductToggleAPI(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, product_id, *args, **kwargs):
        if request.user.role != 'ADMIN':
            return Response({"error": "Acceso denegado."}, status=status.HTTP_403_FORBIDDEN)
            
        product = get_object_or_404(Product, id=product_id)
        product.is_active = not product.is_active
        product.save()
        
        estado = "activado" if product.is_active else "desactivado"
        return Response({"message": f"Producto {estado} exitosamente."})
    
# ==========================================
# VISTA: LOGS DE MOVIMIENTOS
# ==========================================
class StockMovementLogView(LoginRequiredMixin, TemplateView):
    template_name = 'inventory/movements.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['movements'] = StockMovement.objects.all().select_related('product', 'user').order_by('-created_at')[:100]
        return context
    
# ==========================================
# API: KARDEX DEL PRODUCTO
# ==========================================
class ProductKardexAPI(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, product_id, *args, **kwargs):
        product = get_object_or_404(Product, id=product_id)
        movements = StockMovement.objects.filter(product=product).order_by('-created_at')
        
        mov_data = [{
            "date": m.created_at.strftime("%d/%m/%Y %H:%M"),
            "type": m.get_movement_type_display(),
            "qty": m.quantity,
            "user": m.user.get_full_name() or m.user.username,
            "desc": m.description
        } for m in movements]

        return Response({
            "product": {
                "code": product.code,
                "name": product.name,
                "category": product.category.name,
                "supplier": product.supplier.name if product.supplier else "Sin Proveedor",
                "stock": product.stock_actual,
                "unit_type": product.unit_type,
                "image": product.image.url if product.image else None
            },
            "movements": mov_data
        })
    
# ==========================================
# API: CREAR CATEGORÍA
# ==========================================
class CategoryCreateAPI(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        if request.user.role != 'ADMIN':
            return Response({"error": "Acceso denegado."}, status=status.HTTP_403_FORBIDDEN)
        
        name = request.data.get('name')
        prefix = request.data.get('prefix')
        description = request.data.get('description', '')

        if not name or not prefix:
            return Response({"error": "Nombre y prefijo son obligatorios."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            category = Category.objects.create(
                name=name, prefix=prefix.upper(), description=description
            )
            return Response({"message": "Categoría creada exitosamente.", "id": category.id}, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({"error": "El prefijo ya existe o ocurrió un error."}, status=status.HTTP_400_BAD_REQUEST)

# ==========================================
# API: CREAR PROVEEDOR
# ==========================================
class SupplierCreateAPI(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        if request.user.role != 'ADMIN':
            return Response({"error": "Acceso denegado."}, status=status.HTTP_403_FORBIDDEN)
        
        name = request.data.get('name')
        contact_phone = request.data.get('contact_phone', '')
        email = request.data.get('email', '')

        if not name:
            return Response({"error": "El nombre del proveedor es obligatorio."}, status=status.HTTP_400_BAD_REQUEST)

        supplier = Supplier.objects.create(name=name, contact_phone=contact_phone, email=email)
        return Response({"message": "Proveedor creado exitosamente.", "id": supplier.id}, status=status.HTTP_201_CREATED)
    
# ==========================================
# GESTIÓN DE CATÁLOGOS EN INTERFAZ
# ==========================================
class InventorySettingsView(LoginRequiredMixin, TemplateView):
    template_name = 'inventory/settings.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = Category.objects.all().order_by('-created_at')
        context['suppliers'] = Supplier.objects.all().order_by('-created_at')
        return context

class CategoryUpdateAPI(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk, *args, **kwargs):
        if request.user.role != 'ADMIN':
            return Response({"error": "Acceso denegado."}, status=status.HTTP_403_FORBIDDEN)
        
        category = get_object_or_404(Category, pk=pk)
        category.name = request.data.get('name', category.name)
        category.prefix = request.data.get('prefix', category.prefix).upper()
        category.description = request.data.get('description', category.description)
        category.save()
        return Response({"message": "Categoría actualizada exitosamente."})

class CategoryToggleAPI(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk, *args, **kwargs):
        if request.user.role != 'ADMIN':
            return Response({"error": "Acceso denegado."}, status=status.HTTP_403_FORBIDDEN)
        
        category = get_object_or_404(Category, pk=pk)
        category.is_active = not category.is_active
        category.save()
        return Response({"message": "Estado modificado."})

class SupplierUpdateAPI(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk, *args, **kwargs):
        if request.user.role != 'ADMIN':
            return Response({"error": "Acceso denegado."}, status=status.HTTP_403_FORBIDDEN)
        
        supplier = get_object_or_404(Supplier, pk=pk)
        supplier.name = request.data.get('name', supplier.name)
        supplier.contact_phone = request.data.get('contact_phone', supplier.contact_phone)
        supplier.email = request.data.get('email', supplier.email)
        supplier.save()
        return Response({"message": "Proveedor actualizado exitosamente."})

class SupplierToggleAPI(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk, *args, **kwargs):
        if request.user.role != 'ADMIN':
            return Response({"error": "Acceso denegado."}, status=status.HTTP_403_FORBIDDEN)
        
        supplier = get_object_or_404(Supplier, pk=pk)
        supplier.is_active = not supplier.is_active
        supplier.save()
        return Response({"message": "Estado modificado."})

# ==========================================
# API: EDITAR Y ELIMINAR PRODUCTO
# ==========================================
class ProductUpdateAPI(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk, *args, **kwargs):
        if request.user.role != 'ADMIN':
            return Response({"error": "Acceso denegado."}, status=status.HTTP_403_FORBIDDEN)
        
        product = get_object_or_404(Product, pk=pk)
        
        product.name = request.data.get('name', product.name)
        product.description = request.data.get('description', product.description)
        
        category_id = request.data.get('category_id')
        if category_id:
            product.category_id = category_id
            
        supplier_id = request.data.get('supplier_id')
        if supplier_id:
            product.supplier_id = supplier_id
            
        product.brand = request.data.get('brand', product.brand)
        product.unit_type = request.data.get('unit_type', product.unit_type)
        product.model_compatibility = request.data.get('model_compatibility', product.model_compatibility)
        product.location = request.data.get('location', product.location)
        
        product.purchase_price = request.data.get('purchase_price', product.purchase_price)
        product.sale_price = request.data.get('sale_price', product.sale_price)
        
        product.stock_minimo = request.data.get('stock_minimo', product.stock_minimo)
        product.stock_critico = request.data.get('stock_critico', product.stock_critico)
        
        product.save()
        return Response({"message": "Producto actualizado correctamente."})

class ProductDeleteAPI(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk, *args, **kwargs):
        if request.user.role != 'ADMIN':
            return Response({"error": "Acceso denegado."}, status=status.HTTP_403_FORBIDDEN)
        
        product = get_object_or_404(Product, pk=pk)
        product.delete()
        return Response({"message": "Producto eliminado permanentemente."})
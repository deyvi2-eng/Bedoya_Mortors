from django.db import models, transaction
from core.models import BaseModel
from accounts.models import User


class Category(BaseModel):
    name = models.CharField(max_length=100, verbose_name="Nombre de Categoría")
    prefix = models.CharField(max_length=3, unique=True, help_text="Prefijo exacto de 3 letras. Ej: ACE, LLA, MOT")
    description = models.TextField(blank=True, null=True, verbose_name="Descripción")

    class Meta:
        verbose_name = "Categoría"
        verbose_name_plural = "Categorías"

    def __str__(self):
        return f"{self.name} ({self.prefix})"

class Supplier(BaseModel):
    name = models.CharField(max_length=150, verbose_name="Razón Social / Nombre")
    contact_phone = models.CharField(max_length=20, blank=True, null=True, verbose_name="Teléfono")
    email = models.EmailField(blank=True, null=True, verbose_name="Correo Electrónico")

    class Meta:
        verbose_name = "Proveedor"
        verbose_name_plural = "Proveedores"

    def __str__(self):
        return self.name

class Product(BaseModel):
    # Identificadores
    code = models.CharField(max_length=20, unique=True, blank=True, verbose_name="Código Interno")
    barcode = models.CharField(max_length=50, unique=True, blank=True, null=True, verbose_name="Código de Barras")
    
    # Información General
    name = models.CharField(max_length=200, verbose_name="Nombre del Producto")
    description = models.TextField(blank=True, null=True, verbose_name="Descripción")
    category = models.ForeignKey(Category, on_delete=models.PROTECT, verbose_name="Categoría")
    brand = models.CharField(max_length=100, blank=True, null=True, verbose_name="Marca")
    model_compatibility = models.CharField(max_length=255, blank=True, null=True, verbose_name="Compatibilidad (Motos)")
    
    # Precios
    purchase_price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Precio de Compra")
    sale_price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Precio de Venta")
    
    # Inventario
    stock_actual = models.IntegerField(default=0, verbose_name="Stock Actual")
    stock_minimo = models.IntegerField(default=5, verbose_name="Stock Mínimo")
    stock_critico = models.IntegerField(default=2, verbose_name="Stock Crítico")
    location = models.CharField(max_length=100, blank=True, null=True, verbose_name="Ubicación en Bodega")
    unit_measure = models.CharField(max_length=50, default="Unidad", verbose_name="Unidad de Medida")
    
    # Relaciones y multimedia
    supplier = models.ForeignKey(Supplier, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Proveedor")
    image = models.ImageField(upload_to='products/', blank=True, null=True, verbose_name="Imagen del Producto")

    class Meta:
        verbose_name = "Producto"
        verbose_name_plural = "Productos"

    def __str__(self):
        return f"[{self.code}] {self.name}"

    @property
    def profit_margin(self):
        # Cálculo automático del porcentaje de ganancia
        if self.purchase_price and self.purchase_price > 0:
            margin = ((self.sale_price - self.purchase_price) / self.purchase_price) * 100
            return round(margin, 2)
        return 0.0

    def save(self, *args, **kwargs):
        # Generación automática de código estrictamente si el producto es nuevo y no tiene código
        if not self.code:
            with transaction.atomic():
                # select_for_update bloquea las filas concurrentes hasta que termine la transacción
                last_product = Product.objects.select_for_update().filter(
                    category=self.category
                ).order_by('id').last()
                
                secuencia = 1
                if last_product and last_product.code:
                    try:
                        # Extrae el correlativo final, ej: BED-MOT-0015 -> 15 + 1 -> 16
                        secuencia = int(last_product.code.split('-')[-1]) + 1
                    except ValueError:
                        pass
                
                # Ensambla el código final asegurando 4 dígitos
                self.code = f"BED-{self.category.prefix.upper()}-{secuencia:04d}"
        
        super().save(*args, **kwargs)


class StockMovement(BaseModel):
    class MovementType(models.TextChoices):
        IN = 'IN', 'Entrada'
        OUT = 'OUT', 'Salida'
        ADJUST = 'ADJUST', 'Ajuste Manual'

    product = models.ForeignKey(Product, on_delete=models.CASCADE, verbose_name="Producto")
    movement_type = models.CharField(max_length=10, choices=MovementType.choices, verbose_name="Tipo de Movimiento")
    quantity = models.IntegerField(verbose_name="Cantidad")
    description = models.CharField(max_length=255, verbose_name="Descripción / Motivo")
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name="Registrado por")

    class Meta:
        verbose_name = "Movimiento de Stock"
        verbose_name_plural = "Movimientos de Stock"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.get_movement_type_display()} - {self.product.name} ({self.quantity})"
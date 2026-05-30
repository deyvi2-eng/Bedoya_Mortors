from django.db import models, transaction
from core.models import BaseModel
from customers.models import Customer
from inventory.models import Product
from accounts.models import User
from cash_register.models import CashSession
from decimal import Decimal

class Sale(BaseModel):
    PAYMENT_CHOICES = [
        ('CASH', 'Efectivo'),
        ('TRANSFER', 'Transferencia'),
        ('CARD', 'Tarjeta'),
        ('MIXED', 'Mixto'),
    ]
    
    STATUS_CHOICES = [
        ('PROFORMA', 'Proforma'),
        ('DRAFT', 'Borrador (Pre-Factura)'),
        ('INVOICED', 'Facturado'),
        ('VOIDED', 'Anulado')
    ]

    cash_session = models.ForeignKey(CashSession, on_delete=models.PROTECT, related_name='sales', verbose_name="Sesión de Caja", null=True)
    invoice_number = models.CharField(max_length=20, unique=True, verbose_name="Número de Documento")
    
    # Cliente opcional para permitir facturación rápida (Consumidor Final)
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, null=True, blank=True, verbose_name="Cliente")
    seller = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Vendedor")
    
    # Nuevos campos integrados para el ciclo de vida y cobranza
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PROFORMA', verbose_name="Estado")
    valid_until = models.DateField(null=True, blank=True, verbose_name="Válido hasta (Proforma)")
    balance_due = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name="Saldo Pendiente")
    
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    iva = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    
    payment_method = models.CharField(max_length=20, choices=PAYMENT_CHOICES, default='CASH')
    is_voided = models.BooleanField(default=False, verbose_name="Anulada")

    class Meta:
        verbose_name = "Venta / Proforma"
        verbose_name_plural = "Ventas y Proformas"
        ordering = ['-created_at']

    def __str__(self):
        doc_type = dict(self.STATUS_CHOICES).get(self.status, 'Documento')
        # Prevención de error si la factura no tiene cliente asignado
        customer_name = f"{self.customer.first_name} {self.customer.last_name}" if self.customer else "Consumidor Final"
        return f"{doc_type} {self.invoice_number} - {customer_name}"

    def convert_to_invoice(self):
        """Transición de estado del documento a facturado."""
        if self.status in ['PROFORMA', 'DRAFT']:
            self.status = 'INVOICED'
            # Inicializa el saldo pendiente en caso de permitir pagos fraccionados o a crédito
            self.balance_due = self.total
            self.save()


class SaleDetail(BaseModel):
    sale = models.ForeignKey(Sale, on_delete=models.CASCADE, related_name='details', verbose_name="Venta")
    
    # MODIFICADO: product ahora puede ser nulo para permitir la Mano de Obra
    product = models.ForeignKey(Product, on_delete=models.PROTECT, null=True, blank=True, verbose_name="Producto")
    
    # NUEVO: Campos para Mano de Obra
    is_service = models.BooleanField(default=False, verbose_name="Es Mano de Obra")
    service_description = models.CharField(max_length=255, null=True, blank=True, verbose_name="Descripción del Servicio")
    
    quantity = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Cantidad")
    
    historical_price = models.DecimalField(max_digits=12, decimal_places=4, default=0.00, verbose_name="Precio Venta Histórico")
    historical_cost = models.DecimalField(max_digits=12, decimal_places=4, default=0.00, verbose_name="Costo Compra Histórico")
    
    unit_price = models.DecimalField(max_digits=12, decimal_places=4, verbose_name="Precio Unitario Aplicado")
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Subtotal")

    class Meta:
        verbose_name = "Detalle de Venta"
        verbose_name_plural = "Detalles de Venta"

    def __str__(self):
        if self.is_service:
            return f"{self.quantity}x {self.service_description} (Doc {self.sale.invoice_number})"
        
        product_name = self.product.name if self.product else 'Servicio'
        return f"{self.quantity}x {product_name} (Doc {self.sale.invoice_number})"

    def save(self, *args, **kwargs):
        # MODIFICADO: Tomar la foto de precios calculando correctamente si es líquido
        if not self.pk and self.product:
            if self.product.unit_type == 'ML':
                # Si es líquido, dividimos el costo para 1000 para que la ganancia sea exacta
                self.historical_price = self.product.sale_price / Decimal('1000.00')
                self.historical_cost = self.product.purchase_price / Decimal('1000.00')
            else:
                self.historical_price = self.product.sale_price
                self.historical_cost = self.product.purchase_price
        super().save(*args, **kwargs)


class Payment(BaseModel):
    """
    Modelo diseñado para registrar pagos parciales y facilitar la conciliación.
    """
    sale = models.ForeignKey(Sale, on_delete=models.CASCADE, related_name='payments', verbose_name="Factura Relacionada")
    amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Monto Abonado")
    method = models.CharField(max_length=20, choices=Sale.PAYMENT_CHOICES, default='TRANSFER', verbose_name="Método de Pago")
    reference_number = models.CharField(max_length=100, blank=True, null=True, verbose_name="Número de Comprobante / Referencia")
    payment_date = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de Pago")
    is_verified = models.BooleanField(default=False, verbose_name="Pago Verificado")
    
    class Meta:
        verbose_name = "Abono / Pago"
        verbose_name_plural = "Abonos y Pagos"
        ordering = ['-payment_date']

    def __str__(self):
        return f"Abono de ${self.amount} a Factura {self.sale.invoice_number}"

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)
        
        # Al registrar un pago nuevo, el saldo pendiente de la venta disminuye automáticamente
        if is_new:
            self.sale.balance_due -= self.amount
            self.sale.save()
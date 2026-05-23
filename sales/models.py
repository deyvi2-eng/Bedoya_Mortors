from django.db import models, transaction
from core.models import BaseModel
from customers.models import Customer
from inventory.models import Product
from accounts.models import User
from cash_register.models import CashSession


class Sale(BaseModel):
    PAYMENT_CHOICES = [
        ('CASH', 'Efectivo'),
        ('TRANSFER', 'Transferencia'),
        ('CARD', 'Tarjeta'),
        ('MIXED', 'Mixto'),
    ]
    cash_session = models.ForeignKey(CashSession, on_delete=models.PROTECT, related_name='sales', verbose_name="Sesión de Caja", null=True)
    invoice_number = models.CharField(max_length=20, unique=True, verbose_name="Número de Factura")
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, verbose_name="Cliente")
    seller = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Vendedor")
    
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    iva = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    
    payment_method = models.CharField(max_length=20, choices=PAYMENT_CHOICES, default='CASH')
    is_voided = models.BooleanField(default=False, verbose_name="Anulada")

    class Meta:
        verbose_name = "Venta"
        verbose_name_plural = "Ventas"
        ordering = ['-created_at']

    def __str__(self):
        return f"Factura {self.invoice_number} - {self.customer.first_name} {self.customer.last_name}"

class SaleDetail(BaseModel):
    sale = models.ForeignKey(Sale, on_delete=models.CASCADE, related_name='details', verbose_name="Venta")
    product = models.ForeignKey(Product, on_delete=models.PROTECT, verbose_name="Producto")
    quantity = models.PositiveIntegerField(verbose_name="Cantidad")
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Precio Unitario")
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Subtotal")

    class Meta:
        verbose_name = "Detalle de Venta"
        verbose_name_plural = "Detalles de Venta"

    def __str__(self):
        return f"{self.quantity}x {self.product.name} (Venta {self.sale.invoice_number})"
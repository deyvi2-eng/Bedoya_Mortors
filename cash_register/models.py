from django.db import models
from core.models import BaseModel
from accounts.models import User

class CashSession(BaseModel):
    user = models.ForeignKey(User, on_delete=models.PROTECT, verbose_name="Cajero/Vendedor")
    opening_time = models.DateTimeField(auto_now_add=True, verbose_name="Apertura")
    closing_time = models.DateTimeField(null=True, blank=True, verbose_name="Cierre")
    
    opening_balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name="Fondo Inicial")
    
    # Totales calculados al momento del cierre
    total_cash = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name="Total Efectivo Vendido")
    total_transfer = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name="Total Transferencias")
    total_card = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name="Total Tarjeta")
    
    expected_balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name="Efectivo Esperado")
    actual_balance = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="Efectivo Físico Real")
    difference = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name="Diferencia (Sobrante/Faltante)")
    
    is_open = models.BooleanField(default=True, verbose_name="Estado de Caja")
    observations = models.TextField(blank=True, null=True, verbose_name="Observaciones")

    class Meta:
        verbose_name = "Sesión de Caja"
        verbose_name_plural = "Sesiones de Caja"
        ordering = ['-opening_time']

    def __str__(self):
        estado = "ABIERTA" if self.is_open else "CERRADA"
        return f"Caja {self.id} - {self.user.username} ({estado})"
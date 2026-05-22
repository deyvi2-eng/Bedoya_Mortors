from django.db import models
from core.models import BaseModel
from accounts.models import User

class CashSession(BaseModel):
    class Status(models.TextChoices):
        OPEN = 'OPEN', 'Abierta'
        CLOSED = 'CLOSED', 'Cerrada'

    user = models.ForeignKey(User, on_delete=models.PROTECT, verbose_name="Cajero / Vendedor")
    opening_time = models.DateTimeField(auto_now_add=True, verbose_name="Fecha y Hora de Apertura")
    closing_time = models.DateTimeField(blank=True, null=True, verbose_name="Fecha y Hora de Cierre")
    
    opening_balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name="Saldo Inicial")
    system_balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name="Total en Sistema")
    declared_balance = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True, verbose_name="Total Declarado (Físico)")
    discrepancy = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name="Diferencia (Sobrante/Faltante)")
    
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.OPEN, verbose_name="Estado de Caja")
    observations = models.TextField(blank=True, null=True, verbose_name="Observaciones de Cierre")

    class Meta:
        verbose_name = "Sesión de Caja"
        verbose_name_plural = "Sesiones de Caja"
        ordering = ['-opening_time']

    def __str__(self):
        return f"Caja {self.id} - {self.user.get_full_name()} ({self.get_status_display()})"
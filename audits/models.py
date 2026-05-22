from django.db import models
from accounts.models import User

class AuditLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name="Usuario")
    action = models.CharField(max_length=10, verbose_name="Acción (POST/PUT/DELETE)")
    path = models.CharField(max_length=255, verbose_name="Ruta / Módulo")
    ip_address = models.GenericIPAddressField(null=True, blank=True, verbose_name="Dirección IP")
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name="Fecha y Hora")
    
    class Meta:
        verbose_name = "Registro de Auditoría"
        verbose_name_plural = "Registros de Auditoría"
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.user} - {self.action} en {self.path} ({self.timestamp.strftime('%Y-%m-%d %H:%M')})"
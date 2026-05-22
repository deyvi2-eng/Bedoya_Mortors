from django.db import models
from core.models import BaseModel
from .validators import validate_ecuadorian_cedula

class Customer(BaseModel):
    cedula = models.CharField(
        max_length=10, 
        unique=True, 
        validators=[validate_ecuadorian_cedula],
        verbose_name="Cédula de Identidad"
    )
    first_name = models.CharField(max_length=100, verbose_name="Nombres")
    last_name = models.CharField(max_length=100, verbose_name="Apellidos")
    phone = models.CharField(max_length=15, verbose_name="Teléfono")
    whatsapp = models.CharField(max_length=15, blank=True, null=True, verbose_name="WhatsApp")
    email = models.EmailField(blank=True, null=True, verbose_name="Correo Electrónico")
    address = models.TextField(verbose_name="Dirección")
    city = models.CharField(max_length=100, verbose_name="Ciudad")
    observations = models.TextField(blank=True, null=True, verbose_name="Observaciones")

    class Meta:
        verbose_name = "Cliente"
        verbose_name_plural = "Clientes"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.cedula})"
from django.db import models
from core.models import BaseModel
from django.core.exceptions import ValidationError
from .validators import ID_TYPE_CHOICES, ID_TYPE_SHORT, ID_CEDULA_EC, normalize_identification

class Customer(BaseModel):
    # Tipo de documento: cédula EC, RUC, cédula venezolana o colombiana
    id_type = models.CharField(
        max_length=10,
        choices=ID_TYPE_CHOICES,
        default=ID_CEDULA_EC,
        verbose_name="Tipo de Documento"
    )
    # Hacemos la cédula opcional (blank=True, null=True). Se valida en clean() según id_type
    cedula = models.CharField(
        max_length=20, 
        verbose_name="Cédula / RUC",
        blank=True, 
        null=True
    )
    first_name = models.CharField(max_length=100, verbose_name="Nombres")
    last_name = models.CharField(max_length=100, verbose_name="Apellidos")
    phone = models.CharField(max_length=15, verbose_name="Teléfono")
    whatsapp = models.CharField(max_length=15, blank=True, null=True, verbose_name="WhatsApp")
    email = models.EmailField(blank=True, null=True, verbose_name="Correo Electrónico")
    
    # Hacemos dirección y ciudad opcionales (blank=True, null=True)
    address = models.TextField(blank=True, null=True, verbose_name="Dirección")
    city = models.CharField(max_length=100, blank=True, null=True, verbose_name="Ciudad")
    
    observations = models.TextField(blank=True, null=True, verbose_name="Observaciones")

    class Meta:
        verbose_name = "Cliente"
        verbose_name_plural = "Clientes"
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(fields=['id_type', 'cedula'], name='unique_customer_document'),
        ]

    def clean(self):
        super().clean()
        try:
            self.cedula = normalize_identification(self.id_type, self.cedula)
        except ValidationError as e:
            raise ValidationError({'cedula': e.messages})

        if self.cedula:
            duplicate = Customer.objects.filter(id_type=self.id_type, cedula=self.cedula).exclude(pk=self.pk)
            if duplicate.exists():
                raise ValidationError({'cedula': f"Ya existe un cliente registrado con {self.get_id_type_display()} {self.cedula}."})

    @property
    def id_label(self):
        """Etiqueta corta del documento: C.I., RUC, C.I. VE, C.C. CO"""
        return ID_TYPE_SHORT.get(self.id_type, 'C.I.')

    def __str__(self):
        # Evitamos mostrar "None" si no hay cédula
        ci_display = f"{self.id_label} {self.cedula}" if self.cedula else "Sin CI"
        return f"{self.first_name} {self.last_name} ({ci_display})"
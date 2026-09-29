from django.db import models
from core.models import BaseModel


class Company(BaseModel):
    """
    Datos de cada negocio que usa el sistema (Muebles M&L, y en el futuro otros).
    Se usan en los encabezados de los PDF y en la interfaz de cada negocio.
    """
    FURNITURE = 'muebles-ml'

    slug = models.SlugField(unique=True, verbose_name="Identificador interno")
    name = models.CharField(max_length=120, verbose_name="Nombre comercial")
    legal_name = models.CharField(max_length=160, blank=True, verbose_name="Razón social / Propietario")
    ruc = models.CharField(max_length=13, blank=True, verbose_name="RUC")
    address = models.CharField(max_length=255, blank=True, verbose_name="Dirección")
    email = models.EmailField(blank=True, verbose_name="Correo electrónico")
    phone = models.CharField(max_length=20, blank=True, verbose_name="Teléfono / WhatsApp")
    logo = models.ImageField(upload_to='companies/logos/', blank=True, null=True, verbose_name="Logo")
    document_notes = models.TextField(
        blank=True,
        verbose_name="Condiciones al pie de los documentos",
        help_text="Ej: garantía, plazos de retiro, formas de pago."
    )

    class Meta:
        verbose_name = "Empresa"
        verbose_name_plural = "Empresas"
        ordering = ['name']

    def __str__(self):
        return self.name

    @classmethod
    def furniture(cls):
        """Devuelve (y crea si no existe) la empresa Muebles M&L."""
        company, _ = cls.objects.get_or_create(
            slug=cls.FURNITURE,
            defaults={
                'name': 'Muebles M&L',
                'document_notes': (
                    'El cliente declara estar de acuerdo con el estado del mueble descrito en este documento. '
                    'Los muebles no retirados en 30 días después de la fecha de entrega generan recargo por bodegaje.'
                ),
            },
        )
        return company

    def snapshot(self):
        """Copia de los datos para dejarlos congelados en cada documento firmado."""
        return {
            'name': self.name, 'legal_name': self.legal_name, 'ruc': self.ruc,
            'address': self.address, 'email': self.email, 'phone': self.phone,
        }

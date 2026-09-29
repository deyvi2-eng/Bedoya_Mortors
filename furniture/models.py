import uuid
from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils import timezone

from core.models import BaseModel


class Client(BaseModel):
    """Clientes de Muebles M&L (separados de los clientes de Bedoya Motors)."""
    name = models.CharField(max_length=150, verbose_name="Nombre completo")
    id_number = models.CharField(max_length=13, blank=True, verbose_name="Cédula / RUC")
    phone = models.CharField(max_length=20, verbose_name="Celular / WhatsApp")
    email = models.EmailField(blank=True, verbose_name="Correo")
    address = models.CharField(max_length=255, blank=True, verbose_name="Dirección")
    notes = models.TextField(blank=True, verbose_name="Notas")

    class Meta:
        verbose_name = "Cliente (Muebles)"
        verbose_name_plural = "Clientes (Muebles)"
        ordering = ['name']

    def __str__(self):
        return self.name

    @property
    def whatsapp_number(self):
        """Convierte 0991234567 → 593991234567 (formato que exige wa.me)."""
        digits = ''.join(ch for ch in self.phone if ch.isdigit())
        if digits.startswith('593'):
            return digits
        if digits.startswith('0'):
            return '593' + digits[1:]
        if len(digits) == 9:
            return '593' + digits
        return digits

    def to_dict(self):
        return {
            'id': self.id, 'name': self.name, 'id_number': self.id_number,
            'phone': self.phone, 'email': self.email, 'address': self.address,
        }


class Kind(models.TextChoices):
    REUPHOLSTERY = 'RETAPIZADO', 'Retapizado'
    MANUFACTURING = 'FABRICACION', 'Fabricación'


class ItemsMixin:
    """Totales calculados a partir de los ítems (nunca se escriben a mano)."""

    @property
    def total(self):
        return sum((item.total for item in self.items.all()), Decimal('0.00'))


class Order(ItemsMixin, BaseModel):
    """Hoja de Entrada / Orden de trabajo."""

    class Status(models.TextChoices):
        RECEIVED = 'RECIBIDO', 'Recibido'
        IN_PROGRESS = 'EN_PROCESO', 'En proceso'
        READY = 'LISTO', 'Listo para entregar'
        DELIVERED = 'ENTREGADO', 'Entregado'
        CANCELLED = 'CANCELADO', 'Cancelado'

    kind = models.CharField(max_length=15, choices=Kind.choices, verbose_name="Tipo de trabajo")
    status = models.CharField(max_length=15, choices=Status.choices, default=Status.RECEIVED, verbose_name="Estado")
    client = models.ForeignKey(Client, on_delete=models.PROTECT, related_name='orders', verbose_name="Cliente")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='+')
    quote = models.ForeignKey('Quote', on_delete=models.SET_NULL, null=True, blank=True, related_name='orders', verbose_name="Proforma de origen")

    observations = models.TextField(blank=True, verbose_name="Estado actual / Observaciones")
    requirements = models.TextField(blank=True, verbose_name="Requerimientos del cliente")

    deposit = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'), verbose_name="Abono")
    delivery_date = models.DateField(null=True, blank=True, verbose_name="Fecha de entrega")
    delivered_at = models.DateTimeField(null=True, blank=True)

    owner_signature = models.ImageField(upload_to='furniture/signatures/', blank=True, null=True)
    owner_signer_name = models.CharField(max_length=120, blank=True)
    client_signature = models.ImageField(upload_to='furniture/signatures/', blank=True, null=True)
    signed_at = models.DateTimeField(null=True, blank=True)

    # Datos de la empresa congelados al crear el documento (validez legal)
    company_snapshot = models.JSONField(default=dict, blank=True)
    public_token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)

    class Meta:
        verbose_name = "Hoja de entrada"
        verbose_name_plural = "Hojas de entrada"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.number} - {self.client}"

    @property
    def number(self):
        return f"HE-{self.id:05d}" if self.id else "HE-NUEVA"

    @property
    def balance(self):
        return max(self.total - self.deposit, Decimal('0.00'))

    @property
    def is_overdue(self):
        return (
            self.delivery_date is not None
            and self.status in (self.Status.RECEIVED, self.Status.IN_PROGRESS)
            and self.delivery_date < timezone.localdate()
        )

    @property
    def is_open(self):
        return self.status not in (self.Status.DELIVERED, self.Status.CANCELLED)


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    quantity = models.DecimalField(max_digits=8, decimal_places=2, default=1, verbose_name="Cantidad")
    description = models.CharField(max_length=255, verbose_name="Descripción")
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Valor unitario")

    class Meta:
        ordering = ['id']

    @property
    def total(self):
        return (self.quantity * self.unit_price).quantize(Decimal('0.01'))


class OrderPhoto(models.Model):
    class Stage(models.TextChoices):
        CURRENT = 'ACTUAL', 'Estado actual'
        REFERENCE = 'REFERENCIA', 'Referencia / diseño'
        PROGRESS = 'AVANCE', 'Avance'
        FINISHED = 'TERMINADO', 'Terminado'

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='photos')
    image = models.ImageField(upload_to='furniture/orders/%Y/%m/')
    stage = models.CharField(max_length=12, choices=Stage.choices, default=Stage.CURRENT)
    caption = models.CharField(max_length=255, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['uploaded_at']


class StatusLog(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='status_logs')
    status = models.CharField(max_length=15, choices=Order.Status.choices)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='+')
    at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['at']


class Quote(ItemsMixin, BaseModel):
    """Proforma / Cotización rápida."""

    class Status(models.TextChoices):
        DRAFT = 'PENDIENTE', 'Pendiente'
        ACCEPTED = 'ACEPTADA', 'Aceptada'
        REJECTED = 'RECHAZADA', 'Rechazada'

    kind = models.CharField(max_length=15, choices=Kind.choices, default=Kind.REUPHOLSTERY, verbose_name="Tipo de trabajo")
    status = models.CharField(max_length=15, choices=Status.choices, default=Status.DRAFT)
    client = models.ForeignKey(Client, on_delete=models.PROTECT, related_name='quotes', verbose_name="Cliente")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='+')
    notes = models.TextField(blank=True, verbose_name="Detalle / condiciones")
    valid_days = models.PositiveIntegerField(default=15, verbose_name="Validez (días)")
    company_snapshot = models.JSONField(default=dict, blank=True)
    public_token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)

    class Meta:
        verbose_name = "Proforma"
        verbose_name_plural = "Proformas"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.number} - {self.client}"

    @property
    def number(self):
        return f"PR-{self.id:05d}" if self.id else "PR-NUEVA"

    @property
    def valid_until(self):
        return timezone.localtime(self.created_at).date() + timedelta(days=self.valid_days)


class QuoteItem(models.Model):
    quote = models.ForeignKey(Quote, on_delete=models.CASCADE, related_name='items')
    quantity = models.DecimalField(max_digits=8, decimal_places=2, default=1)
    description = models.CharField(max_length=255)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        ordering = ['id']

    @property
    def total(self):
        return (self.quantity * self.unit_price).quantize(Decimal('0.01'))


class QuotePhoto(models.Model):
    quote = models.ForeignKey(Quote, on_delete=models.CASCADE, related_name='photos')
    image = models.ImageField(upload_to='furniture/quotes/%Y/%m/')
    caption = models.CharField(max_length=255, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['uploaded_at']

from django.db import models
from django.utils import timezone

# Importaciones de otras apps de tu ERP
from customers.models import Customer
from inventory.models import Product


class ServiceOrder(models.Model):
    """Hoja de Ingreso y Orden de Reparación (Taller)"""
    STATUS_CHOICES = [
        ('pending', 'Pendiente / En Espera'),
        ('in_progress', 'En Reparación'),
        ('ready', 'Listo (Terminado)'),
        ('delivered', 'Entregado al Cliente')
    ]

    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name='service_orders', verbose_name="Cliente")
    
    # Datos de la Motocicleta
    license_plate = models.CharField(max_length=20, verbose_name="Placa")
    brand = models.CharField(max_length=50, verbose_name="Marca")
    model = models.CharField(max_length=50, verbose_name="Modelo")
    color = models.CharField(max_length=30, verbose_name="Color")
    mileage = models.PositiveIntegerField(verbose_name="Kilometraje Ingreso", default=0)
    serial_number = models.CharField(max_length=100, blank=True, null=True, verbose_name="No. Serie / Chasis")
    arrived_by_crane = models.BooleanField(default=False, verbose_name="Ingreso en Grúa")
    
    # Trabajo, Observaciones y Nuevos Campos (Los que causaban el error)
    # Cámbialo a esto:
    work_to_do = models.TextField(verbose_name="Trabajo a Realizar", default="", blank=True)
    observations = models.TextField(blank=True, null=True, verbose_name="Observaciones Técnicas Generales")
    customer_observation = models.TextField(blank=True, null=True, verbose_name="Observación y Peticiones del Cliente")
    
    # Mapas y Checklist JSON
    damage_map_data = models.JSONField(default=list, blank=True, verbose_name="Puntos del Mapa de Daños")
    condition_checklist = models.JSONField(default=dict, blank=True, verbose_name="Estado de la Motocicleta (B/M)")
    # El inventario detallado lo guardaremos en condition_checklist unificado desde el frontend, 
    # pero si en el futuro necesitas un campo separado, aquí está:
    detailed_inventory = models.JSONField(default=list, blank=True, verbose_name="Inventario Detallado")
    
    # Nivel de Gasolina y Abono
    fuel_level = models.CharField(max_length=20, default='1/2', verbose_name="Nivel de Combustible")
    deposit_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name="Abono Inicial ($)")
    left_keys = models.BooleanField(default=False, verbose_name="Dejó Llaves")
    left_helmet = models.BooleanField(default=False, verbose_name="Dejó Casco")
    left_registration = models.BooleanField(default=False, verbose_name="Dejó Matrícula")
    # Control de Estados y Tiempos
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name="Estado de la Orden")
    created_at = models.DateTimeField(default=timezone.now, verbose_name="Fecha de Ingreso")
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name="Fecha de Finalización")
    
    # Firma Legal
    client_signature_base64 = models.TextField(blank=True, null=True, verbose_name="Firma Digital")
    intake_pdf = models.FileField(upload_to='workshop/pdfs/intakes/', blank=True, null=True, verbose_name="PDF de Ingreso")
    def __str__(self):
        return f"Orden #{self.id} - {self.license_plate} ({self.get_status_display()})"


class ServiceMedia(models.Model):
    """Almacena Fotos o 1 Video corto de evidencia. Optimizado para Cloudinary."""
    service_order = models.ForeignKey(ServiceOrder, on_delete=models.CASCADE, related_name='media_files')
    media_file = models.FileField(upload_to='workshop/%Y/%m/', verbose_name="Archivo Multimedia")
    is_video = models.BooleanField(default=False, help_text="Marca si es un video")
    description = models.TextField(blank=True, null=True, verbose_name="Comentario / Detalle de la foto") # Cambiado a TextField para los comentarios
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        tipo = "Video" if self.is_video else "Foto"
        return f"{tipo} para Orden #{self.service_order.id}"


class ServiceItem(models.Model):
    """Detalle de repuestos y mano de obra usados en la reparación"""
    service_order = models.ForeignKey(ServiceOrder, on_delete=models.CASCADE, related_name='items')
    
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Repuesto Físico")
    description = models.CharField(max_length=200, verbose_name="Descripción (Mano de obra o Repuesto)")
    
    quantity = models.PositiveIntegerField(default=1, verbose_name="Cantidad")
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Precio Unitario ($)")
    
    def get_subtotal(self):
        return self.quantity * self.price

    def __str__(self):
        return f"{self.quantity}x {self.description} - Orden #{self.service_order.id}"
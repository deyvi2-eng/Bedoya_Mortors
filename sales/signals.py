from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db import transaction
from .models import SaleDetail
from inventory.models import StockMovement
from notifications.services import trigger_stock_alert_async

@receiver(post_save, sender=SaleDetail)
def deduct_inventory_and_register_movement(sender, instance, created, **kwargs):
    if created and not instance.sale.is_voided:
        with transaction.atomic():
            producto = instance.product
            
            # 1. Descuento de stock
            producto.stock_actual -= instance.quantity
            producto.save()
            
            # 2. Registro de auditoría / trazabilidad
            StockMovement.objects.create(
                product=producto,
                movement_type='OUT',
                quantity=instance.quantity,
                description=f"Venta registrada. Factura #{instance.sale.invoice_number}",
                user=instance.sale.seller
            )

            # 3. Disparador de Alertas Inteligente
            # Solo envía correo si el stock actual cae exactamente en o por debajo del mínimo, 
            # y evitamos enviar correos por cada venta si ya estaba en crítico (optimización).
            if producto.stock_actual == producto.stock_minimo or producto.stock_actual == producto.stock_critico:
                trigger_stock_alert_async(producto)
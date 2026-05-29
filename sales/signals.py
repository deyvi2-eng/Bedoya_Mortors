from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import SaleDetail
from notifications.services import trigger_stock_alert_async

@receiver(post_save, sender=SaleDetail)
def check_inventory_and_alert(sender, instance, created, **kwargs):
    # 1. Ignorar si la venta es anulada.
    # 2. Ignorar si es un SERVICIO o Mano de Obra (evita el error AttributeError: NoneType).
    if not created or instance.sale.is_voided or getattr(instance, 'is_service', False) or instance.product is None:
        return

    producto = instance.product

    # ==============================================================
    # NOTA: El descuento de inventario y la creación del Kardex 
    # (StockMovement) ya se realizan de manera segura en el views.py 
    # antes de que se dispare este signal. Hacerlo aquí duplicaría 
    # las salidas de inventario.
    # ==============================================================

    # 3. Disparador de Alertas Inteligente
    # Solo envía correo si el stock actual cae exactamente en o por debajo del mínimo, 
    # y evitamos enviar correos por cada venta si ya estaba en crítico (optimización).
    if producto.stock_actual == producto.stock_minimo or producto.stock_actual == producto.stock_critico:
        trigger_stock_alert_async(producto)
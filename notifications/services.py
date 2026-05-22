import threading
from django.core.mail import send_mail
from django.conf import settings

def send_critical_stock_email(product_name, product_code, current_stock, minimum_stock):
    """
    Función interna que se comunica con el servidor SMTP.
    """
    subject = f"⚠️ ALERTA: Stock Crítico - {product_code}"
    
    message = (
        f"SISTEMA ERP BEDOYA MOTORS\n"
        f"----------------------------------------\n\n"
        f"Se notifica que un repuesto requiere reabastecimiento inmediato:\n\n"
        f"Producto: {product_name}\n"
        f"Código: {product_code}\n"
        f"Stock Actual: {current_stock} unidades\n"
        f"Nivel Mínimo Permitido: {minimum_stock} unidades\n\n"
        f"Por favor, contacte a su proveedor lo antes posible para evitar quiebres de inventario.\n"
    )
    
    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.EMAIL_HOST_USER,
            recipient_list=[settings.ADMIN_ALERTS_EMAIL],
            fail_silently=False,
        )
    except Exception as e:
        # En producción, este error se enviaría a un log de errores (ej. Sentry)
        print(f"Error al enviar correo de alerta: {e}")

def trigger_stock_alert_async(product):
    """
    Lanza el envío de correo en un hilo secundario para no bloquear el Frontend (POS).
    """
    thread = threading.Thread(
        target=send_critical_stock_email,
        args=(product.name, product.code, product.stock_actual, product.stock_minimo)
    )
    thread.start()
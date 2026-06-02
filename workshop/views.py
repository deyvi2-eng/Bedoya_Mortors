from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db import transaction
from django.utils import timezone
from django.http import HttpResponse
from django.template.loader import render_to_string

# Modelos del Módulo Taller
from .models import ServiceOrder, ServiceMedia, ServiceItem
from .forms import ServiceOrderForm

# Modelos de otros módulos del ERP
from inventory.models import Product
from sales.models import Sale, SaleDetail
from cash_register.models import CashSession


def workshop_dashboard(request):
    """Vista principal que separa las motos ingresadas por su estado"""
    
    # 1. Motos en el taller (Pendientes o En Reparación)
    active_orders = ServiceOrder.objects.filter(
        status__in=['pending', 'in_progress']
    ).order_by('-created_at')
    
    # 2. Motos listas o ya entregadas (El histórico)
    completed_orders = ServiceOrder.objects.filter(
        status__in=['ready', 'delivered']
    ).order_by('-completed_at', '-created_at') # Las más recientes primero

    context = {
        'active_orders': active_orders,
        'completed_orders': completed_orders,
    }
    return render(request, 'workshop/dashboard.html', context)


def create_intake(request):
    """Crea una nueva orden de recepción de vehículo"""
    
    # Definimos la matriz aquí de forma elegante
    checklist_items = [
        ('espejo', 'Espejos'), ('rines', 'Rines'), ('asiento', 'Asiento'),
        ('pintura', 'Pintura'), ('bateria', 'Batería'), ('direccionales', 'Direccionales'),
        ('faro', 'Faro Principal'), ('filtro_aire', 'Filtro de Aire'), ('stop', 'Stop'),
        ('tapon_radiador', 'Tapón Radiador'), ('posapies', 'Posapies'),
        ('tanque', 'Tanque'), ('maniguetas', 'Maniguetas'), ('llaves', 'Llaves')
    ]

    if request.method == 'POST':
        form = ServiceOrderForm(request.POST)
        signature_data = request.POST.get('signature_base64')
        media_files = request.FILES.getlist('media_uploads')
        
        # Capturamos el mapa de daños (que ahora son 3 vistas) y el nuevo inventario detallado
        damage_map_data = request.POST.get('damage_map_data', '{}')
        detailed_inventory = request.POST.get('detailed_inventory_data', '[]')
        
        condition_data = {}
        for key, label in checklist_items:
            condition_data[key] = request.POST.get(f'chk_{key}', '')

        if form.is_valid():
            service_order = form.save(commit=False)
            if signature_data:
                service_order.client_signature_base64 = signature_data
                
            service_order.condition_checklist = condition_data
            
            # Guardamos los nuevos datos JSON
            import json
            service_order.damage_map_data = json.loads(damage_map_data)
            service_order.detailed_inventory = json.loads(detailed_inventory)
            
            service_order.status = 'pending'
            service_order.save()
            
            for file in media_files:
                is_video = file.content_type.startswith('video/')
                ServiceMedia.objects.create(service_order=service_order, media_file=file, is_video=is_video)
                
            messages.success(request, f"¡Vehículo {service_order.license_plate} ingresado con éxito!")
            return redirect('workshop:workshop_dashboard') 
        else:
            messages.error(request, "Por favor corrige los errores del formulario.")
    else:
        form = ServiceOrderForm()

    return render(request, 'workshop/intake_form.html', {
        'form': form,
        'checklist_items': checklist_items
    })


def generate_entry_pdf(request, order_id):
    import weasyprint
    """Genera el PDF de ingreso con la evidencia fotográfica y legal"""
    # Traemos la orden
    order = get_object_or_404(ServiceOrder, id=order_id)
    
    # Filtramos las fotos de la orden (ignoramos videos para impresión)
    photos = order.media_files.filter(is_video=False)

    # Contexto para el HTML
    context = {
        'order': order,
        'photos': photos,
    }
    
    # Renderizamos el HTML como un string
    html_string = render_to_string('workshop/intake_pdf.html', context, request=request)
    
    # Convertimos a PDF (base_url es crucial para que carguen los logos y fotos)
    pdf_file = weasyprint.HTML(
        string=html_string, 
        base_url=request.build_absolute_uri()
    ).write_pdf()
    
    # Configuramos la respuesta HTTP
    response = HttpResponse(pdf_file, content_type='application/pdf')
    # Usamos 'inline' para que se vea en el navegador. Cambia a 'attachment' para forzar descarga.
    response['Content-Disposition'] = f'inline; filename="Ingreso_{order.license_plate}_{order.id}.pdf"'
    
    return response


def change_status(request, order_id, new_status):
    """Cambia el estado de la orden mediante botones y registra la fecha de finalización"""
    order = get_object_or_404(ServiceOrder, id=order_id)
    
    # Validar que el estado sea correcto
    valid_statuses = dict(ServiceOrder.STATUS_CHOICES).keys()
    if new_status in valid_statuses:
        order.status = new_status
        
        # Si se marca como lista o entregada, guardamos la hora exacta
        if new_status in ['ready', 'delivered'] and not order.completed_at:
            order.completed_at = timezone.now()
            
        order.save()
        messages.success(request, f"El estado de la placa {order.license_plate} cambió a: {order.get_status_display()}")
    
    return redirect('workshop:workshop_dashboard')


def service_checkout(request, order_id):
    """Vista para liquidar la orden, agregar repuestos y mano de obra"""
    order = get_object_or_404(ServiceOrder, id=order_id)
    products = Product.objects.filter(stock__gt=0) # Solo productos con stock disponible
    
    if request.method == 'POST':
        # Aquí procesaremos los items que se agreguen
        product_id = request.POST.get('product_id')
        description = request.POST.get('description')
        quantity = int(request.POST.get('quantity', 1))
        price = float(request.POST.get('price', 0.00))
        
        # Si se seleccionó un producto del inventario, jalamos su nombre y precio oficial
        product = None
        if product_id:
            product = Product.objects.get(id=product_id)
            description = product.name
            price = product.sale_price # Aseguramos usar el precio de venta del sistema
            
        ServiceItem.objects.create(
            service_order=order,
            product=product,
            description=description,
            quantity=quantity,
            price=price
        )
        messages.success(request, "Ítem agregado a la orden.")
        return redirect('workshop:service_checkout', order_id=order.id)
        
    # Calcular totales
    items = order.items.all()
    total_items = sum(item.get_subtotal() for item in items)
    balance_due = total_items - order.deposit_amount

    context = {
        'order': order,
        'items': items,
        'products': products,
        'total_items': total_items,
        'balance_due': balance_due,
    }
    return render(request, 'workshop/checkout.html', context)


def finalize_service_order(request, order_id):
    """Convierte la Orden en una Factura Oficial, descuenta inventario y cierra la orden"""
    order = get_object_or_404(ServiceOrder, id=order_id)
    
    # 1. Verificar que la caja esté abierta
    session = CashSession.objects.filter(is_active=True).first()
    if not session:
        messages.error(request, "Caja cerrada. Abra la caja en el POS para poder facturar la entrega.")
        return redirect('workshop:service_checkout', order_id=order.id)

    items = order.items.all()
    if not items.exists():
        messages.error(request, "Debe agregar al menos un repuesto o mano de obra para facturar.")
        return redirect('workshop:service_checkout', order_id=order.id)

    total = sum(item.get_subtotal() for item in items)
    balance_due = total - order.deposit_amount

    # Usamos transaction.atomic() para que si algo falla, no se guarde nada a medias
    with transaction.atomic():
        # 2. Crear la Venta oficial en el sistema (Módulo Sales)
        sale = Sale.objects.create(
            customer=order.customer,
            seller=request.user,
            cash_session=session,
            total=total,
            balance_due=balance_due if balance_due > 0 else 0,
            status='paid' if balance_due <= 0 else 'pending'
        )
        
        # 3. Mapear los items del taller a la factura y descontar stock
        for item in items:
            SaleDetail.objects.create(
                sale=sale,
                product=item.product,
                quantity=item.quantity,
                price=item.price,
                is_service=item.product is None,
                service_description=item.description if item.product is None else ''
            )
            
            # 4. Descuento estricto de inventario físico
            if item.product:
                item.product.stock -= item.quantity
                item.product.save()

        # 5. Cerrar la orden de taller
        order.status = 'delivered'
        order.completed_at = timezone.now()
        order.save()

    messages.success(request, f"Factura generada y vehículo entregado con éxito. Ingresos en caja actualizados.")
    return redirect('workshop:workshop_dashboard')
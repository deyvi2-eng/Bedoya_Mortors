from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db import transaction
from django.utils import timezone
from django.http import HttpResponse
from django.template.loader import render_to_string, get_template

# Importación para generar PDF sin dependencias del sistema (Ideal para Render)
from xhtml2pdf import pisa

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
    
    # ⚠️ LISTA ACTUALIZADA CON LOS NOMBRES EXACTOS DEL NUEVO HTML DE INGRESO
    checklist_keys = [
        'espejos', 'pito', 'placa', 'tapa-gas', 'templadores', 'timon', 'velocimetro', 'pintura', 'faros',
        'botones', 'carburador', 'estribos', 'filtro-gas', 'perneria', 'switch', 'bateria',
        'acc-pato', 'alarma', 'baul', 'fusiblera', 'herramientas', 'inox', 'medidor-aceite', 'radiador'
    ]

    if request.method == 'POST':
        form = ServiceOrderForm(request.POST)
        signature_data = request.POST.get('signature_base64')
        media_files = request.FILES.getlist('media_uploads')
        
        # Capturamos el mapa de daños
        damage_map_data = request.POST.get('damage_map_data', '[]')
        
        # ⚠️ CAPTURAR LAS NUEVAS OBSERVACIONES DE INVENTARIO
        inventory_obs = request.POST.get('inventory_observations', '')
        
        # Capturamos toda la matriz B/M iterando sobre la nueva lista
        condition_data = {}
        for key in checklist_keys:
            val = request.POST.get(f'chk_{key}')
            if val: # Solo guardamos si marcó B o M
                condition_data[key] = val

        if form.is_valid():
            service_order = form.save(commit=False)
            
            # Si el usuario llenó observaciones de inventario, lo concatenamos a las generales
            if inventory_obs:
                if service_order.observations:
                    service_order.observations += f"\nObs. Inventario Extra: {inventory_obs}"
                else:
                    service_order.observations = f"Obs. Inventario Extra: {inventory_obs}"

            # Manejo de los checkbox del cliente (Llaves, casco, matrícula)
            service_order.left_keys = request.POST.get('left_keys') == 'on'
            service_order.left_helmet = request.POST.get('left_helmet') == 'on'
            service_order.left_registration = request.POST.get('left_registration') == 'on'
            
            # Asignamos el JSON del checklist
            service_order.condition_checklist = condition_data
            
            # Guardamos los datos JSON del mapa visual
            import json
            service_order.damage_map_data = json.loads(damage_map_data)
            
            # Asignamos la firma
            if signature_data:
                service_order.client_signature_base64 = signature_data
                
            service_order.status = 'pending'
            service_order.save()
            
            # Guardamos la evidencia multimedia
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
        'form': form
    })


def generate_entry_pdf(request, order_id):
    """Genera el PDF de ingreso usando xhtml2pdf (100% Python, compatible con Render)"""
    order = get_object_or_404(ServiceOrder, id=order_id)
    photos = order.media_files.filter(is_video=False)

    # 1. Extraemos el diccionario (Si está vacío, usamos uno nuevo {})
    chk = order.condition_checklist or {}
    
    # 2. Preparamos las listas exactas para las 3 columnas del PDF (Etiqueta, Valor)
    exterior = [
        ('Espejos', chk.get('espejos', 'NA')),
        ('Pito', chk.get('pito', 'NA')),
        ('Placa', chk.get('placa', 'NA')),
        ('Tapa Gasolina', chk.get('tapa-gas', 'NA')),
        ('Templadores', chk.get('templadores', 'NA')),
        ('Timón', chk.get('timon', 'NA')),
        ('Velocímetro', chk.get('velocimetro', 'NA')),
        ('Pintura/Asiento', chk.get('pintura', 'NA')),
        ('Faros/Stops', chk.get('faros', 'NA')),
    ]
    interior = [
        ('Botones/Mandos', chk.get('botones', 'NA')),
        ('Carburador', chk.get('carburador', 'NA')),
        ('Estribos', chk.get('estribos', 'NA')),
        ('Filtro Gasolina', chk.get('filtro-gas', 'NA')),
        ('Pernería', chk.get('perneria', 'NA')),
        ('Switch/Llaves', chk.get('switch', 'NA')),
        ('Batería', chk.get('bateria', 'NA')),
    ]
    accesorios = [
        ('Acc Pato', chk.get('acc-pato', 'NA')),
        ('Alarma', chk.get('alarma', 'NA')),
        ('Baúl/Maletero', chk.get('baul', 'NA')),
        ('Fusiblera', chk.get('fusiblera', 'NA')),
        ('Herramientas', chk.get('herramientas', 'NA')),
        ('Lujos Inox', chk.get('inox', 'NA')),
        ('Medidor Aceite', chk.get('medidor-aceite', 'NA')),
        ('Tapa Radiador', chk.get('radiador', 'NA')),
    ]

    # 3. Mandamos las listas ya procesadas al contexto
    context = {
        'order': order,
        'photos': photos,
        'request': request,
        'exterior': exterior,
        'interior': interior,
        'accesorios': accesorios,
    }
    
    template = get_template('workshop/intake_pdf.html')
    html_string = template.render(context)
    
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="Ingreso_{order.license_plate}_{order.id}.pdf"'
    
    pisa_status = pisa.CreatePDF(html_string, dest=response)
    
    if pisa_status.err:
        return HttpResponse(f"Tuvimos un error al generar el PDF de la orden {order.id}")
    
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
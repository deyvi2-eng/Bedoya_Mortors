import json
import io
import base64
from concurrent.futures import ThreadPoolExecutor

import requests
from PIL import Image, ImageDraw

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db import transaction
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.urls import reverse
from django.core.paginator import Paginator
from django.db.models import Q, Count, F
from django.http import HttpResponse
from django.template.loader import get_template
from django.contrib.staticfiles import finders

# Importación para generar PDF sin dependencias del sistema (Ideal para Render)
from xhtml2pdf import pisa

# Modelos del Módulo Taller
from .models import ServiceOrder, ServiceMedia, ServiceItem
from .forms import ServiceOrderForm

# Modelos de otros módulos del ERP
from inventory.models import Product
from sales.models import Sale, SaleDetail
from cash_register.models import CashSession


WORKSHOP_TABS = [
    ('active', 'En taller', ['pending', 'in_progress']),
    ('pending', 'Pendientes', ['pending']),
    ('in_progress', 'En reparación', ['in_progress']),
    ('ready', 'Listas', ['ready']),
    ('delivered', 'Entregadas', ['delivered']),
    ('all', 'Todas', None),
]
WORKSHOP_PAGE_SIZE = 12


def workshop_dashboard(request):
    """Panel del taller: pestañas por estado, búsqueda y paginación"""
    current_tab = request.GET.get('tab', 'active')
    tabs_by_key = {key: statuses for key, _, statuses in WORKSHOP_TABS}
    if current_tab not in tabs_by_key:
        current_tab = 'active'
    query = request.GET.get('q', '').strip()

    orders = ServiceOrder.objects.select_related('customer')
    if query:
        orders = orders.filter(
            Q(license_plate__icontains=query) | Q(brand__icontains=query) | Q(model__icontains=query) |
            Q(customer__first_name__icontains=query) | Q(customer__last_name__icontains=query) |
            Q(customer__cedula__icontains=query)
        )

    # Conteos por estado (respetan la búsqueda) en una sola consulta
    status_counts = dict(orders.values_list('status').annotate(n=Count('id')))
    tabs = []
    for key, label, statuses in WORKSHOP_TABS:
        total = sum(status_counts.get(st, 0) for st in statuses) if statuses else sum(status_counts.values())
        tabs.append({'key': key, 'label': label, 'count': total})

    statuses = tabs_by_key[current_tab]
    if statuses:
        orders = orders.filter(status__in=statuses)
    if current_tab in ('ready', 'delivered'):
        orders = orders.order_by(F('completed_at').desc(nulls_last=True), '-created_at')
    else:
        orders = orders.order_by('-created_at')

    page_obj = Paginator(orders, WORKSHOP_PAGE_SIZE).get_page(request.GET.get('page'))

    context = {
        'page_obj': page_obj,
        'orders': page_obj.object_list,
        'page_range': page_obj.paginator.get_elided_page_range(page_obj.number, on_each_side=1, on_ends=1),
        'tabs': tabs,
        'current_tab': current_tab,
        'query': query,
        'stats': {
            'pending': status_counts.get('pending', 0),
            'in_progress': status_counts.get('in_progress', 0),
            'ready': status_counts.get('ready', 0),
            'delivered': status_counts.get('delivered', 0),
        },
    }
    return render(request, 'workshop/dashboard.html', context)


def _back_to_dashboard(request):
    """Vuelve a la misma pestaña/página del panel desde donde se hizo la acción"""
    referer = request.META.get('HTTP_REFERER')
    if referer and url_has_allowed_host_and_scheme(referer, allowed_hosts={request.get_host()}) \
            and reverse('workshop:workshop_dashboard') in referer:
        return redirect(referer)
    return redirect('workshop:workshop_dashboard')


def create_intake(request):
    """Crea una nueva orden de recepción de vehículo"""
    
    # NOMBRES EXACTOS SACADOS DE TU HTML FRONTEND
    checklist_keys = [
        'espejos', 'pito', 'placa', 'tapa-gas', 'templadores', 'timon', 'velocimetro', 'pintura', 'faros',
        'botones', 'carburador', 'estribos', 'filtro-gas', 'perneria', 'switch', 'bateria',
        'acc-pato', 'alarma', 'baul', 'fusiblera', 'herramientas', 'inox', 'medidor-aceite', 'radiador'
    ]

    if request.method == 'POST':
        form = ServiceOrderForm(request.POST)
        signature_data = request.POST.get('signature_base64')
        media_files = request.FILES.getlist('media_uploads')
        
        # Capturas de JSON y observaciones
        damage_map_data = request.POST.get('damage_map_data', '[]')
        media_comments_data = request.POST.get('media_comments_data', '[]')
        inventory_obs = request.POST.get('inventory_observations', '')
        
        try:
            media_comments = json.loads(media_comments_data)
        except:
            media_comments = []

        condition_data = {}
        for key in checklist_keys:
            val = request.POST.get(f'chk_{key}')
            if val:
                condition_data[key] = val

        if form.is_valid():
            service_order = form.save(commit=False)
            
            # Guardamos las observaciones de inventario
            if inventory_obs:
                obs_text = f"Novedades Inventario Extra: {inventory_obs}"
                service_order.observations = f"{service_order.observations}\n\n{obs_text}" if service_order.observations else obs_text

            # 🛠️ CORRECCIÓN: Checkboxes infalibles (Si el checkbox existe en el POST, es True)
            service_order.left_keys = bool(request.POST.get('left_keys'))
            service_order.left_helmet = bool(request.POST.get('left_helmet'))
            service_order.left_registration = bool(request.POST.get('left_registration'))
            
            service_order.condition_checklist = condition_data
            service_order.damage_map_data = json.loads(damage_map_data)
            
            if signature_data:
                service_order.client_signature_base64 = signature_data
                
            service_order.status = 'pending'
            service_order.save()
            
            # Guardar fotos con su comentario respectivo
            for index, file in enumerate(media_files):
                is_video = file.content_type.startswith('video/')
                comment = media_comments[index] if index < len(media_comments) else ""
                ServiceMedia.objects.create(
                    service_order=service_order, 
                    media_file=file, 
                    is_video=is_video,
                    description=comment # Se guarda el comentario de la foto
                )
            
            messages.success(request, f"¡Vehículo {service_order.license_plate} ingresado con éxito!")
            return redirect('workshop:workshop_dashboard') 
        else:
            messages.error(request, "Por favor corrige los errores del formulario.")
    else:
        form = ServiceOrderForm()

    return render(request, 'workshop/intake_form.html', {'form': form})


# ==========================================
# GENERACIÓN DEL PDF DE INGRESO
# ==========================================
# El PDF se genera al vuelo (no se guarda en Cloudinary: Cloudinary bloquea la
# descarga de PDFs en cuentas gratuitas y eso provocaba el "Internal Server Error").
# Para que sea rápido, todas las imágenes se reducen y se incrustan en base64.

PDF_PHOTO_WIDTH = 500   # px: suficiente para imprimir a 150px de ancho
PDF_PHOTO_TIMEOUT = 8   # s por foto, para nunca colgar el servidor

_static_img_cache = {}


def _jpeg_data_uri(img, max_width, quality=75):
    """Reduce una imagen PIL y la devuelve como data URI JPEG."""
    img = img.convert("RGB")
    if img.width > max_width:
        img = img.resize((max_width, int(img.height * max_width / img.width)), Image.LANCZOS)
    buffer = io.BytesIO()
    img.save(buffer, format="JPEG", quality=quality, optimize=True)
    return f"data:image/jpeg;base64,{base64.b64encode(buffer.getvalue()).decode()}"


def _load_static_image(path, max_width):
    """Abre una imagen estática ya reducida (se cachea en memoria entre peticiones)."""
    key = (path, max_width)
    if key not in _static_img_cache:
        img_path = finders.find(path)
        if not img_path:
            return None
        with Image.open(img_path) as img:
            img = img.convert("RGBA")
            if img.width > max_width:
                img = img.resize((max_width, int(img.height * max_width / img.width)), Image.LANCZOS)
            _static_img_cache[key] = img.copy()
    return _static_img_cache[key].copy()


def _logo_data_uri():
    if 'logo_uri' not in _static_img_cache:
        logo = _load_static_image('img/logo.png', 480)
        if logo is None:
            return None
        buffer = io.BytesIO()
        logo.save(buffer, format="PNG", optimize=True)
        _static_img_cache['logo_uri'] = f"data:image/png;base64,{base64.b64encode(buffer.getvalue()).decode()}"
    return _static_img_cache['logo_uri']


def _damage_map_data_uri(points):
    img = _load_static_image('img/esquema_moto.jpg', 1100)
    if img is None:
        return None
    draw = ImageDraw.Draw(img)
    width, height = img.size
    scale = width / 1100
    r, l, w = int(15 * scale) or 1, int(8 * scale) or 1, max(int(4 * scale), 2)
    for point in points or []:
        try:
            px = int(float(point.get('x', 0)) * width)
            py = int(float(point.get('y', 0)) * height)
        except (TypeError, ValueError, AttributeError):
            continue
        draw.ellipse((px - r, py - r, px + r, py + r), outline="#dc2626", width=w)
        draw.line((px - l, py - l, px + l, py + l), fill="black", width=w)
        draw.line((px - l, py + l, px + l, py - l), fill="black", width=w)
    return _jpeg_data_uri(img, 1100, quality=80)


def _photo_data_uri(media):
    """Descarga una miniatura de la foto (no el original de varios MB) y la incrusta."""
    try:
        name = media.media_file.name
        if not name:
            return None
        if hasattr(media.media_file.storage, '_prepend_prefix'):
            # Cloudinary: pedimos una versión ya reducida y en JPG (convierte HEIC/PNG/etc.)
            import cloudinary
            url = cloudinary.CloudinaryImage(name).build_url(
                width=PDF_PHOTO_WIDTH, crop='limit', quality='auto:eco', fetch_format='jpg', secure=True
            )
            resp = requests.get(url, timeout=PDF_PHOTO_TIMEOUT)
            resp.raise_for_status()
            return f"data:image/jpeg;base64,{base64.b64encode(resp.content).decode()}"
        with media.media_file.open('rb') as f:
            with Image.open(f) as img:
                return _jpeg_data_uri(img, PDF_PHOTO_WIDTH)
    except Exception as e:
        print(f"PDF: no se pudo cargar la foto {media.pk}: {e}")
        return None


def create_pdf_content(order, request):
    """Genera el contenido binario del PDF en memoria"""
    chk = order.condition_checklist or {}
    
    # Preparamos el inventario físico para el PDF
    exterior = [
        ('Espejos', chk.get('espejos', 'NA')), ('Pito', chk.get('pito', 'NA')), ('Placa', chk.get('placa', 'NA')),
        ('Tapa Gasolina', chk.get('tapa-gas', 'NA')), ('Templadores', chk.get('templadores', 'NA')), 
        ('Timón', chk.get('timon', 'NA')), ('Velocímetro', chk.get('velocimetro', 'NA')), 
        ('Pintura/Asiento', chk.get('pintura', 'NA')), ('Faros/Stops', chk.get('faros', 'NA')),
    ]
    interior = [
        ('Botones/Mandos', chk.get('botones', 'NA')), ('Carburador', chk.get('carburador', 'NA')), 
        ('Estribos', chk.get('estribos', 'NA')), ('Filtro Gasolina', chk.get('filtro-gas', 'NA')), 
        ('Pernería', chk.get('perneria', 'NA')), ('Switch/Llaves', chk.get('switch', 'NA')), 
        ('Batería', chk.get('bateria', 'NA')),
    ]
    accesorios = [
        ('Acc Pato', chk.get('acc-pato', 'NA')), ('Alarma', chk.get('alarma', 'NA')), 
        ('Baúl/Maletero', chk.get('baul', 'NA')), ('Fusiblera', chk.get('fusiblera', 'NA')), 
        ('Herramientas', chk.get('herramientas', 'NA')), ('Lujos Inox', chk.get('inox', 'NA')), 
        ('Medidor Aceite', chk.get('medidor-aceite', 'NA')), ('Tapa Radiador', chk.get('radiador', 'NA')),
    ]

    try:
        damage_map_img_b64 = _damage_map_data_uri(order.damage_map_data)
    except Exception as e:
        print(f"Error procesando el mapa de daños: {e}")
        damage_map_img_b64 = None

    try:
        logo_b64 = _logo_data_uri()
    except Exception as e:
        print(f"Error cargando el logo: {e}")
        logo_b64 = None

    # Fotos descargadas en paralelo (miniaturas) para no esperar una por una
    media_list = list(order.media_files.filter(is_video=False))
    with ThreadPoolExecutor(max_workers=6) as pool:
        uris = list(pool.map(_photo_data_uri, media_list))
    photos = [{'src': uri, 'description': m.description} for m, uri in zip(media_list, uris) if uri]

    # La firma sólo se incluye si es una imagen base64 válida
    signature = order.client_signature_base64 or ''
    if not signature.startswith('data:image/'):
        signature = None

    context = {
        'order': order,
        'photos': photos,
        'exterior': exterior,
        'interior': interior,
        'accesorios': accesorios,
        'damage_map_img_b64': damage_map_img_b64, 
        'logo_b64': logo_b64,
        'signature_b64': signature,
    }
    
    template = get_template('workshop/intake_pdf.html')
    html_string = template.render(context)
    
    buffer_pdf = io.BytesIO()
    pisa_status = pisa.CreatePDF(html_string, dest=buffer_pdf, encoding='utf-8')
    
    if pisa_status.err:
        return None
    return buffer_pdf.getvalue()


def generate_entry_pdf(request, order_id):
    """Genera y muestra el PDF de ingreso de la orden"""
    order = get_object_or_404(ServiceOrder, id=order_id)

    try:
        pdf_content = create_pdf_content(order, request)
    except Exception as e:
        print(f"Error generando PDF de la orden {order.id}: {e}")
        pdf_content = None

    if not pdf_content:
        messages.error(request, f"No se pudo generar el PDF de la placa {order.license_plate}. Intenta de nuevo.")
        return redirect('workshop:workshop_dashboard')

    response = HttpResponse(pdf_content, content_type='application/pdf')
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
    
    return _back_to_dashboard(request)


def service_checkout(request, order_id):
    """Vista para liquidar la orden, agregar repuestos y mano de obra"""
    order = get_object_or_404(ServiceOrder, id=order_id)
    products = Product.objects.filter(stock_actual__gt=0)
    
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
                item.product.stock_actual -= item.quantity
                item.product.save()
                
        # 5. Cerrar la orden de taller
        order.status = 'delivered'
        order.completed_at = timezone.now()
        order.save()

    messages.success(request, f"Factura generada y vehículo entregado con éxito. Ingresos en caja actualizados.")
    return redirect('workshop:workshop_dashboard')


def delete_order(request, order_id):
    """Elimina permanentemente una orden de recepción y sus archivos (Fotos/Videos en cascada)"""
    order = get_object_or_404(ServiceOrder, id=order_id)
    
    if request.method == 'POST':
        placa_eliminada = order.license_plate
        # Al ejecutar delete() en la orden, Django eliminará en cascada las fotos de ServiceMedia
        order.delete()
        messages.success(request, f"¡Seguridad: La orden de la placa {placa_eliminada} fue eliminada permanentemente del sistema!")
        
    return _back_to_dashboard(request)
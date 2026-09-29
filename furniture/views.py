import json
from datetime import datetime
from functools import wraps
from urllib.parse import quote as urlquote

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Count, Q
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from companies.models import Company

from .models import Client, Kind, Order, OrderItem, OrderPhoto, Quote, QuoteItem, QuotePhoto, StatusLog
from .services import InvalidData, image_data_uri, parse_items, parse_money, render_pdf, signature_file

MAX_PHOTOS = 15


# =========================================================
# ACCESO
# =========================================================
def can_use_furniture(user):
    return user.is_authenticated and (
        user.is_superuser or getattr(user, 'role', '') in ('MUEBLES', 'ADMIN')
    )


def furniture_required(view):
    """Solo usuarios de Muebles M&L y el administrador."""
    @wraps(view)
    @login_required
    def wrapper(request, *args, **kwargs):
        if not can_use_furniture(request.user):
            return redirect('/')
        return view(request, *args, **kwargs)
    return wrapper


def rows_of(items, size=3):
    """Agrupa en filas de `size` columnas (rellena con None) para la cuadrícula del PDF."""
    rows = [items[i:i + size] for i in range(0, len(items), size)]
    if rows:
        rows[-1] = rows[-1] + [None] * (size - len(rows[-1]))
    return rows


def json_error(message, status=400):
    return JsonResponse({'error': message}, status=status)


def client_from_post(request):
    client_id = request.POST.get('client_id')
    if not client_id:
        raise InvalidData('Seleccione o cree un cliente.')
    try:
        return Client.objects.get(pk=int(client_id), is_active=True)
    except (Client.DoesNotExist, ValueError):
        raise InvalidData('El cliente seleccionado no existe.')


def kind_from_post(request):
    kind = request.POST.get('kind')
    if kind not in Kind.values:
        raise InvalidData('Elija si es Retapizado o Fabricación.')
    return kind


def uploaded_photos(request):
    photos = request.FILES.getlist('photos')
    if len(photos) > MAX_PHOTOS:
        raise InvalidData(f'Máximo {MAX_PHOTOS} fotos por documento.')
    for photo in photos:
        if not (photo.content_type or '').startswith('image/'):
            raise InvalidData(f'"{photo.name}" no es una imagen.')
    captions = request.POST.getlist('photo_captions')
    return [(photo, (captions[i] if i < len(captions) else '')[:255]) for i, photo in enumerate(photos)]


def whatsapp_link(phone_number, text):
    return f"https://wa.me/{phone_number}?text={urlquote(text)}"


# =========================================================
# INICIO
# =========================================================
@furniture_required
def home(request):
    today = timezone.localdate()
    open_orders = Order.objects.filter(is_active=True).exclude(
        status__in=[Order.Status.DELIVERED, Order.Status.CANCELLED]
    ).select_related('client').prefetch_related('items')

    counts = dict(
        Order.objects.filter(is_active=True).order_by().values_list('status').annotate(n=Count('id'))
    )
    received = [o for o in open_orders if o.status == Order.Status.RECEIVED]
    in_progress = [o for o in open_orders if o.status == Order.Status.IN_PROGRESS]
    ready = [o for o in open_orders if o.status == Order.Status.READY]
    context = {
        'company': Company.furniture(),
        'counts': counts,
        'received': received,
        'in_progress': in_progress,
        'ready': ready,
        'board': [
            ('col-received', 'Recibidos', 'bg-sky-500', received),
            ('col-progress', 'En proceso', 'bg-amber-500', in_progress),
            ('col-ready', 'Listos para entregar', 'bg-green-500', ready),
        ],
        'overdue': [o for o in open_orders if o.is_overdue],
        'due_today': [o for o in open_orders if o.delivery_date == today],
        'pending_quotes': Quote.objects.filter(is_active=True, status=Quote.Status.DRAFT).select_related('client')[:5],
        'nav': 'home',
    }
    return render(request, 'furniture/home.html', context)


# =========================================================
# CLIENTES
# =========================================================
@furniture_required
def client_list(request):
    q = request.GET.get('q', '').strip()
    clients = Client.objects.filter(is_active=True).annotate(
        n_orders=Count('orders', distinct=True), n_quotes=Count('quotes', distinct=True)
    )
    if q:
        clients = clients.filter(Q(name__icontains=q) | Q(phone__icontains=q) | Q(id_number__icontains=q))
    return render(request, 'furniture/clients.html', {'clients': clients[:300], 'q': q, 'nav': 'clients'})


@furniture_required
def client_detail(request, pk):
    client = get_object_or_404(Client, pk=pk, is_active=True)
    return render(request, 'furniture/client_detail.html', {
        'client': client,
        'orders': client.orders.filter(is_active=True).prefetch_related('items'),
        'quotes': client.quotes.filter(is_active=True).prefetch_related('items'),
        'nav': 'clients',
    })


@furniture_required
def client_search_api(request):
    q = request.GET.get('q', '').strip()
    clients = Client.objects.filter(is_active=True)
    if q:
        clients = clients.filter(Q(name__icontains=q) | Q(phone__icontains=q) | Q(id_number__icontains=q))
    return JsonResponse({'results': [c.to_dict() for c in clients.order_by('name')[:15]]})


def _fill_client(client, data):
    client.name = (data.get('name') or '').strip()[:150]
    client.phone = (data.get('phone') or '').strip()[:20]
    client.id_number = (data.get('id_number') or '').strip()[:13]
    client.email = (data.get('email') or '').strip()[:254]
    client.address = (data.get('address') or '').strip()[:255]
    client.notes = (data.get('notes') or client.notes or '').strip()
    if not client.name:
        raise InvalidData('Escriba el nombre del cliente.')
    digits = ''.join(ch for ch in client.phone if ch.isdigit())
    if len(digits) < 9:
        raise InvalidData('Escriba un número de celular válido (ej: 0991234567).')
    if client.id_number and (not client.id_number.isdigit() or len(client.id_number) not in (10, 13)):
        raise InvalidData('La cédula debe tener 10 dígitos o el RUC 13.')
    if client.email and '@' not in client.email:
        raise InvalidData('El correo no es válido.')


@furniture_required
@require_POST
def client_save_api(request, pk=None):
    """Crea o edita un cliente. Responde JSON para usarlo desde modales sin recargar."""
    try:
        data = json.loads(request.body or '{}')
    except json.JSONDecodeError:
        return json_error('Datos inválidos.')

    client = get_object_or_404(Client, pk=pk, is_active=True) if pk else Client()
    try:
        _fill_client(client, data)
    except InvalidData as exc:
        return json_error(str(exc))

    if client.id_number and Client.objects.filter(id_number=client.id_number, is_active=True).exclude(pk=client.pk).exists():
        return json_error('Ya existe un cliente con esa cédula/RUC.')

    client.save()
    return JsonResponse({'client': client.to_dict()}, status=200 if pk else 201)


@furniture_required
@require_POST
def client_delete(request, pk):
    client = get_object_or_404(Client, pk=pk, is_active=True)
    client.is_active = False
    client.save(update_fields=['is_active', 'updated_at'])
    messages.success(request, f'Cliente {client.name} eliminado.')
    return redirect('furniture:clients')


# =========================================================
# HOJAS DE ENTRADA (ÓRDENES)
# =========================================================
@furniture_required
def order_list(request):
    status = request.GET.get('estado', 'abiertas')
    q = request.GET.get('q', '').strip()
    orders = Order.objects.filter(is_active=True).select_related('client').prefetch_related('items')

    if status == 'abiertas':
        orders = orders.exclude(status__in=[Order.Status.DELIVERED, Order.Status.CANCELLED])
    elif status in Order.Status.values:
        orders = orders.filter(status=status)

    if q:
        filters = Q(client__name__icontains=q) | Q(client__phone__icontains=q) | Q(observations__icontains=q) | Q(requirements__icontains=q)
        digits = ''.join(ch for ch in q if ch.isdigit())
        if digits:
            filters |= Q(pk=int(digits))
        orders = orders.filter(filters)

    tabs = [('abiertas', 'En taller')] + [(s.value, s.label) for s in Order.Status] + [('todas', 'Todas')]
    return render(request, 'furniture/orders.html', {
        'orders': orders[:200], 'status': status, 'q': q, 'tabs': tabs, 'nav': 'orders',
    })


@furniture_required
def order_create(request):
    if request.method == 'POST':
        return _order_create_post(request)

    kind = request.GET.get('tipo', '').upper()
    source_quote = None
    if request.GET.get('proforma'):
        source_quote = get_object_or_404(Quote, pk=request.GET['proforma'], is_active=True)
        kind = source_quote.kind

    initial = {
        'kind': kind if kind in Kind.values else '',
        'client': source_quote.client.to_dict() if source_quote else None,
        'items': [
            {'quantity': str(i.quantity), 'description': i.description, 'unit_price': str(i.unit_price)}
            for i in source_quote.items.all()
        ] if source_quote else [],
        'requirements': source_quote.notes if source_quote else '',
        'quote_id': source_quote.pk if source_quote else None,
    }
    if not source_quote and request.GET.get('cliente'):
        client = Client.objects.filter(pk=request.GET['cliente'], is_active=True).first()
        initial['client'] = client.to_dict() if client else None
    return render(request, 'furniture/order_form.html', {
        'initial': initial,
        'source_quote': source_quote,
        'quote_photos': source_quote.photos.all() if source_quote else [],
        'owner_name': request.user.get_full_name() or request.user.username,
        'nav': 'new',
    })


def _order_create_post(request):
    try:
        client = client_from_post(request)
        kind = kind_from_post(request)
        items = parse_items(request.POST.get('items'))
        deposit = parse_money(request.POST.get('deposit'))
        photos = uploaded_photos(request)
        client_sig = signature_file(request.POST.get('client_signature'), 'firma_cliente.png')
        owner_sig = signature_file(request.POST.get('owner_signature'), 'firma_responsable.png')
        if not client_sig:
            raise InvalidData('Falta la firma del cliente.')
        if not owner_sig:
            raise InvalidData('Falta la firma del responsable.')
        delivery_date = request.POST.get('delivery_date') or None
        if delivery_date:
            delivery_date = datetime.strptime(delivery_date, '%Y-%m-%d').date()
    except InvalidData as exc:
        return json_error(str(exc))
    except ValueError:
        return json_error('La fecha de entrega no es válida.')

    quote = None
    if request.POST.get('quote_id'):
        quote = Quote.objects.filter(pk=request.POST['quote_id'], is_active=True).first()

    photo_stage = OrderPhoto.Stage.CURRENT if kind == Kind.REUPHOLSTERY else OrderPhoto.Stage.REFERENCE

    with transaction.atomic():
        order = Order.objects.create(
            kind=kind,
            client=client,
            created_by=request.user,
            quote=quote,
            observations=request.POST.get('observations', '').strip(),
            requirements=request.POST.get('requirements', '').strip(),
            deposit=deposit,
            delivery_date=delivery_date,
            owner_signer_name=request.POST.get('owner_signer_name', '').strip()[:120],
            signed_at=timezone.now(),
            company_snapshot=Company.furniture().snapshot(),
        )
        order.client_signature.save(f'cliente_{order.pk}.png', client_sig, save=False)
        order.owner_signature.save(f'responsable_{order.pk}.png', owner_sig, save=False)
        order.save()

        OrderItem.objects.bulk_create([OrderItem(order=order, **item) for item in items])
        for photo, caption in photos:
            OrderPhoto.objects.create(order=order, image=photo, stage=photo_stage, caption=caption)

        if quote:
            # Las fotos de la proforma pasan como referencia (mismo archivo, sin volver a subirlo)
            for qp in quote.photos.all():
                OrderPhoto.objects.create(order=order, image=qp.image.name, stage=OrderPhoto.Stage.REFERENCE, caption=qp.caption)
            quote.status = Quote.Status.ACCEPTED
            quote.save(update_fields=['status', 'updated_at'])

        StatusLog.objects.create(order=order, status=order.status, user=request.user)

    return JsonResponse({'redirect': reverse('furniture:order_detail', args=[order.pk]) + '?nueva=1'}, status=201)


def _order_share_context(request, order):
    pdf_url = request.build_absolute_uri(reverse('furniture:public_order_pdf', args=[order.public_token]))
    company = Company.furniture()
    lines = [
        f"Hola {order.client.name.split(' ')[0]} 👋",
        f"Le saluda *{company.name}*.",
        f"Su hoja de entrada *{order.number}* ({order.get_kind_display()}) está lista:",
        pdf_url,
    ]
    if order.status == Order.Status.READY:
        lines = [
            f"Hola {order.client.name.split(' ')[0]} 👋",
            f"¡Su mueble ya está *listo* en {company.name}! 🛋️",
            f"Orden {order.number}. Saldo pendiente: ${order.balance:.2f}",
            pdf_url,
        ]
    return {
        'pdf_public_url': pdf_url,
        'whatsapp_url': whatsapp_link(order.client.whatsapp_number, '\n'.join(lines)),
    }


@furniture_required
def order_detail(request, pk):
    order = get_object_or_404(
        Order.objects.select_related('client', 'created_by', 'quote').prefetch_related('items', 'photos', 'status_logs__user'),
        pk=pk, is_active=True,
    )
    context = {
        'order': order,
        'is_new': request.GET.get('nueva') == '1',
        'next_status': {
            Order.Status.RECEIVED: (Order.Status.IN_PROGRESS, 'Empezar trabajo', 'ph-hammer'),
            Order.Status.IN_PROGRESS: (Order.Status.READY, 'Marcar como listo', 'ph-check-circle'),
            Order.Status.READY: (Order.Status.DELIVERED, 'Entregar al cliente', 'ph-handshake'),
        }.get(order.status),
        'statuses': Order.Status.choices,
        'stages': OrderPhoto.Stage.choices,
        'nav': 'orders',
        **_order_share_context(request, order),
    }
    return render(request, 'furniture/order_detail.html', context)


@furniture_required
@require_POST
def order_status(request, pk):
    order = get_object_or_404(Order, pk=pk, is_active=True)
    new_status = request.POST.get('status')
    if new_status in Order.Status.values and new_status != order.status:
        order.status = new_status
        order.delivered_at = timezone.now() if new_status == Order.Status.DELIVERED else None
        order.save(update_fields=['status', 'delivered_at', 'updated_at'])
        StatusLog.objects.create(order=order, status=new_status, user=request.user)
        messages.success(request, f'{order.number}: {order.get_status_display()}')
    return redirect('furniture:order_detail', pk=pk)


@furniture_required
@require_POST
def order_payment(request, pk):
    """Registra un abono adicional (se suma al abono existente)."""
    order = get_object_or_404(Order, pk=pk, is_active=True)
    try:
        amount = parse_money(request.POST.get('amount'), 'Monto')
    except InvalidData as exc:
        messages.error(request, str(exc))
        return redirect('furniture:order_detail', pk=pk)
    if amount > 0:
        order.deposit += amount
        order.save(update_fields=['deposit', 'updated_at'])
        messages.success(request, f'Abono de ${amount:.2f} registrado.')
    return redirect('furniture:order_detail', pk=pk)


@furniture_required
@require_POST
def order_add_photos(request, pk):
    order = get_object_or_404(Order, pk=pk, is_active=True)
    stage = request.POST.get('stage')
    if stage not in OrderPhoto.Stage.values:
        return json_error('Elija el tipo de foto.')
    try:
        photos = uploaded_photos(request)
    except InvalidData as exc:
        return json_error(str(exc))
    if not photos:
        return json_error('No se recibió ninguna foto.')
    for photo, caption in photos:
        OrderPhoto.objects.create(order=order, image=photo, stage=stage, caption=caption)
    return JsonResponse({'redirect': reverse('furniture:order_detail', args=[pk]) + '#fotos'}, status=201)


@furniture_required
@require_POST
def order_delete(request, pk):
    order = get_object_or_404(Order, pk=pk, is_active=True)
    order.is_active = False
    order.save(update_fields=['is_active', 'updated_at'])
    messages.success(request, f'{order.number} eliminada.')
    return redirect('furniture:orders')


def _order_pdf_response(order, inline=True):
    company = Company.furniture()
    photos = [
        {'src': image_data_uri(p.image), 'caption': p.caption, 'stage': p.get_stage_display()}
        for p in order.photos.all()
    ]
    context = {
        'order': order,
        'company': order.company_snapshot or company.snapshot(),
        'notes': company.document_notes,
        'logo': image_data_uri(company.logo, max_px=400, quality=90),
        'photo_rows': rows_of([p for p in photos if p['src']]),
        'client_signature': image_data_uri(order.client_signature, max_px=500, quality=90),
        'owner_signature': image_data_uri(order.owner_signature, max_px=500, quality=90),
    }
    try:
        pdf = render_pdf('furniture/pdf/order.html', context)
    except RuntimeError:
        return HttpResponse('No se pudo generar el PDF. Intente de nuevo.', status=500)
    response = HttpResponse(pdf, content_type='application/pdf')
    disposition = 'inline' if inline else 'attachment'
    response['Content-Disposition'] = f'{disposition}; filename="{order.number}.pdf"'
    return response


@furniture_required
def order_pdf(request, pk):
    order = get_object_or_404(Order, pk=pk, is_active=True)
    return _order_pdf_response(order, inline=request.GET.get('descargar') != '1')


def public_order_pdf(request, token):
    """Enlace público (sin login) que se envía al cliente por WhatsApp."""
    order = Order.objects.filter(public_token=token, is_active=True).first()
    if not order:
        raise Http404
    return _order_pdf_response(order)


# =========================================================
# PROFORMAS
# =========================================================
@furniture_required
def quote_list(request):
    status = request.GET.get('estado', '')
    q = request.GET.get('q', '').strip()
    quotes = Quote.objects.filter(is_active=True).select_related('client').prefetch_related('items')
    if status in Quote.Status.values:
        quotes = quotes.filter(status=status)
    if q:
        quotes = quotes.filter(Q(client__name__icontains=q) | Q(client__phone__icontains=q) | Q(notes__icontains=q))
    tabs = [('', 'Todas')] + list(Quote.Status.choices)
    return render(request, 'furniture/quotes.html', {
        'quotes': quotes[:200], 'status': status, 'q': q, 'tabs': tabs, 'nav': 'quotes',
    })


@furniture_required
def quote_create(request):
    if request.method == 'POST':
        try:
            client = client_from_post(request)
            kind = kind_from_post(request)
            items = parse_items(request.POST.get('items'))
            if not items:
                raise InvalidData('Agregue al menos un ítem con descripción y precio.')
            photos = uploaded_photos(request)
            valid_days = int(request.POST.get('valid_days') or 15)
        except InvalidData as exc:
            return json_error(str(exc))
        except ValueError:
            return json_error('Los días de validez deben ser un número.')

        with transaction.atomic():
            quote = Quote.objects.create(
                kind=kind, client=client, created_by=request.user,
                notes=request.POST.get('notes', '').strip(),
                valid_days=max(1, min(valid_days, 365)),
                company_snapshot=Company.furniture().snapshot(),
            )
            QuoteItem.objects.bulk_create([QuoteItem(quote=quote, **item) for item in items])
            for photo, caption in photos:
                QuotePhoto.objects.create(quote=quote, image=photo, caption=caption)

        return JsonResponse({'redirect': reverse('furniture:quote_detail', args=[quote.pk]) + '?nueva=1'}, status=201)

    initial = {'kind': request.GET.get('tipo', '').upper() or Kind.REUPHOLSTERY, 'client': None, 'items': []}
    if request.GET.get('cliente'):
        client = Client.objects.filter(pk=request.GET['cliente'], is_active=True).first()
        initial['client'] = client.to_dict() if client else None
    return render(request, 'furniture/quote_form.html', {'initial': initial, 'nav': 'quotes'})


@furniture_required
def quote_detail(request, pk):
    quote = get_object_or_404(Quote.objects.select_related('client').prefetch_related('items', 'photos', 'orders'), pk=pk, is_active=True)
    pdf_url = request.build_absolute_uri(reverse('furniture:public_quote_pdf', args=[quote.public_token]))
    company = Company.furniture()
    text = '\n'.join([
        f"Hola {quote.client.name.split(' ')[0]} 👋",
        f"Le saluda *{company.name}*. Le enviamos la proforma *{quote.number}*:",
        f"Total: *${quote.total:.2f}* (válida hasta {quote.valid_until:%d/%m/%Y})",
        pdf_url,
    ])
    return render(request, 'furniture/quote_detail.html', {
        'quote': quote,
        'is_new': request.GET.get('nueva') == '1',
        'pdf_public_url': pdf_url,
        'whatsapp_url': whatsapp_link(quote.client.whatsapp_number, text),
        'nav': 'quotes',
    })


@furniture_required
@require_POST
def quote_status(request, pk):
    quote = get_object_or_404(Quote, pk=pk, is_active=True)
    new_status = request.POST.get('status')
    if new_status in Quote.Status.values:
        quote.status = new_status
        quote.save(update_fields=['status', 'updated_at'])
        messages.success(request, f'{quote.number}: {quote.get_status_display()}')
    return redirect('furniture:quote_detail', pk=pk)


@furniture_required
@require_POST
def quote_delete(request, pk):
    quote = get_object_or_404(Quote, pk=pk, is_active=True)
    quote.is_active = False
    quote.save(update_fields=['is_active', 'updated_at'])
    messages.success(request, f'{quote.number} eliminada.')
    return redirect('furniture:quotes')


def _quote_pdf_response(quote):
    company = Company.furniture()
    photos = [{'src': image_data_uri(p.image), 'caption': p.caption} for p in quote.photos.all()]
    context = {
        'quote': quote,
        'company': quote.company_snapshot or company.snapshot(),
        'notes': company.document_notes,
        'logo': image_data_uri(company.logo, max_px=400, quality=90),
        'photo_rows': rows_of([p for p in photos if p['src']]),
    }
    try:
        pdf = render_pdf('furniture/pdf/quote.html', context)
    except RuntimeError:
        return HttpResponse('No se pudo generar el PDF. Intente de nuevo.', status=500)
    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="{quote.number}.pdf"'
    return response


@furniture_required
def quote_pdf(request, pk):
    return _quote_pdf_response(get_object_or_404(Quote, pk=pk, is_active=True))


def public_quote_pdf(request, token):
    quote = Quote.objects.filter(public_token=token, is_active=True).first()
    if not quote:
        raise Http404
    return _quote_pdf_response(quote)

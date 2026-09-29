import base64
import binascii
import io
import json
import logging
from decimal import Decimal, InvalidOperation

from django.core.files.base import ContentFile
from django.template.loader import get_template
from PIL import Image
from xhtml2pdf import pisa

logger = logging.getLogger(__name__)

MAX_ITEMS = 100


class InvalidData(Exception):
    """Error de validación con un mensaje listo para mostrar al usuario."""


def _decimal(value, field):
    try:
        number = Decimal(str(value).replace(',', '.').strip() or '0')
    except (InvalidOperation, ValueError):
        raise InvalidData(f'El valor "{value}" en {field} no es un número válido.')
    if number < 0:
        raise InvalidData(f'{field} no puede ser negativo.')
    return number.quantize(Decimal('0.01'))


def parse_items(raw):
    """
    Recibe el JSON de ítems enviado por el formulario:
    [{"quantity": "2", "description": "Cojín", "unit_price": "15.50"}, ...]
    y devuelve una lista validada. Las filas vacías se ignoran.
    """
    try:
        rows = json.loads(raw or '[]')
    except json.JSONDecodeError:
        raise InvalidData('No se pudieron leer los ítems. Intente de nuevo.')
    if not isinstance(rows, list):
        raise InvalidData('Formato de ítems inválido.')

    items = []
    for row in rows[:MAX_ITEMS]:
        if not isinstance(row, dict):
            continue
        description = str(row.get('description', '')).strip()[:255]
        if not description:
            continue
        quantity = _decimal(row.get('quantity', 1), 'Cantidad')
        if quantity == 0:
            raise InvalidData(f'La cantidad de "{description}" debe ser mayor a cero.')
        items.append({
            'description': description,
            'quantity': quantity,
            'unit_price': _decimal(row.get('unit_price', 0), 'Valor unitario'),
        })
    return items


def parse_money(value, field='Abono'):
    return _decimal(value or 0, field)


def signature_file(data_url, name):
    """Convierte la firma del canvas (data:image/png;base64,...) en un archivo PNG."""
    if not data_url or not data_url.startswith('data:image'):
        return None
    try:
        raw = base64.b64decode(data_url.split(',', 1)[1])
        with Image.open(io.BytesIO(raw)) as img:
            img = img.convert('RGBA')
            # Fondo blanco: los PDF no manejan bien la transparencia
            background = Image.new('RGB', img.size, (255, 255, 255))
            background.paste(img, mask=img.split()[3])
            out = io.BytesIO()
            background.save(out, format='PNG', optimize=True)
    except (binascii.Error, IndexError, OSError, ValueError):
        raise InvalidData('La firma no es válida. Bórrela y firme de nuevo.')
    return ContentFile(out.getvalue(), name=name)


def image_data_uri(field_file, max_px=700, quality=72):
    """
    Lee una imagen (local o Cloudinary), la reduce y la devuelve en base64.
    Así el PDF pesa poco y no depende de descargar URLs externas al renderizar.
    """
    if not field_file:
        return None
    try:
        field_file.open('rb')
        data = field_file.read()
        field_file.close()
        with Image.open(io.BytesIO(data)) as img:
            if img.mode in ('RGBA', 'LA', 'P'):
                img = img.convert('RGBA')
                background = Image.new('RGB', img.size, (255, 255, 255))
                background.paste(img, mask=img.split()[3])
                img = background
            else:
                img = img.convert('RGB')
            img.thumbnail((max_px, max_px))
            out = io.BytesIO()
            img.save(out, format='JPEG', quality=quality, optimize=True)
        return 'data:image/jpeg;base64,' + base64.b64encode(out.getvalue()).decode()
    except Exception as exc:  # una foto dañada no debe impedir generar el PDF
        logger.warning('No se pudo procesar la imagen %s: %s', getattr(field_file, 'name', ''), exc)
        return None


def render_pdf(template_name, context):
    html = get_template(template_name).render(context)
    buffer = io.BytesIO()
    result = pisa.CreatePDF(html, dest=buffer, encoding='utf-8')
    if result.err:
        raise RuntimeError('No se pudo generar el PDF.')
    return buffer.getvalue()

from django.template.loader import get_template
from xhtml2pdf import pisa
from io import BytesIO

def generate_invoice_pdf(sale, request=None):
    """
    Genera un PDF de la factura utilizando xhtml2pdf.
    Retorna los bytes del documento generado.
    """
    template = get_template('sales/invoice_pdf.html')
    context = {
        'sale': sale,
        'customer': sale.customer,
        'details': sale.details.all(),
        'company': {
            'name': 'Bedoya Motors',
            'address': 'Av. Principal y Calle Secundaria',
            'city': 'Sangolquí, Ecuador',
            'phone': '+593 99 999 9999',
            'email': 'facturacion@bedoyamotors.com',
            'ruc': '1799999999001'
        }
    }
    
    # Renderizar el HTML
    html = template.render(context)
    
    # Crear un buffer de memoria para el PDF
    result = BytesIO()
    
    # Convertir HTML a PDF
    pdf = pisa.pisaDocument(BytesIO(html.encode("UTF-8")), result)
    
    if not pdf.err:
        return result.getvalue()
        
    return None
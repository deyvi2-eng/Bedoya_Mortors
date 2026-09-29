from companies.models import Company


def furniture_company(request):
    """Datos de Muebles M&L disponibles en todas las pantallas de /muebles/."""
    if request.path.startswith('/muebles/'):
        return {'furniture_company': Company.furniture()}
    return {}

from django.core.paginator import Paginator


def paginate(request, queryset, per_page=20, page_param='page'):
    """Pagina un queryset/lista y devuelve el contexto que usa templates/includes/pagination.html.

    Uso en la plantilla: {% include 'includes/pagination.html' with page_obj=... %}
    (con page_param='...' si la página tiene más de una lista paginada).
    """
    page_obj = Paginator(queryset, per_page).get_page(request.GET.get(page_param))
    page_obj.elided_range = list(page_obj.paginator.get_elided_page_range(page_obj.number, on_each_side=1, on_ends=1))
    page_obj.page_param = page_param
    return page_obj

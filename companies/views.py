from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import get_object_or_404, redirect, render

from .forms import CompanyForm
from .models import Company


def is_admin(user):
    return user.is_authenticated and (user.is_superuser or getattr(user, 'role', '') == 'ADMIN')


@login_required
@user_passes_test(is_admin)
def company_list(request):
    Company.furniture()  # garantiza que Muebles M&L exista
    return render(request, 'companies/list.html', {'companies': Company.objects.all()})


@login_required
@user_passes_test(is_admin)
def company_edit(request, slug):
    company = get_object_or_404(Company, slug=slug)
    form = CompanyForm(request.POST or None, request.FILES or None, instance=company)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, f'Datos de {company.name} guardados.')
        return redirect('companies:list')
    return render(request, 'companies/edit.html', {'company': company, 'form': form})

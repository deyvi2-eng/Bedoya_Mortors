from django import forms
from .models import Company

INPUT = 'w-full bg-gray-50 border border-gray-200 rounded-2xl px-4 py-3 text-base outline-none focus:ring-2 focus:ring-gray-900'


class CompanyForm(forms.ModelForm):
    class Meta:
        model = Company
        fields = ['name', 'legal_name', 'ruc', 'address', 'email', 'phone', 'logo', 'document_notes']
        widgets = {
            'name': forms.TextInput(attrs={'class': INPUT}),
            'legal_name': forms.TextInput(attrs={'class': INPUT}),
            'ruc': forms.TextInput(attrs={'class': INPUT, 'inputmode': 'numeric', 'maxlength': 13}),
            'address': forms.TextInput(attrs={'class': INPUT}),
            'email': forms.EmailInput(attrs={'class': INPUT}),
            'phone': forms.TextInput(attrs={'class': INPUT, 'inputmode': 'tel'}),
            'logo': forms.FileInput(attrs={'accept': 'image/*', 'class': 'hidden', 'id': 'logo-input'}),
            'document_notes': forms.Textarea(attrs={'class': INPUT, 'rows': 4}),
        }

    def clean_ruc(self):
        ruc = (self.cleaned_data.get('ruc') or '').strip()
        if ruc and (not ruc.isdigit() or len(ruc) != 13):
            raise forms.ValidationError('El RUC debe tener 13 dígitos.')
        return ruc

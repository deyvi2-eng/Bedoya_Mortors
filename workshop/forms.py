from django import forms
from .models import ServiceOrder
from customers.models import Customer

class ServiceOrderForm(forms.ModelForm):
    # Buscador de clientes inteligente (Select2)
    customer = forms.ModelChoiceField(
        queryset=Customer.objects.all(),
        empty_label="--- Buscar o Seleccionar Cliente ---",
        widget=forms.Select(attrs={
            'class': 'form-select select2-search',
            'id': 'customer_select'
        }),
        label="Propietario / Cliente"
    )

    class Meta:
        model = ServiceOrder
        fields = [
            'customer', 'license_plate', 'brand', 'model', 'color', 
            'mileage', 'serial_number', 'arrived_by_crane',
            'work_to_do', 'observations', 'customer_observation', 'fuel_level', 'deposit_amount'
        ]
        widgets = {
            # Datos Técnicos
            'license_plate': forms.TextInput(attrs={'class': 'form-control uppercase', 'placeholder': 'Ej: AB123C', 'style': 'text-transform: uppercase;'}),
            'brand': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: Yamaha'}),
            'model': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: MT-09'}),
            'color': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Color'}),
            'mileage': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Ej: 15000'}),
            'serial_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'N° Chasis / Motor (Opcional)'}),
            
            # Checkbox de Grúa
            'arrived_by_crane': forms.CheckboxInput(attrs={'class': 'custom-checkbox border-orange-300'}),
            
            # Textos y Observaciones
            'work_to_do': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Especifique el trabajo exacto a realizar...'}),
            'observations': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Observaciones técnicas, rayones, faltantes...'}),
            'customer_observation': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Lo que el cliente nos indica adicionalmente...'}),
            
            # Finanzas y Combustible
            'fuel_level': forms.Select(attrs={'class': 'form-select'}),
            'deposit_amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
        }
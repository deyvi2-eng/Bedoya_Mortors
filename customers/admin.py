from django.contrib import admin
from .models import Customer

@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ('cedula', 'first_name', 'last_name', 'phone', 'city', 'is_active')
    search_fields = ('cedula', 'first_name', 'last_name', 'email')
    list_filter = ('city', 'is_active')
    
    fieldsets = (
        ('Información Personal', {
            'fields': ('cedula', 'first_name', 'last_name')
        }),
        ('Contacto', {
            'fields': ('phone', 'whatsapp', 'email')
        }),
        ('Ubicación y Notas', {
            'fields': ('address', 'city', 'observations', 'is_active')
        }),
    )
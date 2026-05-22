from django.contrib import admin
from .models import Category, Supplier, Product

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'prefix', 'is_active', 'created_at')
    search_fields = ('name', 'prefix')
    list_filter = ('is_active',)

@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ('name', 'contact_phone', 'email', 'is_active')
    search_fields = ('name', 'email')

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    # Columnas visibles en la tabla principal
    list_display = ('code', 'name', 'category', 'stock_actual', 'purchase_price', 'sale_price', 'profit_margin_display', 'is_active')
    search_fields = ('code', 'name', 'barcode', 'brand')
    list_filter = ('category', 'is_active', 'brand')
    
    # El código se bloquea en la interfaz para que el sistema lo genere automáticamente
    readonly_fields = ('code', 'created_at', 'updated_at')
    
    # Organización visual del formulario tipo ERP corporativo
    fieldsets = (
        ('Identificadores', {
            'fields': ('code', 'barcode', 'category')
        }),
        ('Información General', {
            'fields': ('name', 'description', 'brand', 'model_compatibility')
        }),
        ('Precios', {
            'fields': ('purchase_price', 'sale_price')
        }),
        ('Inventario', {
            'fields': ('stock_actual', 'stock_minimo', 'stock_critico', 'location', 'unit_measure')
        }),
        ('Relaciones y Multimedia', {
            'fields': ('supplier', 'image', 'is_active')
        }),
    )

    def profit_margin_display(self, obj):
        return f"{obj.profit_margin}%"
    profit_margin_display.short_description = "Margen de Ganancia"
from django.contrib import admin
from .models import Category, Supplier, Product, StockMovement

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'prefix', 'is_active', 'created_at')
    search_fields = ('name', 'prefix')
    list_filter = ('is_active',)
    ordering = ('name',)

@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ('name', 'contact_phone', 'email', 'is_active', 'created_at')
    search_fields = ('name', 'contact_phone', 'email')
    list_filter = ('is_active',)

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'category', 'stock_actual', 'sale_price', 'is_active')
    search_fields = ('code', 'name', 'barcode', 'brand')
    list_filter = ('category', 'is_active', 'supplier')
    ordering = ('-created_at',)
    readonly_fields = ('code',) # Protege el código generado automáticamente

@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = ('product', 'movement_type', 'quantity', 'user', 'created_at')
    list_filter = ('movement_type', 'created_at')
    search_fields = ('product__name', 'product__code', 'description')
    readonly_fields = ('product', 'movement_type', 'quantity', 'user', 'description') # Evita alteraciones manuales en auditoría
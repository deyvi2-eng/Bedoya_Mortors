from django.contrib import admin
from .models import ServiceOrder, ServiceMedia, ServiceItem

class ServiceMediaInline(admin.TabularInline):
    model = ServiceMedia
    extra = 0

class ServiceItemInline(admin.TabularInline):
    model = ServiceItem
    extra = 0

@admin.register(ServiceOrder)
class ServiceOrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'license_plate', 'customer', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('license_plate', 'customer__first_name', 'customer__cedula')
    inlines = [ServiceMediaInline, ServiceItemInline]
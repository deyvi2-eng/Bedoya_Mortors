from django.contrib import admin
from .models import Client, Order, OrderItem, OrderPhoto, Quote, QuoteItem, QuotePhoto


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0


class OrderPhotoInline(admin.TabularInline):
    model = OrderPhoto
    extra = 0


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('number', 'client', 'kind', 'status', 'created_at')
    list_filter = ('kind', 'status')
    inlines = [OrderItemInline, OrderPhotoInline]


class QuoteItemInline(admin.TabularInline):
    model = QuoteItem
    extra = 0


class QuotePhotoInline(admin.TabularInline):
    model = QuotePhoto
    extra = 0


@admin.register(Quote)
class QuoteAdmin(admin.ModelAdmin):
    list_display = ('number', 'client', 'status', 'created_at')
    inlines = [QuoteItemInline, QuotePhotoInline]


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ('name', 'phone', 'id_number')
    search_fields = ('name', 'phone', 'id_number')

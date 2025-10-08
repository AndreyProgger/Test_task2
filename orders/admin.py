from django.contrib import admin
from unfold.admin import ModelAdmin

from .models import Order, OrderItem


@admin.register(Order)
class OrderAdmin(ModelAdmin):
    list_display = ['user', 'get_products', 'status', 'created_at', 'total_price']
    list_filter = ['status']
    search_fields = ['user']
    date_hierarchy = 'created_at'

    def get_products(self, instance):
        return [product for product in instance.products.all()]


@admin.register(OrderItem)
class OrderAdmin(ModelAdmin):
    list_display = ['order', 'product', 'quantity', 'price']
    list_filter = ['quantity', 'price']
    search_fields = ['order', 'product']


from django.contrib import admin
from .models import Product


'''@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['username', 'first_name', 'last_name', 'email', 'is_staff', 'is_active', 'patronymic']
    list_filter = ['status', 'created', 'publish', 'author']
    search_fields = ['username', 'email', 'first_name', 'last_name']
    date_hierarchy = 'date_joined'
    ordering = ['username']'''

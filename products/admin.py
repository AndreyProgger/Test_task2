from django.contrib import admin
from django.db import models
from unfold.admin import ModelAdmin
from unfold.contrib.forms.widgets import WysiwygWidget

from .models import Product


@admin.register(Product)
class ProductAdmin(ModelAdmin):
    list_display = ['name', 'description', 'price', 'stock', 'category', 'created_at', 'updated_at']
    list_filter = ['price', 'category']
    search_fields = ['name', 'description', 'category']
    date_hierarchy = 'created_at'
    ordering = ['created_at']

    formfield_overrides = {
        models.TextField: {
            "widget": WysiwygWidget,
        }
    }

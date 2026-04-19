from django.contrib import admin
from django.db import models
from unfold.admin import ModelAdmin
from unfold.contrib.forms.widgets import WysiwygWidget

from .models import Address


@admin.register(Address)
class AddressAdmin(ModelAdmin):
    list_display = ['user', 'city', 'house', 'apartment', 'postal_code', 'created_at', 'is_default']
    list_filter = ['user', 'city']
    search_fields = ['user', 'city']
    date_hierarchy = 'created_at'
    ordering = ['created_at']

    formfield_overrides = {
        models.TextField: {
            "widget": WysiwygWidget,
        }
    }
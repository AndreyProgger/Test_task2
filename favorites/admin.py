from django.contrib import admin
from django.db import models
from unfold.admin import ModelAdmin
from unfold.contrib.forms.widgets import WysiwygWidget

from .models import FavoriteItem


@admin.register(FavoriteItem)
class FavoriteItemAdmin(ModelAdmin):
    list_display = ['favorite', 'product', 'exist']
    search_fields = ['product']

    formfield_overrides = {
        models.TextField: {
            "widget": WysiwygWidget,
        }
    }

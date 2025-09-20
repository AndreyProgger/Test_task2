from django.contrib import admin
from .models import User


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ['username', 'first_name', 'last_name', 'email', 'is_staff', 'is_active', 'patronymic']
    list_filter = ['is_staff', 'is_active']
    search_fields = ['username', 'email', 'first_name', 'last_name']
    date_hierarchy = 'date_joined'
    ordering = ['username']

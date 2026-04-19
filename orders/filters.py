import django_filters
from django_filters import DateFromToRangeFilter
from .models import Order


class OrderFilter(django_filters.FilterSet):
    # Фильтрация по статусу
    status = django_filters.CharFilter(field_name='status', lookup_expr='iexact', required=False)

    # Фильтрация по диапазону дат (created_at)
    created_at = DateFromToRangeFilter(field_name='created_at', required=False)

    # Сортировка по дате создания
    ordering = django_filters.OrderingFilter(
        fields=(
            ('created_at', 'created_at'),
        ),
        field_labels={
            'created_at': 'Дата создания',
        }
    )

    class Meta:
        model = Order
        fields = ['status']

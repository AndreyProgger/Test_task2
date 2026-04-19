import django_filters
from django.db.models import Avg, Q
from .models import Product


class ProductFilter(django_filters.FilterSet):
    # Фильтры
    category = django_filters.CharFilter(field_name='category__slug', lookup_expr='iexact')
    seller = django_filters.NumberFilter(field_name='seller__id')
    is_active = django_filters.BooleanFilter(field_name='is_active')
    in_stock = django_filters.BooleanFilter(method='filter_in_stock')
    min_price = django_filters.NumberFilter(field_name='price', lookup_expr='gte')
    max_price = django_filters.NumberFilter(field_name='price', lookup_expr='lte')
    search = django_filters.CharFilter(method='filter_search')

    # Сортировка
    ordering = django_filters.OrderingFilter(
        fields=(
            ('price', 'price'),
            ('created_at', 'created_at'),
            ('avg_rating', 'rating'),
        ),
        field_labels={
            'price': 'Цена',
            'created_at': 'Дата создания',
            'avg_rating': 'Рейтинг',
        }
    )

    class Meta:
        model = Product
        fields = []  # поля определяем явно выше

    def filter_in_stock(self, queryset, name, value):
        if value:
            return queryset.filter(stock__gt=0)
        return queryset

    def filter_search(self, queryset, name, value):
        return queryset.filter(Q(name__icontains=value) | Q(description__icontains=value))

    def filter_queryset(self, queryset):
        # Добавляем аннотацию среднего рейтинга для сортировки
        queryset = queryset.annotate(avg_rating=Avg('reviews__rating'))
        return super().filter_queryset(queryset)
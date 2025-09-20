import django_filters

from .models import Product


class ProductFilter(django_filters.FilterSet):
    """ Поля для фильтрации """

    max_price = django_filters.NumberFilter(field_name='price', lookup_expr='lte')
    min_price = django_filters.NumberFilter(field_name='price', lookup_expr='gte')
    category = django_filters.CharFilter(field_name='category', lookup_expr='iexact')

    class Meta:
        model = Product
        fields = ['max_price', 'min_price', 'category']
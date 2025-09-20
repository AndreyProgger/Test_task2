import django_filters

from orders.models import Order


class OrderFilter(django_filters.FilterSet):
    """ Фильтры для вывода списка заказов в админском эндпоинте """
    status = django_filters.ChoiceFilter(field_name='status', choices=Order.STATUS_CHOICES, lookup_expr='exact')
    user = django_filters.CharFilter(field_name='user__username', lookup_expr='iexact')

    class Meta:
        model = Order
        fields = ['status', 'user']
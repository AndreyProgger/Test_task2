import logging

from django.core.cache import cache
from django.http import Http404

from .models import Order

cache_logger = logging.getLogger('hit/miss_cache logger')


def get_order(pk: int) -> Order:
    """ Вспомогательная функция для получения объекта по pk """
    try:
        cache_key = f'cached_order_{pk}'
        order = cache.get(cache_key)
        if order is not None:
            cache_logger.info(f'Get order № {order.pk} from cache (cache_hit)')
            return order
        order_cached = Order.objects.prefetch_related('items__product').get(pk=pk)
        cache.set(cache_key, order_cached, 60)
        cache_logger.info(f'Get order № {order_cached.pk} from bd (cache_miss)')
        return order_cached
    except Order.DoesNotExist:
        raise Http404

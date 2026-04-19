import logging

from django.core.cache import cache
from django.http import Http404

from .models import Product, Category

cache_logger = logging.getLogger('hit/miss_cache logger')


def get_product(pk: int) -> Product:
    """ Вспомогательная функция для получения объекта по pk """
    # Сначала ищем объект в кэшированном списке
    products = cache.get('cached_product_list')
    if products:
        # Ищем продукт в кэшированном словаре
        for product in products:
            if product.pk == pk:
                cache_logger.info(f'Get product {product.pk} from cache (cache_hit)')
                return product
    try:
        cache_logger.info('Get product from bd (cache_miss)')
        return Product.objects.prefetch_related('images', 'price_history').get(pk=pk)
    except Product.DoesNotExist:
        raise Http404


def get_category(pk: int) -> Category:
    """ Вспомогательная функция для получения объекта по pk """
    # Сначала ищем объект в кэшированном списке
    categories = cache.get('cached_category_list')
    if categories:
        for category in categories:
            if category.pk == pk:
                cache_logger.info(f'Get category {category.pk} from cache (cache_hit)')
                return category
    try:
        cache_logger.info('Get category from bd (cache_miss)')
        return Category.objects.get(pk=pk)
    except Category.DoesNotExist:
        raise Http404

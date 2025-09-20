from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.core.cache import cache

from .models import Product


@receiver(post_save, sender=Product)
def clear_product_cache_post_save(sender, instance, **kwargs):
    """ Сигнал для очистки кэша после создание или обновления продукта """
    cache.delete('cached_product_list')


@receiver(post_delete, sender=Product)
def clear_product_cache_post_delete(sender, instance, **kwargs):
    """ Сигнал для очистки кэша после удаления продукта """
    cache.delete('cached_product_list')

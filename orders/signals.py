from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.core.cache import cache

from .models import Order
from .tasks import send_order_email


@receiver(post_save, sender=Order)
def clear_order_cache_order_save(sender, instance, **kwargs):
    """ Сигнал для очистки кэша заказа после создания или обновления """
    cache_key = f'cached_order_{instance.pk}'
    cache.delete(cache_key)


@receiver(post_delete, sender=Order)
def clear_order_cache_order_delete(sender, instance, **kwargs):
    """ Сигнал для очистки кэша заказа после удаления """
    cache_key = f'cached_order_{instance.pk}'
    cache.delete(cache_key)


@receiver(post_save, sender=Order)
def send_detail_to_email(sender, instance, created, **kwargs):
    """ Сигнал для запуска задачи по генерации и отправлению PDF отчета """
    if created:
        send_order_email.delay(instance.id)

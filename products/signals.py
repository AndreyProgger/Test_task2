from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver
from django.core.cache import cache

from .models import Product, Category, PriceHistory


@receiver(post_save, sender=Product)
def clear_product_cache_post_save(sender, instance, **kwargs):
    """ Сигнал для очистки кэша после создание или обновления продукта """
    cache.delete('cached_product_list')


@receiver(post_delete, sender=Product)
def clear_product_cache_post_delete(sender, instance, **kwargs):
    """ Сигнал для очистки кэша после удаления продукта """
    cache.delete('cached_product_list')


@receiver(post_save, sender=Category)
def clear_category_cache_post_save(sender, instance, **kwargs):
    """ Сигнал для очистки кэша после создание или обновления категории """
    cache.delete('cached_category_list')


@receiver(post_delete, sender=Category)
def clear_category_cache_post_delete(sender, instance, **kwargs):
    """ Сигнал для очистки кэша после удаления категории """
    cache.delete('cached_category_list')


@receiver(post_save, sender=Product)
def create_initial_price_history(sender, instance, created, **kwargs):
    """
    Создаёт первую запись в истории цен при создании нового товара
    """
    if created:
        # Создаем запись в истории с начальной ценой
        PriceHistory.objects.create(
            product=instance,
            price=instance.price,
        )


@receiver(pre_save, sender=Product)
def capture_old_product_values(sender, instance, **kwargs):
    """Сохраняет старые значения цен перед обновлением"""
    if instance.pk:  # Только для существующих товаров
        try:
            old_instance = Product.objects.get(pk=instance.pk)
            # Сохраняем старые значения в атрибуты instance
            instance._old_price = old_instance.price
            instance._old_discount_price = old_instance.discount_price
        except Product.DoesNotExist:
            instance._old_price = None
            instance._old_discount_price = None


@receiver(post_save, sender=Product)
def log_price_change(sender, instance, created, **kwargs):
    """Создаёт записи в истории цен при изменении цен товара"""
    if not created:
        # Получаем старые значения, сохраненные в pre_save
        old_price = getattr(instance, '_old_price', None)
        old_discount_price = getattr(instance, '_old_discount_price', None)

        if old_price is not None:
            # Проверяем изменения обычной цены
            if old_price != instance.price:
                PriceHistory.objects.create(
                    product=instance,
                    price=instance.price
                )

            # Проверяем изменения скидочной цены
            if old_discount_price != instance.discount_price:
                if instance.discount_price is None:
                    PriceHistory.objects.create(
                        product=instance,
                        price=instance.price
                    )
                else:
                    PriceHistory.objects.create(
                        product=instance,
                        price=instance.discount_price
                    )
    else:
        # Для нового товара создаём запись с актуальной ценой
        price_to_save = instance.discount_price if instance.discount_price else instance.price
        PriceHistory.objects.create(product=instance, price=price_to_save)

    # Очищаем временные атрибуты
    if hasattr(instance, '_old_price'):
        delattr(instance, '_old_price')
    if hasattr(instance, '_old_discount_price'):
        delattr(instance, '_old_discount_price')
from django.core.exceptions import ValidationError
from django.db import models
from django.conf import settings

from products.models import Product


class Favorite(models.Model):
    """
    Представляет модель списка избранных товаров пользователя

    Атрибуты:
        user (OneToOneField): Пользователь кому принадлежит список избранных
        favorites (ManyToManyField): Избранные товары

    """
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    favorites = models.ManyToManyField(Product, through='FavoriteItem', through_fields=('favorite', 'product'),
                                       related_name='favorited_by')

    @property
    def owner(self):
        return self.user


class FavoriteItem(models.Model):
    """
    Представляет промежуточную модель для связи продуктов с конкретным заказом

    Атрибуты:
        favorite (ForeignKey): Конкретный список избранных товаров
        product (ForeignKey): Товар
        exist (BooleanField): Флаг показывающий есть ли конкретный товар уже в избранном

    """

    favorite = models.ForeignKey(Favorite, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='favorite_items')
    exist = models.BooleanField(default=False)

    class Meta:
        unique_together = ('favorite', 'product')
        verbose_name = 'Детали списка избранных'
        verbose_name_plural = 'Детали списков избранных'

    def clean(self):
        """
        Валидация на уровне модели:
        - Нельзя добавить свой товар в избранное
        - Нельзя добавить неактивный товар
        - Нельзя добавить удаленный товар
        """
        super().clean()

        # Проверка что пользователь не добавляет свой товар
        if self.product.seller == self.favorite.user:
            raise ValidationError({
                'product': 'Нельзя добавить свой товар в избранное'
            })

        # Проверка что товар активен
        if hasattr(self.product, 'is_active') and not self.product.is_active:
            raise ValidationError({
                'product': 'Нельзя добавить неактивный товар в избранное'
            })

        # Проверка что товар не удален (soft delete)
        if hasattr(self.product, 'is_deleted') and self.product.is_deleted:
            raise ValidationError({
                'product': 'Нельзя добавить удаленный товар в избранное'
            })

    def save(self, *args, **kwargs):
        """
        Вызываем валидацию перед сохранением.
        Если запись существует, но exist=False, обновляем на True.
        """
        self.full_clean()

        # Если запись существует с exist=False, обновляем её
        if not self.pk and self._meta.model.objects.filter(
                favorite=self.favorite,
                product=self.product
        ).exists():
            existing = self._meta.model.objects.get(
                favorite=self.favorite,
                product=self.product
            )
            if not existing.exist:
                existing.exist = True
                existing.save()
            return

        super().save(*args, **kwargs)
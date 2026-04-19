from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError

from orders.models import Order
from products.models import Product


class Review(models.Model):
    """
        Представляет модель отзыва

        Атрибуты:
            product (ForeignKey): Оцениваемый товар
            user (ForeignKey): Автор отзыва
            rating (int): Общая оценка товара
            text (str): Текст отзыва
            created_at (DateTimeField): Дата создания отзыва
            is_published (bool): Флаг проверяющий опубликован ли отзыв

        """

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='reviews',
        verbose_name='Товар'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='reviews',
        verbose_name='Пользователь'
    )
    rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        verbose_name='Рейтинг'
    )
    text = models.TextField(verbose_name='Текст отзыва')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    is_published = models.BooleanField(default=True, verbose_name='Опубликован')

    class Meta:
        unique_together = ('product', 'user')
        verbose_name = 'Отзыв'
        verbose_name_plural = 'Отзывы'
        ordering = ['-created_at']

    def __str__(self):
        return f'Отзыв от {self.user} на {self.product} (оценка {self.rating})'

    # Добавляем валидацию на уровне БД чтобы исключить недопустимые данные при прямом добавлении в бд
    def clean(self):
        if not self.product_id:
            raise ValidationError('Product is required')

        # Загружаем продукт из БД
        try:
            product_obj = Product.objects.get(pk=self.product_id)
        except Product.DoesNotExist:
            raise ValidationError('Product does not exist')

        # Проверка на свой товар
        if product_obj.seller == self.user:
            raise ValidationError('Нельзя оставить отзыв на свой товар')

        # Проверка наличия завершённого заказа
        if not Order.objects.filter(
                user=self.user,
                status='completed',
                items__product=product_obj
        ).exists():
            raise ValidationError('Нельзя оставить отзыв на товар, так как нет завершенных заказов с этим товаром.')

    def _has_completed_order(self):
        """Проверяет, есть ли у пользователя завершённый заказ с этим товаром"""
        return Order.objects.filter(
            items__product=self.product,
            user=self.user,
            status='completed'
        ).exists()

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    @property
    def owner(self):
        return self.user

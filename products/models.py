from decimal import Decimal
from django.db import models
from django.core.validators import MinValueValidator


class Product(models.Model):
    """
    Представляет объект товара в магазине

    Атрибуты:
        name (str): Имя товара
        description (str): Описание товара
        price (DecimalField): Цена товара
        stock (PositiveInteger): Количество товара на складе
        category (str): Категория товара
        created_at (DateTimeField): Время создания товара
        updated_at (DateTimeField): Время последнего обновления товара
    """

    CATEGORY_CHOICES = [
        ('electronics', 'Электроника'),
        ('clothing', 'Одежда'),
        ('books', 'Книги'),
        ('home', 'Дом и сад'),
        ('sport', 'Спорт')
    ]

    name = models.CharField(
        max_length=255,
        verbose_name='Название продукта'
    )

    description = models.TextField(
        verbose_name='Описание продукта',
        blank=True,
        null=True
    )

    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        verbose_name='Цена'
    )

    stock = models.PositiveIntegerField(
        default=0,
        verbose_name='Количество на складе'
    )

    category = models.CharField(
        max_length=20,
        choices=CATEGORY_CHOICES,
        verbose_name='Категория'
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата создания'
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Дата обновления'
    )

    class Meta:
        verbose_name = 'Продукт'
        verbose_name_plural = 'Продукты'
        ordering = ['-created_at']  # Сортируем по дате создания в обратном порядке
        # Здесь мы можем позволить использовать индекс, так как запрос
        # к продуктам при создании заказов ожидается в разы чаще, чем изменения в списке продуктов
        indexes = [
            models.Index(fields=['price']),
        ]

    def __str__(self) -> str:
        return f"Название: {self.name}, Количество: {self.stock}, Цена: {self.price}."

    def is_in_stock(self):
        """Проверяет, есть ли товар в наличии"""
        return self.stock > 0
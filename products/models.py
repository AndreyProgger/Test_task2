from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models
from django.core.validators import MinValueValidator
from django.conf import settings
from django.utils.text import slugify


class ProductManager(models.Manager):
    """Менеджер модели Product с фильтрацией активных товаров"""

    def get_queryset(self):
        """По умолчанию возвращает только активные и неудалённые товары"""
        return super().get_queryset().filter(is_active=True, is_deleted=False)


class Category(models.Model):
    name = models.CharField(max_length=200, verbose_name='Название')
    slug = models.SlugField(max_length=200, unique=True, verbose_name='Slug')
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='children',
        verbose_name='Родительская категория',
        default=None,
    )
    is_active = models.BooleanField(default=True, verbose_name='Активна')

    class Meta:
        verbose_name = 'Категория'
        verbose_name_plural = 'Категории'
        ordering = ['name']
        indexes = [
            models.Index(fields=['name']),
        ]

    def __str__(self):
        if self.parent:
            return f'{self.parent.name} → {self.name}'
        return self.name

    def clean(self):
        # Запрещаем вложенность более 1 уровня (parent не может иметь parent)
        if self.parent and self.parent.parent:
            raise ValidationError('Поддержка вложенности только на один уровень (нельзя создавать подкатегорию'
                                  ' у подкатегории).')

    def save(self, *args, **kwargs):
        # Автоматически генерируем slug, если не задан
        if not self.slug:
            base_slug = slugify(self.name)
            slug = base_slug
            counter = 1
            while Category.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        self.full_clean()  # вызовет clean() и валидацию полей
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        # Запрещаем удаление категории, если к ней привязаны товары
        if self.products.exists():
            raise ValidationError(f'Невозможно удалить категорию "{self.name}", так как к ней привязаны товары.')
        super().delete(*args, **kwargs)


class ProductImage(models.Model):
    product = models.ForeignKey(
        'Product',
        on_delete=models.CASCADE,
        related_name='images',
        verbose_name='Товар'
    )
    image_url = models.URLField(
        max_length=500,
        verbose_name='URL изображения'
    )
    sort_order = models.PositiveSmallIntegerField(
        verbose_name='Порядок сортировки',
        help_text='Чем меньше число, тем выше изображение'
    )

    class Meta:
        verbose_name = 'Изображение товара'
        verbose_name_plural = 'Изображения товаров'
        # Ограничение: sort_order уникален в рамках одного товара
        constraints = [
            models.UniqueConstraint(
                fields=['product', 'sort_order'],
                name='unique_sort_order_per_product'
            )
        ]
        # Сортировка по умолчанию – по возрастанию sort_order
        ordering = ['sort_order']
        indexes = [
            models.Index(fields=['sort_order']),
        ]

    def __str__(self):
        return f"Изображение для {self.product} (порядок {self.sort_order})"

    def clean(self):
        # Проверка: не более 8 изображений на товар
        if not self.pk:  # только для новых записей
            current_count = ProductImage.objects.filter(product=self.product).count()
            if current_count >= 8:
                raise ValidationError('У товара не может быть более 8 изображений.')
        super().clean()

    def save(self, *args, **kwargs):
        self.full_clean()  # вызовет clean() и валидацию полей
        super().save(*args, **kwargs)


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

    # Стандартный менеджер всех товаров для админа
    objects = models.Manager()

    # Кастомный менеджер для активных товаров для покупателей
    available = ProductManager()

    name = models.CharField(
        max_length=255,
        verbose_name='Название продукта'
    )
    seller = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='owner',
        verbose_name='Продавец'
    )

    slug = models.SlugField(
        max_length=255,
        unique=True,
        blank=True,
        db_index=True,
        verbose_name='Slug'
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

    discount_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        verbose_name='Цена',
        null=True,
        blank=True
    )

    stock = models.PositiveIntegerField(
        default=0,
        verbose_name='Количество на складе'
    )

    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name='products',
        verbose_name='Категория',
        null=True,
        blank=True
    )

    is_deleted = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

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
        return f"Название: {self.name}, Количество: {self.stock}, Цена: {self.price}, Продавец: {self.seller}."

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name)
            slug = base_slug
            counter = 1
            # Гарантируем уникальность
            while Product.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        self.full_clean()  # вызывает clean() и валидацию полей
        super().save(*args, **kwargs)

    def is_in_stock(self):
        """Проверяет, есть ли товар в наличии"""
        return self.stock > 0

    @property
    def owner(self):
        return self.seller


class PriceHistory(models.Model):
    """
    Представляет объект измененной цены товара

    Атрибуты:
        name (str): Имя товара
        price (DecimalField): Цена товара
        updated_at (DateTimeField): Время последнего обновления товара
    """

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='price_history',
        verbose_name='Товар'
    )
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        verbose_name='Цена'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата создания записи'
    )

    class Meta:
        verbose_name = 'История цены'
        verbose_name_plural = 'Истории цен'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['product', '-created_at']),
        ]

    def __str__(self) -> str:
        return f"Товар: {self.product.name}, цена: {self.price}, дата: {self.created_at.strftime('%d.%m.%Y %H:%M')}"


from django.db.models import F, Sum
from decimal import Decimal
from django.utils import timezone
from django.db import models
from django.conf import settings

from products.models import Product


class Order(models.Model):
    """
    Представляет объект заказа

    Атрибуты:
        user (ForeignKey): Пользователь создавший заказ
        products (ManyToManyField): Список всех продуктов из заказа
        status (str): Статус заказа
        created_at (DateTimeField): Время создания заказа
    """

    STATUS_CHOICES = [
        ('pending', 'Ожидает обработки'),
        ('processing', 'В обработке'),
        ('shipped', 'Отправлен'),
        ('delivered', 'Доставлен'),
        ('cancelled', 'Отменен'),
    ]
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='owners')
    products = models.ManyToManyField(Product, through='OrderItem', through_fields=('order', 'product'),
                                      related_name='orders')
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name = 'Заказ'
        verbose_name_plural = 'Заказы'
        ordering = ['-created_at']  # Сортируем по дате создания в обратном порядке

    def __str__(self) -> str:
        return f'Order #{self.pk} by {self.user}'

    def calculate_total(self) -> Decimal:
        """
        Возвращает сумму всех (price * quantity) для элементов заказа.
        Использует агрегацию на уровне БД для эффективности.
        """
        total = self.items.annotate(line_total=F('price') * F('quantity')) \
                          .aggregate(sum=Sum('line_total'))['sum']
        return total or Decimal('0.00')

    @property
    def total_price(self) -> Decimal:
        return self.calculate_total()


class OrderItem(models.Model):
    """
    Представляет промежуточную модель для связи продуктов в определенном количестве с конкретным заказом

    Атрибуты:
        order (ForeignKey): Заказ
        product (ForeignKey): Товар
        price (DecimalField): Цена товара
        quantity (PositiveInteger): Количество товара в заказе

    """

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='order_items')
    quantity = models.PositiveIntegerField(default=1)
    price = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        unique_together = ('order', 'product')
        verbose_name = 'Детали заказа'
        verbose_name_plural = 'Детали заказов'



from decimal import Decimal

from django.db.models import Sum, F
from django.utils import timezone
from django.db import models
from django.conf import settings

from products.models import Product


class Cart(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='cart_owner')
    products = models.ManyToManyField(Product, through='CartItem', through_fields=('cart', 'product'),
                                      related_name='carts')
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Корзина'
        verbose_name_plural = 'Корзины'
        ordering = ['-updated_at']  # Сортируем по дате создания в обратном порядке

    def __str__(self) -> str:
        return f'Cart #{self.pk} by {self.user}'

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

    @property
    def owner(self):
        return self.user


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='cart_items')
    quantity = models.PositiveIntegerField(default=1)
    price = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        unique_together = ('cart', 'product')
        verbose_name = 'Детали корзины'
        verbose_name_plural = 'Детали корзин'

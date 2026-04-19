# cart/services.py
from django.db import transaction
from .models import Cart
import logging

logger = logging.getLogger(__name__)


class CartService:
    @staticmethod
    def clear_cart(user) -> bool:
        """
        Очищает корзину пользователя.
        Возвращает True, если корзина существовала и была очищена, иначе False.
        """
        try:
            cart = Cart.objects.get(user=user)
            with transaction.atomic():
                cart.items.all().delete()
            logger.info(f'Корзина пользователя {user.username} очищена через сервис')
            return True
        except Cart.DoesNotExist:
            logger.warning(f'Попытка очистить несуществующую корзину для пользователя {user.username}')
            return False

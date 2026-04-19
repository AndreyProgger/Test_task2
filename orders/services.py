from decimal import Decimal
from typing import Tuple, List, Optional

from django.db import transaction

from carts.models import Cart
from .models import Order, Product, OrderItem
import logging

stock_logger = logging.getLogger('stock')
logger = logging.getLogger(__name__)


class OrderService:
    """Сервис для работы с заказами"""

    @staticmethod
    def restore_stock_for_cancelled_order(order: Order) -> dict:
        """
        Возвращает товары на склад при отмене заказа.
        Использует транзакцию и блокировку строк для предотвращения гонок.

        Returns:
            dict: {
                'success': bool,
                'restored_items': list,
                'failed_items': list,
                'message': str
            }
        """
        with transaction.atomic():
            # Получаем все товары из заказа с блокировкой для обновления
            order_items = order.items.select_related('product').all()
            product_ids = [item.product_id for item in order_items]

            # Блокируем продукты для безопасного обновления остатков
            products = Product.objects.select_for_update().in_bulk(product_ids)

            restored_items = []
            failed_items = []

            for item in order_items:
                product = products.get(item.product_id)
                if product:
                    # Возвращаем количество на склад
                    product.stock += item.quantity
                    product.save(update_fields=['stock'])
                    restored_items.append({
                        'product_id': product.id,
                        'product_name': product.name,
                        'quantity': item.quantity,
                        'new_stock': product.stock
                    })

                    stock_logger.info(
                        f'Возврат товара на склад: заказ #{order.pk}, '
                        f'товар "{product.name}", количество: {item.quantity}, '
                        f'новый остаток: {product.stock}'
                    )
                else:
                    # Товар был удален - логируем, но не прерываем процесс
                    failed_items.append({
                        'product_id': item.product_id,
                        'product_name': item.product.name if item.product else 'Unknown',
                        'quantity': item.quantity
                    })

                    stock_logger.warning(
                        f'Невозможно вернуть на склад товар из заказа #{order.pk}: '
                        f'товар с ID {item.product_id} не найден'
                    )

            if restored_items:
                items_str = ", ".join([f"{item['product_name']} (+{item['quantity']})"
                                       for item in restored_items])
                stock_logger.info(
                    f'Заказ #{order.pk} отменен. Возвращены товары на склад: {items_str}'
                )

            return {
                'success': len(failed_items) == 0,
                'restored_items': restored_items,
                'failed_items': failed_items,
                'message': f'Восстановлено товаров: {len(restored_items)}, не удалось: {len(failed_items)}'
            }

    @staticmethod
    def create_order_from_cart(cart: Cart, user, status: str = 'new') -> Tuple[Optional[Order], List[str]]:
        """
        Создает заказ на основе корзины пользователя.
        Включает проверку наличия, списание со склада и расчет стоимости.

        Args:
            cart: объект корзины
            user: пользователь, создающий заказ
            status: начальный статус заказа

        Returns:
            Tuple[Order, List[str]]: (созданный_заказ, список_ошибок)
            Если есть ошибки, заказ будет None
        """
        cart_items = cart.items.select_related('product').all()

        if not cart_items.exists():
            return None, ['Корзина пуста, невозможно создать заказ.']

        with transaction.atomic():
            # Блокируем продукты для проверки и обновления
            product_ids = [item.product_id for item in cart_items]
            products = Product.objects.select_for_update().in_bulk(product_ids)

            # Валидируем товары в корзине
            insufficient = []
            for item in cart_items:
                product = products.get(item.product_id)

                if not product:
                    insufficient.append(f'Товар "{item.product.name}" больше не доступен.')
                    continue

                if product.is_deleted:
                    insufficient.append(f'Товар "{product.name}" был удален и недоступен для заказа.')
                    continue

                if not product.is_active:
                    insufficient.append(f'Товар "{product.name}" деактивирован и недоступен для заказа.')
                    continue

                if product.stock < item.quantity:
                    insufficient.append(
                        f'Недостаточно товара "{product.name}". '
                        f'Доступно: {product.stock}, запрошено: {item.quantity}.'
                    )

            if insufficient:
                return None, insufficient

            # Создаем заказ
            order = Order.objects.create(
                user=user,
                status=status
            )

            total_price = Decimal('0.00')
            order_items = []
            stock_updates = []

            # Создаем позиции заказа и готовим обновления склада
            for item in cart_items:
                product = products[item.product_id]
                quantity = item.quantity

                current_price = product.price
                if hasattr(product, 'discount_price') and product.discount_price is not None:
                    if product.discount_price < product.price:
                        current_price = product.discount_price

                # Создаем позицию заказа
                order_item = OrderItem(
                    order=order,
                    product=product,
                    quantity=quantity,
                    price=current_price
                )
                order_items.append(order_item)

                # Готовим обновление склада
                product.stock -= quantity
                stock_updates.append(product)

                stock_logger.info(
                    f'Списание со склада: заказ #{order.pk}, '
                    f'товар "{product.name}", количество: {quantity}, '
                    f'новый остаток: {product.stock}'
                )

            # Массовое создание позиций заказа
            OrderItem.objects.bulk_create(order_items)

            # Массовое обновление остатков
            Product.objects.bulk_update(stock_updates, ['stock'])

            order.save()

            logger.info(
                f'Создан заказ #{order.pk} пользователем {user.username}. '
                f'Товаров: {len(order_items)}, сумма: {total_price}'
            )

            return order, []

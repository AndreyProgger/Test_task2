import pytest
from decimal import Decimal

from django.db import IntegrityError
from django.urls import reverse
from rest_framework import status

from carts.models import Cart, CartItem
from .models import Order, OrderItem
from products.models import Product
from .services import OrderService

pytestmark = pytest.mark.django_db


class TestOrderModel:
    def test_create_order(self, user):
        order = Order.objects.create(user=user)
        assert order.user == user
        assert order.status == 'new'
        assert order.total_price == Decimal('0.00')

    def test_order_str_method(self, order):
        assert str(order) == f'Order #{order.pk} by {order.user}'

    def test_order_total_price(self, order, product):
        assert order.total_price == Decimal('199.98')

    def test_order_total_price_with_multiple_items(self, order, product, seller_user):
        product2 = Product.objects.create(name='Another', price=Decimal('50.00'), stock=10, seller=seller_user)
        OrderItem.objects.create(order=order, product=product2, quantity=1, price=Decimal('50.00'))
        assert order.total_price == Decimal('249.98')


class TestOrderItemModel:
    def test_create_order_item(self, user, product, seller_user):
        order = Order.objects.create(user=user, status='pending')
        item = OrderItem.objects.create(order=order, product=product, quantity=3, price=product.price)
        assert item.order == order
        assert item.product == product
        assert item.quantity == 3
        assert item.price == product.price

    def test_unique_together(self, user, product):
        order = Order.objects.create(user=user, status='pending')
        OrderItem.objects.create(order=order, product=product, quantity=1, price=product.price)
        with pytest.raises(IntegrityError):
            OrderItem.objects.create(order=order, product=product, quantity=2, price=product.price)


class TestOrderItemCreateSerializer:
    def test_valid_data(self):
        from orders.serializers import OrderItemCreateSerializer
        data = {'product_name': 'Test', 'quantity': 2}
        serializer = OrderItemCreateSerializer(data=data)
        assert serializer.is_valid()
        assert serializer.validated_data['quantity'] == 2

    def test_invalid_quantity(self):
        from orders.serializers import OrderItemCreateSerializer
        data = {'product_name': 'Test', 'quantity': 0}
        serializer = OrderItemCreateSerializer(data=data)
        assert not serializer.is_valid()
        assert 'quantity' in serializer.errors


class TestOrderSerializer:
    def test_serializer_output(self, order):
        from orders.serializers import OrderSerializer
        serializer = OrderSerializer(instance=order)
        data = serializer.data
        assert data['user'] == str(order.user)
        assert data['status'] == order.status
        assert len(data['items']) == 1
        assert data['total_price'] == str(order.total_price)


class TestOrderCreateAPI:
    def test_create_order_success(self, auth_client, product):
        client, user = auth_client
        # 1. Добавляем товар в корзину через API корзины
        cart_url = reverse('cart')
        cart_data = {'product_id': product.id, 'quantity': 2}
        cart_response = client.post(cart_url, cart_data, format='json')
        assert cart_response.status_code == status.HTTP_201_CREATED

        # 2. Создаём заказ из корзины (тело запроса пустое)
        url = reverse('order-list')
        response = client.post(url, {}, format='json')
        assert response.status_code == status.HTTP_201_CREATED

        order = Order.objects.filter(user=user).first()
        assert order is not None
        assert order.items.count() == 1
        item = order.items.first()
        assert item.product == product
        assert item.quantity == 2
        product.refresh_from_db()
        assert product.stock == 8  # было 10, заказали 2

    def test_create_order_stock_decrease(self, auth_client, product):
        client, _ = auth_client
        initial_stock = product.stock

        cart_url = reverse('cart')
        client.post(cart_url, {'product_id': product.id, 'quantity': 3})

        url = reverse('order-list')
        response = client.post(url, {}, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        product.refresh_from_db()
        assert product.stock == initial_stock - 3

    def test_create_order_inactive_product(self, auth_client, inactive_product):
        client, user = auth_client
        # Добавляем неактивный товар напрямую в корзину (API может запретить)
        cart = Cart.objects.get(user=user)
        CartItem.objects.create(cart=cart, product=inactive_product, quantity=1, price=inactive_product.price)

        url = reverse('order-list')
        response = client.post(url, {}, format='json')
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        error_str = str(response.data).lower()
        assert 'неактив' in error_str or 'inactive' in error_str

    def test_create_order_deleted_product(self, auth_client, deleted_product):
        client, user = auth_client
        cart = Cart.objects.get(user=user)
        CartItem.objects.create(cart=cart, product=deleted_product, quantity=1, price=deleted_product.price)

        url = reverse('order-list')
        response = client.post(url, {}, format='json')
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        error_str = str(response.data).lower()
        assert 'удален' in error_str or 'deleted' in error_str

    def test_create_order_own_product(self, seller_auth_client, product):
        client, seller = seller_auth_client
        # Пытаемся добавить свой товар через API корзины
        cart_url = reverse('cart')
        cart_data = {'product_id': product.id, 'quantity': 1}
        cart_response = client.post(cart_url, cart_data, format='json')
        # Ожидаем, что API корзины вернёт 400 (запрет на свой товар)
        assert cart_response.status_code == status.HTTP_400_BAD_REQUEST
        # Заказ даже не пытаемся создавать, тест пройден

    def test_create_order_unauthenticated(self, api_client):
        url = reverse('order-list')
        response = api_client.post(url, {}, format='json')
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestOrderStatusUpdateAPI:
    def test_admin_update_status_valid_transition(self, admin_auth_client, order):
        client, _ = admin_auth_client
        url = reverse('order_status-update', args=[order.id])
        data = {'status': 'paid'}
        response = client.put(url, data, format='json')
        assert response.status_code == status.HTTP_200_OK
        order.refresh_from_db()
        assert order.status == 'paid'

    def test_admin_update_status_invalid_transition(self, admin_auth_client, order):
        client, _ = admin_auth_client
        url = reverse('order_status-update', args=[order.id])
        data = {'status': 'in_delivery'}
        response = client.put(url, data, format='json')
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'Не допустимый переход' in response.data['message']

    def test_cannot_update_completed_order(self, admin_auth_client, order):
        order.status = 'completed'
        order.save()
        client, _ = admin_auth_client
        url = reverse('order_status-update', args=[order.id])
        data = {'status': 'cancelled'}
        response = client.put(url, data, format='json')
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'нельзя изменить статус отмененного или выполненного заказа' in response.data['message'].lower()

    def test_non_admin_cannot_update_status(self, auth_client, order):
        client, _ = auth_client   # обычный пользователь (не админ)
        url = reverse('order_status-update', args=[order.id])
        data = {'status': 'cancelled'}
        response = client.put(url, data, format='json')
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_unauthenticated_cannot_update_status(self, api_client, order):
        url = reverse('order_status-update', args=[order.id])
        data = {'status': 'cancelled'}
        response = api_client.put(url, data, format='json')
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestOrderListView:

    def test_list_orders_authenticated(self, auth_client, order):
        client, user = auth_client
        url = reverse('order-list')
        response = client.get(url)
        assert response.status_code == status.HTTP_200_OK
        # предполагаем пагинацию
        if 'results' in response.data:
            orders = response.data['results']
        else:
            orders = response.data
        assert len(orders) == 1

    def test_list_orders_unauthenticated(self, api_client):
        url = reverse('order-list')
        response = api_client.get(url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestOrderDetailView:
    def test_get_order_detail_owner(self, auth_client, order):
        client, _ = auth_client
        url = reverse('order-detail', args=[order.id])
        response = client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data['id'] == order.id

    def test_get_order_detail_not_owner(self, api_client, order, seller_auth_client):
        client, user = seller_auth_client
        url = reverse('order-detail', args=[order.id])
        response = client.get(url)
        assert response.status_code == status.HTTP_403_FORBIDDEN

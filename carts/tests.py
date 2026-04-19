from decimal import Decimal

import pytest
from django.db import IntegrityError
from django.urls import reverse
from rest_framework import status

from conftest import product, cart, cart_item
from .models import CartItem, Cart
from .serializers import AddCartItemSerializer, EditCartItemSerializer, CartSerializer, CartItemSerializer

pytestmark = pytest.mark.django_db


class TestCartModel:

    def test_create_cart(self, user):
        Cart.objects.filter(user=user).delete()
        cart = Cart.objects.create(user=user)
        assert cart.user == user
        assert cart.total_price == Decimal('0.00')

    def test_cart_str_method(self, cart):
        assert str(cart) == f'Cart #{cart.pk} by {cart.user}'

    def test_cart_one_to_one(self, user):
        Cart.objects.filter(user=user).delete()
        cart1 = Cart.objects.create(user=user)
        with pytest.raises(IntegrityError):
            Cart.objects.create(user=user)

    def test_cart_total_price_empty(self, cart):
        cart.items.all().delete()
        cart.refresh_from_db()
        assert cart.total_price == Decimal('0.00')

    def test_cart_total_price_with_items(self, cart, product):
        cart.items.all().delete()
        CartItem.objects.create(cart=cart, product=product, quantity=3, price=Decimal('100.00'))
        cart.refresh_from_db()
        assert cart.total_price == Decimal('300.00')

    def test_cart_total_price_multiple_items(self, cart, product, seller_user):
        from products.models import Product
        cart.items.all().delete()
        product2 = Product.objects.create(name='Another', price=Decimal('50.00'), stock=10, seller=seller_user)
        CartItem.objects.create(cart=cart, product=product, quantity=2, price=Decimal('100.00'))
        CartItem.objects.create(cart=cart, product=product2, quantity=1, price=Decimal('50.00'))
        cart.refresh_from_db()
        assert cart.total_price == Decimal('250.00')


class TestCartItemModel:
    def test_create_cart_item(self, cart, product):
        item = CartItem.objects.create(
            cart=cart,
            product=product,
            quantity=3,
            price=product.price
        )
        assert item.cart == cart
        assert item.product == product
        assert item.quantity == 3
        assert item.price == product.price

    def test_unique_together(self, cart, product):
        CartItem.objects.create(cart=cart, product=product, quantity=1, price=product.price)
        with pytest.raises(Exception):  # IntegrityError
            CartItem.objects.create(cart=cart, product=product, quantity=2, price=product.price)


class TestCartItemSerializer:
    def test_serializer_output(self, cart_item):
        serializer = CartItemSerializer(instance=cart_item)
        data = serializer.data
        assert data['id'] == cart_item.id
        assert data['product'] == cart_item.product.id
        assert data['quantity'] == cart_item.quantity
        assert Decimal(data['unit_price']) == cart_item.product.price
        assert Decimal(data['total_price']) == cart_item.product.price * cart_item.quantity


class TestCartSerializer:
    def test_serializer_output(self, cart, cart_item):
        serializer = CartSerializer(instance=cart)
        data = serializer.data
        assert data['id'] == cart.id
        assert data['user'] == cart.user.id
        assert len(data['items']) == 1
        assert Decimal(data['total_price']) == cart_item.product.price * cart_item.quantity
        assert data['unique_items_count'] == 1

    def test_serializer_empty_cart(self, cart):
        serializer = CartSerializer(instance=cart)
        data = serializer.data
        assert data['items'] == []
        assert data['total_price'] == Decimal('0.00')
        assert data['unique_items_count'] == 0


class TestAddCartItemSerializer:
    def test_valid_data(self):
        data = {'product_id': 1, 'quantity': 2}
        serializer = AddCartItemSerializer(data=data)
        assert serializer.is_valid()
        assert serializer.validated_data['product_id'] == 1
        assert serializer.validated_data['quantity'] == 2

    def test_missing_product_id(self):
        data = {'quantity': 2}
        serializer = AddCartItemSerializer(data=data)
        assert not serializer.is_valid()
        assert 'product_id' in serializer.errors

    def test_missing_quantity(self):
        data = {'product_id': 1}
        serializer = AddCartItemSerializer(data=data)
        assert not serializer.is_valid()
        assert 'quantity' in serializer.errors

    def test_negative_quantity(self):
        data = {'product_id': 1, 'quantity': -1}
        serializer = AddCartItemSerializer(data=data)
        assert not serializer.is_valid()
        assert 'quantity' in serializer.errors


class TestEditCartItemSerializer:
    def test_valid_data(self):
        data = {'quantity': 5}
        serializer = EditCartItemSerializer(data=data)
        assert serializer.is_valid()
        assert serializer.validated_data['quantity'] == 5

    def test_negative_quantity(self):
        data = {'quantity': -3}
        serializer = EditCartItemSerializer(data=data)
        assert not serializer.is_valid()
        assert 'quantity' in serializer.errors


class TestCartByUserListView:
    def test_get_cart_unauthenticated(self, api_client):
        url = reverse('cart')
        response = api_client.get(url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_get_cart_authenticated(self, auth_client, cart, cart_item):
        client, user = auth_client
        url = reverse('cart')
        response = client.get(url)
        assert response.status_code == status.HTTP_200_OK
        data = response.data
        assert data['user'] == user.id
        assert len(data['items']) == 1
        assert data['items'][0]['product'] == cart_item.product.id

    def test_add_product_to_cart_success(self, auth_client, product):
        client, user = auth_client
        url = reverse('cart')
        data = {'product_id': product.id, 'quantity': 2}
        response = client.post(url, data)
        assert response.status_code == status.HTTP_201_CREATED
        cart = Cart.objects.get(user=user)
        assert cart.items.count() == 1
        item = cart.items.first()
        assert item.product == product
        assert item.quantity == 2
        assert item.price == product.price

    def test_add_product_increase_quantity(self, auth_client, cart_item):
        client, user = auth_client
        product = cart_item.product
        url = reverse('cart')
        data = {'product_id': product.id, 'quantity': 1}
        response = client.post(url, data)
        assert response.status_code == status.HTTP_200_OK
        cart_item.refresh_from_db()
        assert cart_item.quantity == 3

    def test_add_product_insufficient_stock(self, auth_client, product):
        product.stock = 1
        product.save()
        client, _ = auth_client
        url = reverse('cart')
        data = {'product_id': product.id, 'quantity': 5}
        response = client.post(url, data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'Нельзя добавить в корзину больше' in response.data['error']

    def test_add_own_product(self, seller_auth_client, product):
        client, _ = seller_auth_client
        url = reverse('cart')
        data = {'product_id': product.id, 'quantity': 1}
        response = client.post(url, data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'Нельзя добавить в корзину свой товар' in response.data['error']

    def test_add_inactive_product(self, auth_client, inactive_product):
        client, _ = auth_client
        url = reverse('cart')
        data = {'product_id': inactive_product.id, 'quantity': 1}
        response = client.post(url, data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'неактивный товар' in response.data['error']

    def test_add_product_without_auth(self, api_client, product):
        url = reverse('cart')
        data = {'product_id': product.id, 'quantity': 1}
        response = api_client.post(url, data)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_add_product_invalid_data(self, auth_client):
        client, _ = auth_client
        url = reverse('cart')
        data = {'product_id': 99999, 'quantity': 1}
        response = client.post(url, data)
        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestCartItemView:
    def test_update_cart_item_quantity(self, auth_client, cart_item):
        client, _ = auth_client
        url = reverse('cart-item', args=[cart_item.id])
        data = {'quantity': 3}
        response = client.put(url, data)
        assert response.status_code == status.HTTP_200_OK
        cart_item.refresh_from_db()
        assert cart_item.quantity == 5

    def test_update_cart_item_invalid_quantity(self, auth_client, cart_item):
        client, _ = auth_client
        url = reverse('cart-item', args=[cart_item.id])
        data = {'quantity': -1}
        response = client.put(url, data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_update_cart_item_not_found(self, auth_client):
        client, _ = auth_client
        url = reverse('cart-item', args=[99999])
        data = {'quantity': 1}
        response = client.put(url, data)
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_update_cart_item_unauthenticated(self, api_client, cart_item):
        url = reverse('cart-item', args=[cart_item.id])
        data = {'quantity': 1}
        response = api_client.put(url, data)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_delete_cart_item(self, auth_client, cart_item):
        client, _ = auth_client
        url = reverse('cart-item', args=[cart_item.id])
        response = client.delete(url)
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not CartItem.objects.filter(id=cart_item.id).exists()

    def test_delete_cart_item_not_found(self, auth_client):
        client, _ = auth_client
        url = reverse('cart-item', args=[99999])
        response = client.delete(url)
        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestCartClearView:
    def test_clear_cart_success(self, auth_client, cart, cart_item):
        client, _ = auth_client
        url = reverse('cart-clear')
        response = client.delete(url)
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert Cart.objects.get(user=cart.user).items.count() == 0

    def test_clear_cart_unauthenticated(self, api_client):
        url = reverse('cart-clear')
        response = api_client.delete(url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

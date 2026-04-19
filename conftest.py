import uuid
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from carts.models import Cart, CartItem
from delivery.models import Address
from favorites.models import Favorite, FavoriteItem
from orders.models import Order, OrderItem
from products.models import Category, Product
from reviews.models import Review

User = get_user_model()


def short_uid() -> str:
    return str(uuid.uuid4().int)[:4]  # 4 цифры, например '1234'


# ========== Глобальные фикстуры для всех приложений ==========


@pytest.fixture(scope='session')
def django_db_setup(django_db_setup, django_db_blocker):
    """Настройка БД для всей сессии тестов"""
    with django_db_blocker.unblock():
        # Здесь можно добавить глобальную настройку БД
        pass


@pytest.fixture
def api_client():
    """API клиент без аутентификации"""
    return APIClient()


@pytest.fixture
def user(db):
    """Обычный пользователь – владелец адресов, корзин, избранного и т.д."""
    uid = short_uid()
    return User.objects.create_user(
        username=f'u{uid}',          # например 'u1234' (5 символов)
        email=f'u{uid}@example.com',
        password='testpass123',
        first_name='Test',
        last_name='User',
        role='user'
    )


@pytest.fixture
def seller_user(db):
    uid = short_uid()
    return User.objects.create_user(
        username=f's{uid}',          # 's5678' (5 символов)
        email=f's{uid}@example.com',
        password='sellerpass123',
        first_name='Seller',
        last_name='Test',
        role='seller'
    )


@pytest.fixture
def admin_user(db):
    return User.objects.create_user(
        username='admin',            # 5 символов
        email='admin@example.com',
        password='adminpass123',
        first_name='Admin',
        last_name='User',
        role='admin',
        is_staff=True
    )


# ---- АУТЕНТИФИЦИРОВАННЫЕ КЛИЕНТЫ ----
@pytest.fixture
def auth_client(api_client, user):
    """Клиент, аутентифицированный как обычный пользователь (тот же, что и в address и др.)"""
    api_client.force_authenticate(user=user)
    return api_client, user


@pytest.fixture
def seller_auth_client(api_client, seller_user):
    api_client.force_authenticate(user=seller_user)
    return api_client, seller_user


@pytest.fixture
def admin_auth_client(api_client, admin_user):
    api_client.force_authenticate(user=admin_user)
    return api_client, admin_user


# ---- ОСТАЛЬНЫЕ ФИКСТУРЫ (категории, товары, адреса, заказы, отзывы) ----
@pytest.fixture
def category(db):
    return Category.objects.create(name='Electronics', slug='electronics')


@pytest.fixture
def subcategory(db, category):
    return Category.objects.create(name='Laptops', slug='laptops', parent=category)


@pytest.fixture
def product(db, seller_user):
    return Product.objects.create(
        name='Test Product',
        price=Decimal('99.99'),
        stock=10,
        seller=seller_user
    )


@pytest.fixture
def inactive_product(db, seller_user):
    return Product.objects.create(
        name='Inactive Product',
        price=Decimal('49.99'),
        stock=5,
        seller=seller_user,
        is_active=False,
        is_deleted=False
    )


@pytest.fixture
def deleted_product(db, seller_user):
    return Product.objects.create(
        name='Deleted Product',
        price=Decimal('29.99'),
        stock=0,
        seller=seller_user,
        is_active=True,
        is_deleted=True
    )


@pytest.fixture
def multiple_products(db, seller_user):
    products = []
    for i in range(1, 6):
        product = Product.objects.create(
            name=f'Product {i}',
            description=f'Description {i}',
            price=Decimal(str(100 * i)),
            stock=10 * i,
            seller=seller_user,
            is_active=True
        )
        products.append(product)
    return products


@pytest.fixture
def address(db, user):
    return Address.objects.create(
        user=user,
        city='Moscow',
        street='Tverskaya',
        house='10',
        apartment='5',
        postal_code='101000',
        is_default=True
    )


@pytest.fixture
def second_address(db, user):
    return Address.objects.create(
        user=user,
        city='Saint Petersburg',
        street='Nevsky',
        house='20',
        apartment='10',
        postal_code='191000',
        is_default=False
    )


@pytest.fixture
def order(db, user, product):
    order = Order.objects.create(user=user, status='new')
    OrderItem.objects.create(order=order, product=product, quantity=2, price=product.price)
    return order


@pytest.fixture
def order2(db, user, product):
    order = Order.objects.create(user=user, status='completed')
    OrderItem.objects.create(order=order, product=product, quantity=1, price=product.price)
    return order


@pytest.fixture
def review(db, user, product, order2):
    return Review.objects.create(
        product=product,
        user=user,
        rating=5,
        text='Great product!'
    )


@pytest.fixture
def favorite(db, user):
    return Favorite.objects.create(user=user)


@pytest.fixture
def favorite_item(db, favorite, product):
    return FavoriteItem.objects.create(
        favorite=favorite,
        product=product,
        exist=True
    )


@pytest.fixture
def cart(db, user):
    cart, _ = Cart.objects.get_or_create(user=user)
    return cart


@pytest.fixture
def cart_item(db, cart, product):
    return CartItem.objects.create(
        cart=cart,
        product=product,
        quantity=2,
        price=product.price
    )


@pytest.fixture
def jwt_auth_client(db):
    user = User.objects.create_user(
        username='jwtusr',          # 6 символов
        email='jwt@example.com',
        password='jwtpass123',
        first_name='JWT',
        last_name='User',
        role='user'
    )
    refresh = RefreshToken.for_user(user)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
    return client, user


@pytest.fixture
def create_user(db):
    counter = 1
    def make_user(**kwargs):
        nonlocal counter
        # Имя не длиннее 6 символов: обрезаем до 6
        username = f'u{counter}'[:6]
        defaults = {
            'username': username,
            'email': f'{username}@example.com',
            'password': 'defaultpass123',
            'first_name': 'Test',
            'last_name': 'User',
            'role': 'customer'
        }
        defaults.update(kwargs)
        counter += 1
        return User.objects.create_user(**defaults)
    return make_user

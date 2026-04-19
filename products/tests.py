from decimal import Decimal

import pytest
from django.urls import reverse
from django.core.exceptions import ValidationError
from rest_framework import status

from conftest import subcategory
from .models import Product, Category

pytestmark = pytest.mark.django_db


class TestProductModel:
    """Тесты модели товара"""

    def test_create_product(self, seller_user):
        """Тест создания товара"""
        product = Product.objects.create(
            name='Test Product',
            description='Test Description',
            price=Decimal('99.99'),
            stock=10,
            seller=seller_user
        )
        assert product.name == 'Test Product'
        assert product.price == Decimal('99.99')
        assert product.stock == 10
        assert product.seller == seller_user

    def test_product_str_method(self, product):
        """Тест строкового представления"""
        expected_str = f"Название: {product.name}, Количество: {product.stock}, Цена: {product.price}, Продавец: {product.seller}."
        assert str(product) == expected_str

    def test_product_price_positive(self, seller_user):
        """Тест положительной цены"""
        with pytest.raises(ValidationError):
            product = Product(
                name='Invalid',
                price=Decimal('-10.00'),
                stock=5,
                seller=seller_user
            )
            product.full_clean()
            product.save()

    def test_product_stock_non_negative(self, seller_user):
        """Тест неотрицательного количества"""
        product = Product.objects.create(
            name='Test',
            price=Decimal('100'),  # Используйте Decimal
            stock=0,
            seller=seller_user
        )
        assert product.stock == 0

        # Дополнительно проверяем, что нельзя создать с отрицательным запасом
        with pytest.raises(ValidationError):
            invalid_product = Product(
                name='Invalid',
                price=Decimal('100'),
                stock=-5,
                seller=seller_user
            )
            invalid_product.full_clean()


class TestProductsAPI:
    """Тесты API товаров"""

    def test_list_products_unauthenticated(self, api_client, multiple_products):
        """Тест получения списка товаров без аутентификации"""
        url = reverse('product-list')
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == len(multiple_products)

    def test_list_products_authenticated(self, auth_client, multiple_products):
        """Тест получения списка товаров с аутентификацией"""
        client, _ = auth_client
        url = reverse('product-list')
        response = client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == len(multiple_products)

    def test_filter_products_by_price(self, api_client, multiple_products):
        """Тест фильтрации товаров по цене"""
        url = reverse('product-list')
        response = api_client.get(url, {'min_price': 150, 'max_price': 250})

        assert response.status_code == status.HTTP_200_OK
        for product in response.data:
            price = float(product['price'])
            assert 150 <= price <= 250

    def test_search_products(self, api_client, multiple_products):
        """Тест поиска товаров"""
        url = reverse('product-list')
        response = api_client.get(url, {'search': 'Product 1'})

        assert response.status_code == status.HTTP_200_OK
        assert any('Product 1' in p['name'] for p in response.data)

    def test_create_product_as_seller(self, seller_auth_client):
        """Тест создания товара продавцом"""
        client, seller = seller_auth_client
        url = reverse('product-list')
        data = {
            'name': 'New Product',
            'description': 'New Description',
            'price': 299.99,
            'stock': 50
        }
        response = client.post(url, data)

        assert response.status_code == status.HTTP_201_CREATED
        assert Product.objects.filter(name='New Product').exists()
        product = Product.objects.get(name='New Product')
        assert product.seller == seller

    def test_create_product_as_customer(self, auth_client):
        """Тест создания товара обычным пользователем (должен быть запрещен)"""
        client, _ = auth_client
        url = reverse('product-list')
        data = {
            'name': 'New Product',
            'price': 299.99,
            'stock': 50
        }
        response = client.post(url, data)

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_create_product_without_auth(self, api_client):
        """Тест создания товара без аутентификации"""
        url = reverse('product-list')
        data = {'name': 'New Product', 'price': 100, 'stock': 10}
        response = api_client.post(url, data)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_update_product_as_owner(self, seller_auth_client, product):
        """Тест обновления товара владельцем"""
        client, _ = seller_auth_client
        url = reverse('product-detail', args=[product.id])
        data = {'name': 'Updated Name', 'price': 150.00}
        response = client.put(url, data)

        assert response.status_code == status.HTTP_200_OK
        product.refresh_from_db()
        assert product.name == 'Updated Name'
        assert product.price == Decimal(150.00)

    def test_update_product_not_owner(self, auth_client, product):
        """Тест обновления товара не владельцем"""
        client, _ = auth_client
        url = reverse('product-detail', args=[product.id])
        data = {'name': 'Hacked Name'}
        response = client.put(url, data)

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_delete_product_as_owner(self, seller_auth_client, product):
        client, _ = seller_auth_client
        url = reverse('product-detail', args=[product.id])
        response = client.delete(url)
        assert response.status_code == status.HTTP_204_NO_CONTENT
        product.refresh_from_db()
        assert product.is_deleted is True

    def test_get_product_detail(self, auth_client, product):
        """Тест получения деталей товара"""
        client, _ = auth_client  # разверните кортеж
        url = reverse('product-detail', args=[product.id])
        response = client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data['id'] == product.id
        assert response.data['name'] == product.name


class TestProductValidation:
    """Тесты валидации товаров"""

    def test_invalid_price_negative(self, seller_auth_client):
        """Тест с отрицательной ценой"""
        client, _ = seller_auth_client
        url = reverse('product-list')
        data = {
            'name': 'Invalid',
            'price': -100,
            'stock': 10
        }
        response = client.post(url, data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'details' in response.data
        assert 'price' in response.data['details']
        assert 'greater than or equal to 0.01' in str(response.data['details']['price'])

    def test_invalid_stock_negative(self, seller_auth_client):
        """Тест с отрицательным количеством"""
        client, _ = seller_auth_client
        url = reverse('product-list')
        data = {
            'name': 'Invalid',
            'price': 100,
            'stock': -5
        }
        response = client.post(url, data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'details' in response.data
        assert 'stock' in response.data['details']
        assert 'greater than or equal to 0' in str(response.data['details']['stock'])

    def test_invalid_discount_price(self, seller_auth_client):
        """Тест с неправильной скидочной ценой"""
        client, _ = seller_auth_client
        url = reverse('product-list')
        data = {
            'name': 'Invalid',
            'price': 100,
            'discount_price': 150,
            'stock': 5
        }
        response = client.post(url, data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'details' in response.data
        # Ошибка скидочной цены - non_field_errors
        assert 'non_field_errors' in response.data['details']
        assert 'Цена со скидкой должна быть меньше обычной цены' in str(response.data['details']['non_field_errors'])

    def test_missing_required_fields(self, seller_auth_client):
        client, _ = seller_auth_client
        url = reverse('product-list')
        data = {'price': 100}
        response = client.post(url, data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'details' in response.data
        assert 'name' in response.data['details']

        assert response.data['details']['name']
        assert 'required' in str(response.data['details']['name']).lower()


class TestCategoryModel:
    def test_create_category(self, category):
        assert category.name == 'Electronics'
        assert category.slug == 'electronics'
        assert category.parent is None
        assert category.is_active is True

    def test_category_str_without_parent(self, category):
        assert str(category) == 'Electronics'

    def test_category_str_with_parent(self, subcategory, category):
        assert str(subcategory) == 'Electronics → Laptops'

    def test_category_slug_auto_generation(self):
        cat = Category.objects.create(name='New & Unique')
        assert cat.slug == 'new-unique'

    def test_category_slug_uniqueness(self):
        Category.objects.create(name='Gadgets', slug='gadgets')
        cat2 = Category.objects.create(name='Gadgets')
        assert cat2.slug.startswith('gadgets-')

    def test_category_nesting_only_one_level(self, category, subcategory):
        with pytest.raises(ValidationError):
            Category.objects.create(name='Ultrabook', parent=subcategory)

    def test_category_cannot_be_self_parent(self, category):
        category.parent = category
        with pytest.raises(ValidationError):
            category.full_clean()

    def test_category_deletion_blocked_if_has_products(self, category, seller_user):
        Product.objects.create(
            name='Phone',
            price=500,
            stock=5,
            seller=seller_user,
            category=category
        )
        with pytest.raises(ValidationError, match='привязаны товары'):
            category.delete()

    def test_category_deletion_allowed_without_products(self, category):
        category.delete()
        assert not Category.objects.filter(id=category.id).exists()


class TestCategoryAPI:
    def test_list_categories_unauthenticated(self, api_client, category, subcategory):
        url = reverse('category-list')
        response = api_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 2

    def test_list_categories_authenticated(self, auth_client, category):
        client, _ = auth_client
        url = reverse('category-list')
        response = client.get(url)
        assert response.status_code == status.HTTP_200_OK

    def test_create_category_as_admin(self, admin_auth_client):
        client, _ = admin_auth_client
        url = reverse('category-list')
        data = {'name': 'Books'}
        response = client.post(url, data)
        assert response.status_code == status.HTTP_201_CREATED
        assert Category.objects.filter(name='Books').exists()

    def test_create_category_as_seller(self, seller_auth_client):
        client, _ = seller_auth_client
        url = reverse('category-list')
        data = {'name': 'Toys'}
        response = client.post(url, data)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_create_category_as_customer(self, auth_client):
        client, _ = auth_client
        url = reverse('category-list')
        data = {'name': 'Toys'}
        response = client.post(url, data)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_create_category_with_parent(self, admin_auth_client, category):
        client, _ = admin_auth_client
        url = reverse('category-list')
        data = {'name': 'Smartphones', 'parent': category.id}
        response = client.post(url, data)
        assert response.status_code == status.HTTP_201_CREATED
        new_cat = Category.objects.get(name='Smartphones')
        assert new_cat.parent == category

    def test_create_category_with_invalid_parent(self, admin_auth_client, subcategory):
        client, _ = admin_auth_client
        url = reverse('category-list')
        data = {'name': 'Invalid', 'parent': subcategory.id}
        response = client.post(url, data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        # Проверяем структуру ответа API
        assert 'details' in response.data
        assert 'parent' in response.data['details']
        assert 'один уровень вложенности' in str(response.data['details']['parent'])

    def test_retrieve_category(self, auth_client, category):
        client, _ = auth_client
        url = reverse('category-detail', args=[category.id])
        response = client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data['name'] == category.name

    def test_update_category_as_admin(self, admin_auth_client, category):
        client, _ = admin_auth_client
        url = reverse('category-detail', args=[category.id])
        data = {'name': 'Updated Electronics'}
        response = client.put(url, data)
        assert response.status_code == status.HTTP_200_OK
        category.refresh_from_db()
        assert category.name == 'Updated Electronics'

    def test_update_category_as_non_admin(self, seller_auth_client, category):
        client, _ = seller_auth_client
        url = reverse('category-detail', args=[category.id])
        data = {'name': 'Hacked'}
        response = client.put(url, data)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_delete_category_as_admin(self, admin_auth_client, category):
        client, _ = admin_auth_client
        url = reverse('category-detail', args=[category.id])
        response = client.delete(url)
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not Category.objects.filter(id=category.id).exists()

    def test_delete_category_with_products(self, admin_auth_client, category, seller_user):
        Product.objects.create(
            name='Phone',
            price=500,
            stock=5,
            seller=seller_user,
            category=category
        )
        client, _ = admin_auth_client
        url = reverse('category-detail', args=[category.id])
        response = client.delete(url)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'привязаны товары' in response.data['error']

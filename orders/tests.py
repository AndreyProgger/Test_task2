from decimal import Decimal
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIRequestFactory, force_authenticate
from rest_framework import status

from .models import Order, OrderItem
from .views import OrderByUserListView, OrderDetailView
from products.models import Product

User = get_user_model()


class OrderItemModelTests(TestCase):
    """ Тест моделей заказа и промежуточной """

    def setUp(self):
        # Создаем и сохраняем пользователя
        self.user = User.objects.create_user(
            email='example@mail.ru',
            username='Tested',
            first_name='Andrey',
            last_name='Diatlov',
            password='testpassword123'
        )

        # Создаем и сохраняем продукт
        self.product = Product.objects.create(
            name='Phone',
            description='Инструмент для мобильной связи',
            price=Decimal('5000.99'),
            stock=100,
            category='electronics'
        )

        # Создаем и сохраняем заказ
        self.order = Order.objects.create(
            user=self.user,
            status='pending'
        )

        # Создаем и сохраняем элемент заказа
        self.order_item1 = OrderItem.objects.create(
            order=self.order,
            product=self.product,
            price=Decimal('5000.99'),
            quantity=2
        )

    def test_order_item_creation(self):
        """Тест создания элемента заказа"""

        self.assertEqual(self.order_item1.order, self.order)
        self.assertEqual(self.order_item1.product, self.product)
        self.assertEqual(self.order_item1.price, Decimal('5000.99'))
        self.assertEqual(self.order_item1.quantity, 2)

    def test_order_relationships(self):
        """Тест связей заказа"""

        # Проверяем связь пользователя с заказом
        self.assertEqual(self.order.user, self.user)
        self.assertIn(self.order, self.user.owners.all())

        # Проверяем связь заказа с продуктами через OrderItem
        self.assertEqual(self.order.items.count(), 1)
        self.assertEqual(self.order.items.first(), self.order_item1)

        # Проверяем связь продукта с заказами
        self.assertEqual(self.product.order_items.count(), 1)
        self.assertEqual(self.product.order_items.first(), self.order_item1)

    def test_calculate_total(self):
        """Тест расчета общей суммы заказа"""

        total = self.order.calculate_total()
        expected_total = Decimal('5000.99') * 2  # price * quantity
        self.assertEqual(total, expected_total)

    def test_total_price_property(self):
        """Тест свойства total_price"""

        self.assertEqual(self.order.total_price, Decimal('10001.98'))

    def test_order_str_representation(self):
        """Тест строкового представления заказа"""

        self.assertEqual(str(self.order), f'Order #{self.order.pk} by {self.user}')


class OrderListAndDetailViewTests(TestCase):
    """ Тесты для представления списка заказов пользователя """

    def setUp(self):
        self.factory = APIRequestFactory()
        # Создаем и сохраняем пользователя
        self.user = User.objects.create_user(
            email='example@mail.ru',
            username='Tested',
            first_name='Andrey',
            last_name='Diatlov',
            password='testpassword123'
        )

        # Создаем и сохраняем продукт
        self.product = Product.objects.create(
            name='Phone',
            description='Инструмент для мобильной связи',
            price=Decimal('5000.99'),
            stock=100,
            category='electronics'
        )

        # Создаем и сохраняем заказ
        self.order = Order.objects.create(
            user=self.user,
            status='pending'
        )

        # Создаем и сохраняем элемент заказа
        self.order_item1 = OrderItem.objects.create(
            order=self.order,
            product=self.product,
            price=Decimal('5000.99'),
            quantity=2
        )

    def test_get_list(self):
        """ Тест проверяющий получение списка всех заказов пользователя """

        url = reverse("order-list")  # Получаем url для списка
        request = self.factory.get(url)
        view = OrderByUserListView.as_view()
        force_authenticate(request, user=self.user)
        response = view(request)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        # Проверяем, что вернули правильный заказ
        self.assertEqual(response.data[0]['status'], self.order.status)

    def test_order_create(self):
        """ Тест проверяющий создание заказа """

        url = reverse("order-list")  # получаем url для списка
        data = {"products": [{"product_name": "Phone", "quantity": 10}]}
        request = self.factory.post(url, data, format="json")  # используем POST, с json данными
        force_authenticate(request, user=self.user)
        view = OrderByUserListView.as_view()
        response = view(request)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Order.objects.count(), 2)  # проверяем, что создался объект
        new_product = Order.objects.filter(user=self.user).last()  # получаем объект
        self.assertNotEqual(new_product, None)  # проверяем что получили объект

    def test_get_detail(self):
        """ Тест проверяющий получение информации по конкретному заказа """

        url = reverse("order-detail", kwargs={'pk': self.order.pk})  # получаем url для detail
        request = self.factory.get(url)
        force_authenticate(request, user=self.user)
        view = OrderDetailView.as_view()
        response = view(request, pk=self.order.pk)
        self.assertEqual(response.status_code, status.HTTP_200_OK)  # Проверяем код ответа
        self.assertEqual(response.data['status'], self.order.status)  # Проверяем имя и описание продукта

    def test_put_update(self):
        """ Тест проверяющий обновление статуса заказа """

        url = reverse("order-detail", kwargs={'pk': self.order.pk})
        data = {"status": "delivered"}
        request = self.factory.put(url, data, format="json")
        force_authenticate(request, user=self.user)
        view = OrderDetailView.as_view()
        response = view(request, pk=self.order.pk)  # передаем pk в метод update
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.order.refresh_from_db()  # Обновляем order из БД
        self.assertEqual(self.order.status, "delivered")

    def test_delete_destroy(self):
        """ Тест проверяющий удаление конкретного заказа """

        url = reverse("order-detail", kwargs={'pk': self.order.pk})
        request = self.factory.delete(url)  # создаем DELETE запрос
        force_authenticate(request, user=self.user)
        view = OrderDetailView.as_view()
        response = view(request, pk=self.order.pk)  # передаем pk в destroy
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)  # check code
        self.assertEqual(Order.objects.count(), 0)  # проверяем, что объект удален
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIRequestFactory, force_authenticate
from rest_framework import status

from orders.models import Order, OrderItem
from .views import OrdersListView
from products.models import Product

User = get_user_model()


class OrderListAndDetailViewTests(TestCase):
    """ Тесты для представления списка всех заказов для админа """

    def setUp(self):
        self.factory = APIRequestFactory()
        # Создаем и сохраняем пользователя
        self.user = User.objects.create_user(
            email='example@mail.ru',
            username='Tested',
            first_name='Andrey',
            last_name='Diatlov',
            password='testpassword123',
            is_staff=True
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
        """ Тест проверяющий получение списка всех заказов """

        url = reverse("order-admin")  # Получаем url для списка
        request = self.factory.get(url)
        view = OrdersListView.as_view()
        force_authenticate(request, user=self.user)
        response = view(request)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)  # Проверяем, что вернулcя 1 заказ
        # Проверяем, что вернули заказ с правильным статусом
        self.assertEqual(response.data[0]['status'], self.order.status)

from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIRequestFactory
from rest_framework import status

from .models import Product
from .views import ProductListView, ProductDetailView


class ProductModelTests(TestCase):
    """    Тест модели каталога    """

    def setUp(self):
        self.product = Product(
            name='Phone',
            description='Инструмент для мобильной связи',
            price=5000.99,
            stock=100,
            category='electronics'
        )

    def test_create_product(self):
        """ Тест для проверки корректного создания экземпляра модели Product """

        self.assertIsInstance(self.product, Product)

    def test_str_representation(self):
        """ Тест для проверки строкового представления объекта модели Product """

        self.assertEqual(str(self.product), "Название: Phone, Количество: 100, Цена: 5000.99.")

    def test_saving_and_retrieving_book(self):
        """ Тест проверяющий сохранение объектов и доступ к ним """

        first_product = Product()
        first_product.name = 'Phone'
        first_product.description = 'Инструмент для мобильной связи'
        first_product.price = 5000.99
        first_product.stock = 100
        first_product.category = 'electronics'
        first_product.save()

        second_product = Product()
        second_product.name = 'Computer'
        second_product.description = 'Персональный компьютер'
        second_product.price = 10000.00
        second_product.stock = 50
        second_product.category = 'electronics'
        second_product.save()

        saved_products = Product.objects.all()
        self.assertEqual(saved_products.count(), 2)  # проверяем кол-во созданных объектов

        first_saved_product = saved_products[0]
        second_saved_product = saved_products[1]
        self.assertEqual(first_saved_product.name, 'Computer')  # проверяем атрибуты каждого объекта
        self.assertEqual(second_saved_product.stock, 100)


class ProductListAndDetailViewTests(TestCase):
    """ Тесты для представления списка продуктов """

    def setUp(self):
        self.factory = APIRequestFactory()
        self.product1 = Product.objects.create(name='Phone',
                                               description='Инструмент для мобильной связи',
                                               price=5000.99,
                                               stock=100,
                                               category='electronics')
        self.product2 = Product.objects.create(name='Computer',
                                               description='Персональный компьютер',
                                               price=10000.00,
                                               stock=50,
                                               category='electronics')

    def test_get_list(self):
        """ Тест проверяющий получение списка всех продуктов """

        url = reverse("product-list")  # Получаем url для списка
        request = self.factory.get(url)
        view = ProductListView.as_view()
        response = view(request)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)  # Проверяем, что вернулись 2 продукта
        # Проверяем, что вернули правильные продукты
        self.assertEqual(response.data[0]['name'], 'Computer')
        self.assertEqual(response.data[1]['name'], 'Phone')

    def test_product_create(self):
        """ Тест проверяющий создание продукта """

        url = reverse("product-list")  # получаем url для списка
        data = {"name": "Playstation", "description": "Console for video-games", "price": "10000.00",
                "stock": "20", "category": "electronics"}
        request = self.factory.post(url, data, format="json")  # используем POST, с json данными
        view = ProductListView.as_view()
        response = view(request)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Product.objects.count(), 3)  # проверяем, что создался объект
        new_product = Product.objects.get(name='Playstation')  # получаем объект
        self.assertEqual(new_product.description, 'Console for video-games')  # проверяем описание

    def test_get_detail(self):
        """ Тест проверяющий получение информации по конкретному продукту """

        url = reverse("product-detail", kwargs={'pk': self.product1.pk})  # получаем url для detail
        request = self.factory.get(url)
        view = ProductDetailView.as_view()
        response = view(request, pk=self.product1.pk)
        self.assertEqual(response.status_code, status.HTTP_200_OK)  # Проверяем код ответа
        self.assertEqual(response.data['name'], "Phone")  # Проверяем имя и описание продукта
        self.assertEqual(response.data['description'], "Инструмент для мобильной связи")

    def test_put_update(self):
        """ Тест проверяющий обновление (допустимо частичное) конкретного продукта """

        url = reverse("product-detail", kwargs={'pk': self.product2.pk})
        data = {"name": "PC", "price": "15000.00"}
        request = self.factory.put(url, data, format="json")
        view = ProductDetailView.as_view()
        response = view(request, pk=self.product2.pk)  # передаем pk в метод update
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.product2.refresh_from_db()  # Обновляем product1 из БД
        self.assertEqual(self.product2.name, "PC")  # проверяем имя и цену
        self.assertEqual(self.product2.price, 15000.00)

    def test_delete_destroy(self):
        """ Тест проверяющий удаление конкретного продукта """

        url = reverse("product-detail", kwargs={'pk': self.product1.pk})
        request = self.factory.delete(url)  # создаем DELETE запрос
        view = ProductDetailView.as_view()
        response = view(request, pk=self.product1.pk)  # передаем pk в destroy
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)  # check code
        self.assertEqual(Product.objects.count(), 1)  # проверяем, что объект удален

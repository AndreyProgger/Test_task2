from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIRequestFactory
from rest_framework import status

from .models import User
from .views import LoginAPIView, RegisterAPIView


class UserModelTests(TestCase):
    """    Тест модели пользователя    """

    def setUp(self):
        self.user = User.objects.create_user(
            email='example@mail.ru',
            username='Tested',
            first_name='Andrey',
            last_name='Diatlov',
            patronymic='Olegovich',
            password='testpassword123'
        )

    def test_create_user(self):
        """ Тест для проверки корректного создания экземпляра модели User """

        self.assertIsInstance(self.user, User)

    def test_str_representation(self):
        """ Тест для проверки строкового представления объекта модели User """

        self.assertEqual(str(self.user), "Andrey Olegovich Diatlov")

    def test_saving_and_retrieving_user(self):
        """ Тест проверяющий сохранение объектов и доступ к ним """

        first_user = User()
        first_user.email = 'example1@mail.ru'
        first_user.username = 'Tested1'
        first_user.first_name = 'Andrey'
        first_user.last_name = 'Diatlov'
        first_user.patronymic = 'Olegovich'
        first_user.password = 'testpassword123'
        first_user.save()

        second_user = User()
        second_user.email = 'example2@mail.ru'
        second_user.username = 'Tested2'
        second_user.first_name = 'Andrey2'
        second_user.last_name = 'Diatlov2'
        second_user.patronymic = 'Olegovich2'
        second_user.password = 'testpassword1232'
        second_user.save()

        saved_users = User.objects.all()
        self.assertEqual(saved_users.count(), 3)  # проверяем кол-во созданных объектов

        first_saved_user = saved_users[1]
        second_saved_user = saved_users[2]
        self.assertEqual(first_saved_user.username, 'Tested1')  # проверяем атрибуты каждого объекта
        self.assertEqual(second_saved_user.first_name, 'Andrey2')


class LoginAndRegistrationViewTests(TestCase):
    """ Тесты для представления регистрации и входа """

    def setUp(self):
        self.factory = APIRequestFactory()
        self.user = User.objects.create_user(
            email='example@mail.ru',
            username='Tested',
            first_name='Andrey',
            last_name='Diatlov',
            patronymic='Olegovich',
            password='testpassword123'
        )

    def test_login(self):
        """ Тест проверяющий получение списка всех продуктов """

        url = reverse("login")  # Получаем url для списка
        data = {"email": "example@mail.ru", "password": "testpassword123", }
        request = self.factory.post(url, data, format="json")
        view = LoginAPIView.as_view()
        response = view(request)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_registration(self):
        """ Тест проверяющий регистрацию пользователя """

        url = reverse("registration")  # получаем url для списка
        data = {"email": "example2@mail.ru", "username": "Tested2", "first_name": "Andrey",
                "last_name": "Diatlov", "patronymic": "Olegovich", "password": "testpassword123",
                "password_confirm": "testpassword123"}
        request = self.factory.post(url, data, format="json")  # используем POST, с json данными
        view = RegisterAPIView.as_view()
        response = view(request)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)


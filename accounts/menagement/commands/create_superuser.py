# accounts/management/commands/create_superuser.py
import getpass
import re
from django.core.management.base import BaseCommand, CommandError
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model

User = get_user_model()


class Command(BaseCommand):
    help = 'Создаёт суперпользователя с валидацией данных через консоль'

    def validate_email(self, email):
        """Валидация email"""
        try:
            validate_email(email)
        except ValidationError:
            raise CommandError(f'Некорректный email адрес: {email}')

        if User.objects.filter(email=email).exists():
            raise CommandError(f'Пользователь с email {email} уже существует')
        return email

    def validate_username(self, username):
        """Валидация username"""
        if not username:
            raise CommandError('Username не может быть пустым')

        if not re.match(r'^[\w.@+-]+$', username):
            raise CommandError('Username содержит недопустимые символы')

        if User.objects.filter(username=username).exists():
            raise CommandError(f'Пользователь с username {username} уже существует')
        return username

    def validate_password(self, password, confirm_password):
        """Валидация пароля"""
        if not password:
            raise CommandError('Пароль не может быть пустым')

        if len(password) < 8:
            self.stdout.write(self.style.ERROR('Пароль должен содержать минимум 8 символов'))
            return None

        if password != confirm_password:
            raise CommandError('Пароли не совпадают')
        return password

    def handle(self, *args, **options):

        self.stdout.write(self.style.SUCCESS('\n=== Создание суперпользователя ===\n'))

        # Ввод email
        while True:
            email_input = input('Email: ').strip()
            email = self.validate_email(email_input)
            if email:
                break

        # Ввод username
        while True:
            username_input = input('Username: ').strip()
            username = self.validate_username(username_input)
            if username:
                break

            # Ввод имени
        first_name = input('Имя: ').strip()
        if not first_name:
            first_name = 'Admin'

        # Ввод фамилии
        last_name = input('Фамилия: ').strip()
        if not last_name:
            last_name = 'User'

        # Ввод отчества (опционально)
        patronymic = input('Отчество (опционально): ').strip()
        patronymic = patronymic if patronymic else None

        # Ввод пароля
        while True:
            password = getpass.getpass('Пароль (мин. 8 символов): ')
            confirm_password = getpass.getpass('Подтверждение пароля: ')
            valid_password = self.validate_password(password, confirm_password)
            if valid_password:
                password = valid_password
                break

        role = 'admin'

        try:
            user = User.objects.create_superuser(
                email=email,
                username=username,
                password=password,
                first_name=first_name,
                last_name=last_name,
                patronymic=patronymic if 'patronymic' in locals() else None,
                role=role
            )

            self.stdout.write(self.style.SUCCESS(
                f'\n Суперпользователь "{user.email}" успешно создан!'
            ))
            self.stdout.write(f'   Username: {user.username}')
            self.stdout.write(f'   Email: {user.email}')
            self.stdout.write(f'   Роль: {user.role}')

        except Exception as e:
            raise CommandError(f'Ошибка при создании суперпользователя: {e}')

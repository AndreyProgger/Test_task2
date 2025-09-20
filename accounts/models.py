from django.db import models
from django.contrib.auth.models import AbstractUser

from accounts.managers import CustomUserManager


class User(AbstractUser):
    """
    Представляет объект пользователя в БД

    Атрибуты:
        name (str): Имя товара
        description (str): Описание товара
        price (DecimalField): Цена товара
        stock (PositiveInteger): Количество товара на складе
        category (str): Категория товара
        created_at (DateTimeField): Время создания товара
        updated_at (DateTimeField): Время последнего обновления товара
    """

    email = models.EmailField(unique=True)
    patronymic = models.CharField(verbose_name="Patronymic", max_length=25, null=True, default=None)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["first_name", "last_name", "username"]

    objects = CustomUserManager()

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.patronymic} {self.last_name}"

    def __str__(self) -> str:
        return self.full_name

    def has_perm(self, perm, obj=None):
        return True

    def has_module_perms(self, app_label):
        return True

    @property
    def is_superuser(self):
        return self.is_staff

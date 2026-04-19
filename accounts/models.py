from django.db import models
from django.contrib.auth.models import AbstractUser

from accounts.managers import CustomUserManager


class User(AbstractUser):
    """
    Представляет объект пользователя в БД
    """
    ROLE_CHOICES = [
        ('user', 'Обычный пользователь'),
        ('seller', 'Продавец'),
        ('admin', 'Администратор'),
    ]

    role = models.CharField(max_length=6, choices=ROLE_CHOICES, default='user')
    email = models.EmailField(unique=True)
    patronymic = models.CharField(verbose_name="Patronymic", max_length=25, null=True, default=None)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["first_name", "last_name", "username", "role"]

    objects = CustomUserManager()

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.patronymic} {self.last_name}"

    def __str__(self) -> str:
        return self.full_name + ' ' + self.role

    def has_perm(self, perm, obj=None):
        return True

    def has_module_perms(self, app_label):
        return True

    @property
    def is_superuser(self):
        return self.is_staff


class Profile(models.Model):
    """
    Расширенный профиль пользователя.
    Создаётся автоматически при создании User.
    """
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='profile'
    )
    patronymic = models.CharField(
        verbose_name="Отчество",
        max_length=25,
        blank=True,
        null=True,
        default=None
    )
    avatar = models.ImageField(
        upload_to='avatars/',
        blank=True,
        null=True,
        verbose_name="Аватар"
    )
    bio = models.TextField(
        max_length=500,
        blank=True,
        verbose_name="О себе"
    )
    phone = models.CharField(
        max_length=15,
        blank=True,
        verbose_name="Телефон"
    )
    birth_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="Дата рождения"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Профиль"
        verbose_name_plural = "Профили"

    def __str__(self):
        return f"Профиль пользователя {self.user.email}"
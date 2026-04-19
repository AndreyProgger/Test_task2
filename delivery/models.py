from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError


class Address(models.Model):
    """
    Представляет объект товара в магазине
    Атрибуты:
        user (link): Пользователь которому принадлежит адрес
        city (str): Город
        street  (str): Улица
        house (str): Дом
        apartment (str): Квартира
        postal_code (str): Почтовый код
        is_default (bool): Флаг является ли адрес адресом по умолчанию
        created_at (DateTimeField): Время создания адреса
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='addresses',
        verbose_name='User'
    )
    city = models.CharField(max_length=100, verbose_name='City')
    street = models.CharField(max_length=150, verbose_name='Street')
    house = models.CharField(max_length=20, verbose_name='House')
    apartment = models.CharField(max_length=20, blank=True, null=True, verbose_name='Apartment')
    postal_code = models.CharField(max_length=20, verbose_name='Post code')
    is_default = models.BooleanField(default=False, verbose_name='Default address')
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата создания'
    )

    class Meta:
        verbose_name = 'Address to delivery'
        verbose_name_plural = 'Addresses to delivery'
        ordering = ['-is_default', 'city', 'street']

    def __str__(self):
        apt = f', кв. {self.apartment}' if self.apartment else ''
        return f'{self.city}, {self.street}, {self.house}{apt}'

    # Добавляем валидацию на уровне БД чтобы исключить недопустимые данные при прямом добавлении в бд
    def save(self, *args, **kwargs):
        # Если текущий адрес устанавливается как default, сбрасываем default у других адресов пользователя
        if self.is_default:
            Address.objects.filter(user=self.user, is_default=True).exclude(pk=self.pk).update(is_default=False)
        super().save(*args, **kwargs)

    def clean(self):
        # Проверка: нельзя сделать адрес по умолчанию, если у пользователя уже есть другой адрес по умолчанию
        # (это дополнительная проверка, хотя save уже обрабатывает)
        if self.is_default and Address.objects.filter(user=self.user, is_default=True).exclude(pk=self.pk).exists():
            raise ValidationError('У пользователя уже есть адрес по умолчанию. Сначала снимите флаг с него.')

    def delete(self, *args, **kwargs):
        # Если удаляем адрес по умолчанию, нужно назначить другой адрес по умолчанию (если есть)
        if self.is_default:
            next_address = Address.objects.filter(user=self.user).exclude(pk=self.pk).first()
            if next_address:
                next_address.is_default = True
                next_address.save(update_fields=['is_default'])
        super().delete(*args, **kwargs)

    @property
    def owner(self):
        return self.user
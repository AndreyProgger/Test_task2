from rest_framework import serializers
from .models import Address


class AddressSerializer(serializers.ModelSerializer):
    """Сериализатор для модели Address"""

    class Meta:
        model = Address
        fields = ['id', 'user', 'city', 'street', 'house', 'apartment', 'postal_code', 'is_default']
        read_only_fields = ['id', 'user']

    def validate_is_default(self, value):
        """
        Если значение True, проверяем, что у пользователя ещё нет адреса по умолчанию
        (кроме текущего редактируемого адреса).
        """
        if value:
            user = self.context['request'].user
            existing_default = Address.objects.filter(user=user, is_default=True)
            if self.instance:
                existing_default = existing_default.exclude(pk=self.instance.pk)
            if existing_default.exists():
                raise serializers.ValidationError(
                    "У пользователя уже есть адрес по умолчанию. Сначала снимите флаг с него."
                )
        return value

    def create(self, validated_data):
        """При создании адреса с is_default=True снимаем флаг с других адресов пользователя."""
        if validated_data.get('is_default'):
            Address.objects.filter(user=validated_data['user'], is_default=True).update(is_default=False)
        return super().create(validated_data)

    def update(self, instance, validated_data):
        """При обновлении адреса с is_default=True снимаем флаг с других адресов пользователя."""
        if validated_data.get('is_default') and not instance.is_default:
            Address.objects.filter(user=instance.user, is_default=True).exclude(pk=instance.pk).update(is_default=False)
        return super().update(instance, validated_data)
from rest_framework import serializers
from .models import Product


class ProductSerializer(serializers.ModelSerializer):
    """ Модельный сериализатор для модели Product """

    class Meta:
        model = Product
        fields = '__all__'
        extra_kwargs = {
            'description': {'required': False},
            'created_at': {'read_only': True},
            'updated_at': {'read_only': True}
        }

    def validate_price(self, value):
        """ Валидатор положительной цены """
        if value <= 0:
            raise serializers.ValidationError("Цена должна быть положительной!")
        return value

    def validate_stock(self, value):
        """ Валидатор положительного количества на складе """
        if value <= 0:
            raise serializers.ValidationError("Количество на складе должно быть положительным!")
        return value

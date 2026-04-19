from rest_framework import serializers
from .models import Product, Category, ProductImage, PriceHistory


class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ['id', 'image_url', 'sort_order']


class ProductSerializer(serializers.ModelSerializer):
    """ Модельный сериализатор для модели Product """
    images = ProductImageSerializer(many=True, read_only=True)

    class Meta:
        model = Product
        fields = '__all__'
        extra_kwargs = {
            'seller': {'read_only': True},
            'description': {'required': False},
            'created_at': {'read_only': True},
            'updated_at': {'read_only': True}
        }

    def validate_price(self, value):
        """ Валидатор положительной цены """
        if value <= 0:
            raise serializers.ValidationError("Цена должна быть положительной!")
        return value

    def validate_discount_price(self, value):
        """ Валидатор: скидочная цена не может быть отрицательной """
        if value < 0:
            raise serializers.ValidationError("Цена со скидкой не может быть отрицательной!")
        return value

    def validate_stock(self, value):
        """ Валидатор положительного количества на складе """
        if value <= 0:
            raise serializers.ValidationError("Количество на складе должно быть положительным!")
        return value

    def validate(self, data):
        price = data.get('price')
        discount_price = data.get('discount_price')

        if price is not None and discount_price is not None and discount_price >= price:
            raise serializers.ValidationError("Цена со скидкой должна быть меньше обычной цены!")
        return data


class PriceHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = PriceHistory
        fields = ['price', 'created_at']
        extra_kwargs = {
            'created_at': {'read_only': True}
        }


class ProductDetailSerializer(ProductSerializer):
    """
    Сериализатор для детальной информации о продукте.
    Включает историю изменения цен и дополнительную информацию.
    """
    price_history = PriceHistorySerializer(many=True, read_only=True)

    class Meta(ProductSerializer.Meta):
        model = Product
        fields = [
            'id', 'name', 'slug', 'description', 'price', 'discount_price',
            'stock', 'category', 'seller', 'is_active', 'is_deleted',
            'created_at', 'updated_at', 'images',
            'price_history'
        ]
        read_only_fields = [
            'created_at',
            'price_history',
        ]
        extra_kwargs = {
            'discount_price': {'required': False}
        }


class CategorySerializer(serializers.ModelSerializer):
    """ Модельный сериализатор для модели Product """

    class Meta:
        model = Category
        fields = ['name', 'parent']
        extra_kwargs = {
            'parent': {'required': False},
            'is_active': {'read_only': True},
            'slug': {'read_only': True}
        }

    def validate_parent(self, value):
        """Проверяет, что родительская категория не имеет своего родителя (вложенность только 1 уровень)
         и нет самоссылки."""

        if value is None:
            return value

        # Запрещаем вложенность глубже 1 уровня
        if value.parent is not None:
            raise serializers.ValidationError(
                "Поддерживается только один уровень вложенности."
            )

        # Запрещаем делать категорию родителем самой себя (только при обновлении)
        if self.instance and value.pk == self.instance.pk:
            raise serializers.ValidationError("Нельзя назначить категорию родителем самой себе.")

        return value


class PriceHistorySerializer(serializers.ModelSerializer):
    """ Модельный сериализатор для модели PriceHistory """

    class Meta:
        model = PriceHistory
        fields = '__all__'
        extra_kwargs = {
            'created_at': {'read_only': True},
            'product': {'read_only': True}
        }



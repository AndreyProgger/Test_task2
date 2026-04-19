from rest_framework import serializers
from .models import CartItem, Cart


class CartItemSerializer(serializers.ModelSerializer):
    unit_price = serializers.DecimalField(source='product.price', max_digits=10, decimal_places=2, read_only=True)
    total_price = serializers.SerializerMethodField()

    class Meta:
        model = CartItem
        fields = ['id', 'product', 'quantity', 'unit_price', 'total_price']
        read_only_fields = ['id', 'unit_price', 'total_price']

    def get_total_price(self, obj):
        """Цена за единицу * количество"""
        return obj.product.price * obj.quantity


class AddCartItemSerializer(serializers.Serializer):
    product_id = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=1)


class EditCartItemSerializer(serializers.Serializer):
    quantity = serializers.IntegerField(min_value=1)


class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    total_price = serializers.SerializerMethodField()
    unique_items_count = serializers.SerializerMethodField()

    class Meta:
        model = Cart
        fields = ['id', 'user', 'items', 'total_price', 'unique_items_count']

    def get_total_price(self, obj):
        # Используем уже готовое свойство модели (или метод calculate_total)
        return obj.total_price

    def get_unique_items_count(self, obj):
        """Количество уникальных товаров (не сумма quantity, а число разных продуктов)"""
        return obj.items.count()
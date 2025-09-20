from rest_framework import serializers
from django.contrib.auth import get_user_model

from orders.models import OrderItem, Order

User = get_user_model()


class OrderItemCreateSerializer(serializers.Serializer):
    """ Промежуточный сериализатор для создания предметов в заказе """
    product_name = serializers.CharField()
    quantity = serializers.IntegerField(min_value=1)

    def validate_quantity(self, value):
        """ Валидатор положительного количества товара в заказе """
        if value <= 0:
            raise serializers.ValidationError("Количество товара должно быть положительным!")
        return value


class OrderItemSerializer(serializers.ModelSerializer):
    """ Промежуточный сериализатор для чтения предметов заказа """

    product_name = serializers.CharField(source='product.name')

    class Meta:
        model = OrderItem
        fields = ['quantity', 'price', 'product_name']
        read_only_fields = ['price', 'product_name']


class OrderSerializer(serializers.Serializer):
    """ Сериализатор для модели заказа """
    user = serializers.CharField(read_only=True)
    products = OrderItemCreateSerializer(write_only=True, many=True)
    items = OrderItemSerializer(many=True, read_only=True, source='items.all')
    status = serializers.ChoiceField(choices=[('pending', 'Ожидает обработки'),
                                              ('processing', 'В обработке'),
                                              ('shipped', 'Отправлен'),
                                              ('delivered', 'Доставлен'),
                                              ('cancelled', 'Отменен'), ], read_only=True)
    created_at = serializers.DateTimeField(read_only=True)
    total_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    def validate_total_price(self, value):
        """ Валидатор минимальной суммы заказа """
        if value < 1000:
            raise serializers.ValidationError("Минимальная сумма заказа 1000!")
        return value


class OrderUpdateSerializer(serializers.ModelSerializer):
    """Специальный сериализатор для обновления статуса заказа"""

    class Meta:
        model = Order
        fields = ['status']
        read_only_fields = ['user', 'created_at', 'products']

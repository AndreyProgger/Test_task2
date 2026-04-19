from rest_framework import serializers
from django.contrib.auth import get_user_model

from favorites.models import FavoriteItem
from orders.models import OrderItem

User = get_user_model()


class FavoriteItemSerializer(serializers.ModelSerializer):
    """ Промежуточный сериализатор для чтения предметов из избранного """

    product_name = serializers.CharField(source='product.name')

    class Meta:
        model = OrderItem
        fields = ['product_name']
        read_only_fields = ['product_name']


class FavoritesSerializer(serializers.Serializer):
    """ Сериализатор для модели избранного """
    user = serializers.CharField(read_only=True)
    items = FavoriteItemSerializer(many=True, read_only=True, source='items.all')
    created_at = serializers.DateTimeField(read_only=True)


class AddItemSerializer(serializers.ModelSerializer):
    """ Промежуточный сериализатор для добавления предметов в избранное """

    product_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = FavoriteItem
        fields = ['product_id']

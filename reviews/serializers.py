from rest_framework import serializers
from .models import Review


class ReviewSerializer(serializers.ModelSerializer):
    """ Модельный сериализатор для модели Review """

    user = serializers.StringRelatedField(read_only=True)
    product_name = serializers.CharField(source='product.name', read_only=True)

    class Meta:
        model = Review
        fields = ['id', 'product', 'product_name', 'user', 'rating', 'text', 'created_at']
        extra_kwargs = {
            'text': {'required': False},
            'created_at': {'read_only': True},
            'product': {'read_only': True},
            'user': {'read_only': True}
        }
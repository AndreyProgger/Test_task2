import logging

from rest_framework.pagination import LimitOffsetPagination
from rest_framework.request import Request
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.throttling import UserRateThrottle
from drf_spectacular.utils import extend_schema

from common.pagination import PAGINATION_PARAM_EXAMPLE
from products.utils import get_product
from .models import Favorite, FavoriteItem
from common.permissions import IsOwner
from .serializers import FavoritesSerializer, AddItemSerializer

tags = ["favorites"]

logger = logging.getLogger(__name__)
cache_logger = logging.getLogger('hit/miss_cache logger')


class FavoritesByUserListView(APIView):
    """ Представление выводящие список всех элементов из списка избранного пользователя """

    serializer_class = FavoritesSerializer
    permission_classes = [IsAuthenticated]
    throttle_classes = [UserRateThrottle]
    pagination_class = LimitOffsetPagination

    @extend_schema(
        summary="Retrieve all favorite products by user",
        description="""
                This endpoint allows to retrieve all favorite products for request user.
            """,
        tags=tags,
        parameters=PAGINATION_PARAM_EXAMPLE,
    )
    def get(self, request: Request) -> Response:
        favorites = Favorite.objects.prefetch_related('items__product').filter(user=request.user)
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(favorites, request, view=self)
        if page is not None:
            serializer = self.serializer_class(page, many=True)
            return paginator.get_paginated_response(serializer.data)
        serializer = self.serializer_class(favorites, many=True)
        logger.info(f'Пользователь: {request.user.username} успешно получил информацию о своих избранных товарах')
        return Response(serializer.data)

    @extend_schema(
        summary="Add new product in user's favorites",
        description="""
                This endpoint allows a authenticated user to add new order.
            """,
        tags=tags,
    )
    def post(self, request: Request) -> Response:
        favorite, created = Favorite.objects.get_or_create(user=request.user)
        serializer = AddItemSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        product_id = serializer.validated_data['product_id']

        if not product_id:
            return Response(
                {"error": "product_id is required"},
                status=400
            )

        product = get_product(product_id)

        # Проверяем, не добавлен ли уже товар в избранное
        if FavoriteItem.objects.filter(favorite=favorite, product=product, exist=True).exists():
            return Response(
                {"error": "Product already in favorites"},
                status=400
            )
        # Проверяем что пользователь не добавляет свой товар в избранное
        if product.seller == request.user:
            return Response(
                {"error": "You can add own product in favorites"},
                status=400
            )

        # Создаем запись в промежуточной модели
        favorite_item = FavoriteItem.objects.create(
            favorite=favorite,
            product=product,
            exist=True
        )

        logger.info(f'Пользователь {request.user.username} добавил товар {product.id} в избранное')

        return Response(
            serializer.data,
            status=201
        )


class FavoriteDetailView(APIView):
    serializer_class = FavoritesSerializer
    throttle_classes = [UserRateThrottle]
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Delete Product from favorites",
        description="""
            This endpoint allows a user to delete product from favorites.
        """,
        tags=tags,
    )
    def delete(self, request: Request, pk: int) -> Response:
        product = get_product(pk)
        try:
            favorite = Favorite.objects.get(user=request.user)
            product_item = FavoriteItem.objects.get(favorite=favorite, product=product)
            product_item.delete()
            logger.info(f'Пользователь: {request.user.username} успешно удалил товар № {product.pk} из избранного')
            return Response(status=204)
        except Favorite.DoesNotExist:
            return Response(
                {"error": "Product not in favorites"},
                status=404
            )
        except FavoriteItem.DoesNotExist:
            return Response(
                {"error": "Product not in favorites"},
                status=404
            )
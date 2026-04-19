import logging

from rest_framework.views import APIView
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.decorators import permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.throttling import UserRateThrottle, AnonRateThrottle
from drf_spectacular.utils import extend_schema

from common.pagination import PAGINATION_PARAM_EXAMPLE
from products.utils import get_product
from orders.models import Order
from .models import Review
from .serializers import ReviewSerializer

tags = ["reviews"]

logger = logging.getLogger(__name__)
cache_logger = logging.getLogger('hit/miss_cache logger')


class ReviewsView(APIView):
    """ Представление отвечающие за вывод списка продуктов и добавление в него новых """

    serializer_class = ReviewSerializer
    pagination_class = LimitOffsetPagination
    throttle_classes = [UserRateThrottle, AnonRateThrottle]

    def get_permissions(self):
        """Динамически назначаем permission классы в зависимости от метода"""
        if self.request.method == 'GET':
            return [AllowAny()]
        elif self.request.method == 'POST':
            return [IsAuthenticated()]
        return super().get_permissions()

    @extend_schema(
        summary="Retrieve all reviews about product",
        description="""
                This endpoint allows to retrieve all reviews about product.
            """,
        tags=tags,
        parameters=PAGINATION_PARAM_EXAMPLE,
    )
    def get(self, request: Request, pk: int) -> Response:
        product = get_product(pk)
        product_reviews = product.reviews.all()
        paginator = self.pagination_class()
        paginated_reviews = paginator.paginate_queryset(product_reviews, request, view=self)

        if paginated_reviews is not None:
            serializer = self.serializer_class(paginated_reviews, many=True)
            return paginator.get_paginated_response(serializer.data)

        serializer = self.serializer_class(product_reviews, many=True)
        logger.info(f'Пользователь успешно получил отзывы о товаре: {product.pk}')
        return Response(serializer.data)

    @extend_schema(
        summary="Create new category in shop",
        description="""
                This endpoint allows a admin2 user to add new category.
            """,
        tags=tags,
    )
    def post(self, request: Request, pk: int) -> Response:
        product = get_product(pk)
        if product.seller == request.user:
            return Response(
                {"error": "Нельзя оставить отзыв на свой товар"},
                status=400
            )
        has_completed_order = Order.objects.filter(
            items__product=product,
            user=request.user,
            status='completed'
        ).exists()
        if not has_completed_order:
            return Response(
                {"error": "Нельзя оставить отзыв на товар так как нет завершенных заказов с этим товаром"},
                status=400
            )
        if Review.objects.filter(product=product, user=request.user).exists():
            return Response(
                {"error": "Вы уже оставили отзыв на этот товар"},
                status=400
            )

        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            serializer.save(product=product, user=request.user)
            logger.info('Пользователь успешно добавил новый отзыв на товар')
            return Response(serializer.data, status=201)
        else:
            logger.warning('Ошибка при добавлении пользователем нового отзыва на товар')
            return Response(
                {'error': 'Неверные данные', 'details': serializer.errors},
                status=400
            )

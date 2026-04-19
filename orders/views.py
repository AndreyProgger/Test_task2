import logging

from django.db.models import Prefetch, Exists, OuterRef
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.request import Request
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.throttling import UserRateThrottle
from drf_spectacular.utils import extend_schema, OpenApiExample

from carts.models import Cart
from carts.services import CartService
from common.pagination import PAGINATION_PARAM_EXAMPLE
from .models import Order, OrderItem
from common.permissions import IsOwner, IsAdmin
from .serializers import OrderSerializer, StatusUpdateSerializer
from .schema_examples import ORDER_PARAM_EXAMPLE
from .filters import OrderFilter
from .services import OrderService
from .utils import get_order

tags = ["orders"]

logger = logging.getLogger(__name__)
cache_logger = logging.getLogger('hit/miss_cache logger')
status_logger = logging.getLogger('status_changes logger')

STATUS_MOVES = {
    'new': ('paid', 'cancelled'),
    'paid': ('in_delivery', 'cancelled'),
    'in_delivery': ('completed')
}


class OrderByUserListView(APIView):
    """ Представление выводящие список всех заказов сделанных пользователем """

    serializer_class = OrderSerializer
    throttle_classes = [UserRateThrottle]
    pagination_class = LimitOffsetPagination
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Retrieve all Order by user",
        description="""
                This endpoint allows to retrieve all orders for request user.
            """,
        tags=tags,
        parameters=ORDER_PARAM_EXAMPLE,
    )
    def get(self, request: Request) -> Response:
        if request.user.role == 'seller':
            seller_items = OrderItem.objects.filter(product__user=request.user).select_related('product')

            # Заказы, содержащие хотя бы один такой item
            orders = Order.objects.filter(
                Exists(seller_items.filter(order=OuterRef('pk')))
            )
            prefetch_items = Prefetch('items', queryset=seller_items)
            orders = orders.prefetch_related(prefetch_items)

            logger.info(f'Продавец: {request.user.username} успешно получил заказы со своими товарами')
        else:
            orders = Order.objects.filter(user=request.user).prefetch_related('items__product')
            logger.info(f'Пользователь: {request.user.username} успешно получил информацию о своих заказах')
        filterset = OrderFilter(request.query_params, queryset=orders)
        if not filterset.is_valid():
            return Response(filterset.errors, status=400)
        queryset = filterset.qs
        ordering = request.query_params.get('ordering', '-created_at')
        if ordering in ['created_at', '-created_at']:
            queryset = queryset.order_by(ordering)
        serializer = self.serializer_class(queryset, many=True)

        return Response(serializer.data)

    @extend_schema(
        summary="Create new order by user",
        description="""
                This endpoint allows a authenticated user to add new order.
            """,
        tags=tags,
        request=None,
    )
    def post(self, request: Request) -> Response:
        # Получаем корзину пользователя
        cart = get_object_or_404(Cart, user=request.user)

        # Создаем заказ через сервис
        order, errors = OrderService.create_order_from_cart(
            cart=cart,
            user=request.user,
            status='new'
        )

        if errors:
            logger.warning(
                f'Пользователь {request.user.username} не смог создать заказ. '
                f'Ошибки: {errors}'
            )
            return Response(
                {
                    'error': 'Невозможно создать заказ.',
                    'details': errors
                },
                status=400
            )

        # Очищаем корзину после успешного создания заказа
        CartService.clear_cart(request.user)

        logger.info(
            f'Пользователь {request.user.username} успешно создал заказ #{order.pk} '
            f'на сумму {order.total_price}'
        )

        serializer = self.serializer_class(order)
        return Response(serializer.data, status=201)


class OrderDetailView(APIView):
    serializer_class = OrderSerializer
    throttle_classes = [UserRateThrottle]
    permission_classes = [IsOwner, IsAuthenticated]

    @extend_schema(
        summary="Retrieve Order",
        description="""
                This endpoint allows an owner to get detail information about the order.
            """,
        tags=tags,
    )
    def get(self, request: Request, pk: int) -> Response:
        order = get_order(pk)
        self.check_object_permissions(request, order)
        serializer = self.serializer_class(order)
        logger.info(f'Пользователь: {request.user.username} успешно получил информацию о заказе № {order.pk}')
        return Response(serializer.data)

    @extend_schema(
        summary="Delete Order",
        description="""
                This endpoint allows a owner to delete order.
            """,
        tags=tags,
    )
    def delete(self, request: Request, pk: int) -> Response:
        order = get_order(pk)
        self.check_object_permissions(request, order)
        if order.status != 'cancelled':
            # так как уже возвращали при смене статуса
            OrderService.restore_stock_for_cancelled_order(order)
        order.delete()
        logger.info(f'Пользователь: {request.user.username} успешно удалил заказ № {order.pk}')
        return Response(status=204)


class StatusUpdateView(APIView):
    serializer_class = StatusUpdateSerializer
    throttle_classes = [UserRateThrottle]
    permission_classes = [IsAdmin, IsAuthenticated]

    @extend_schema(
        summary="Edit Order status",
        description="""
                    This endpoint allows a owner to edit order status.
                """,
        tags=tags,
        examples=[
            OpenApiExample(
                "Example request",
                value={"status": "new"},
                request_only=True
            )
        ]
    )
    def put(self, request: Request, pk: int) -> Response:
        order = get_order(pk)
        serializer = StatusUpdateSerializer(order, data=request.data)
        if serializer.is_valid():
            # Проверяем чтобы новые данные не повторяли уже существующие,
            # чтобы лишний раз не обращаться к БД (refresh_from_db())
            if serializer.validated_data.get('status') == order.status:
                return Response({'message': 'Данный статус заказа уже установлен'}, status=400)
            new_status = serializer.validated_data.get('status')
            if order.status in ('completed', 'cancelled'):
                return Response({'message': 'Нельзя изменить статус отмененного или выполненного заказа'}, status=400)
            status_moves = STATUS_MOVES[order.status]
            if new_status not in status_moves:
                return Response({'message': 'Не допустимый переход статуса'}, status=400)
            serializer.save()
            if new_status == 'cancelled':
                # Если заказ отменен возвращаем товары на склад
                OrderService.restore_stock_for_cancelled_order(order)
                order.delete()
                return Response({'message': 'Заказ отменён, товары возвращены на склад'}, status=200)
            order.refresh_from_db()
            full_serializer = self.serializer_class(order)
            # Сохраняем изменения статусов заказа в специальный log файл
            status_logger.info(f'Статус заказа: {order.pk} пользователя {order.user} был успешно изменен на '
                               f'{order.status} в {timezone.now().strftime("%Y-%m-%d %H:%M:%S %Z")}')
            logger.info(f'Пользователь: {request.user.username} успешно обновил информацию о статусе заказа № {order.pk}')
            return Response(full_serializer.data, status=200)
        logger.warning(f'Ошибка при обновлении информации о статусе заказа № {order.pk}')
        return Response({'message': 'Отсутствуют данные или они некорректны'}, status=400)
from django.db import transaction
from rest_framework.views import APIView
from rest_framework.response import Response
from django.http import Http404
from rest_framework.decorators import permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.throttling import UserRateThrottle
from drf_spectacular.utils import extend_schema, OpenApiExample
from django.core.cache import cache

from products.models import Product
from .models import Order, OrderItem
from common.permissions import IsOwner, IsAdmin
from .serializers import OrderSerializer, OrderUpdateSerializer
from .tasks import call_remote_api

tags = ["orders"]


class OrderByUserListView(APIView):
    """ Представление выводящие список всех заказов сделанных пользователем """

    serializer_class = OrderSerializer
    permission_class = IsAuthenticated
    throttle_classes = [UserRateThrottle]

    @extend_schema(
        summary="Retrieve all Order by user",
        description="""
                This endpoint allows to retrieve all orders for request user.
            """,
        tags=tags,
    )
    def get(self, request):
        orders = Order.objects.prefetch_related('items__product').filter(user=request.user)
        serializer = self.serializer_class(orders, many=True)
        return Response(serializer.data)

    @extend_schema(
        summary="Create new order by user",
        description="""
                This endpoint allows a authenticated user to add new order.
            """,
        tags=tags,
    )
    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            validated_data = serializer.validated_data
            with transaction.atomic():
                # Создаем заказ
                order = Order.objects.create(
                    user=request.user,
                    status=serializer.validated_data.get('status', 'pending')
                )
                products_data = validated_data.pop('products')
                products_count = 0  # счетчик проверяющий наличие хотя бы одного релевантного товара
                # Обрабатываем каждый продукт
                for product_data in products_data:
                    try:
                        product = Product.objects.select_for_update().get(name__iexact=product_data['product_name'])
                        quantity = product_data['quantity']

                        # Проверяем наличие
                        if product.stock < quantity:
                            return Response(
                                {'error': f'Недостаточно товара {product.name} в наличии'},
                                status=400
                            )

                        order_item = OrderItem.objects.create(
                            order=order,
                            product=product,
                            quantity=quantity,
                            price=product.price * quantity
                        )
                        order_item.save()
                        # Обновляем склад
                        product.stock -= quantity
                        product.save()
                        products_count += 1  # если товар существует и добавляем его к общему количеству

                    # Если пользователь добавил не существующий товар, просто пропускаем его, выкидывая из корзины
                    except Product.DoesNotExist:
                        continue
                if products_count == 0:
                    return Response(
                        {'error': 'В заказе не нашлось ни одного товара, который есть в наличии'},
                        status=400
                    )
                order.save()
                response_serializer = self.serializer_class(order)
                return Response(response_serializer.data, status=201)
        else:
            return Response(
                {'error': 'Неверные данные', 'details': serializer.errors},
                status=400
            )


class OrderDetailView(APIView):
    serializer_class = OrderSerializer
    throttle_classes = [UserRateThrottle]

    def get_object(self, pk):
        """ Вспомогательная функция для получения объекта по pk """
        try:
            cache_key = f'cached_order_{pk}'
            return cache.get_or_set(cache_key, Order.objects.prefetch_related('items__product').get(pk=pk), 60)
        except Order.DoesNotExist:
            raise Http404

    @extend_schema(
        summary="Retrieve Order",
        description="""
                This endpoint allows an owner or admin to get detail information about the order.
            """,
        tags=tags,
    )
    @permission_classes([IsOwner, IsAdmin])
    def get(self, request, pk):
        order = self.get_object(pk)
        serializer = self.serializer_class(order)
        return Response(serializer.data)

    @extend_schema(
        summary="Edit Order status",
        description="""
                This endpoint allows a owner to edit order status.
            """,
        tags=tags,
        request=OrderUpdateSerializer,  # Явно указываем сериализатор для запроса
        examples=[
            OpenApiExample(
                "Example request",
                value={"status": "shipped"},
                request_only=True
            )
        ]
    )
    @permission_classes([IsOwner, IsAdmin])
    def put(self, request, pk):
        order = self.get_object(pk)
        # Используем специальный сериализатор чтобы после создания заказа можно было обновить только статус
        serializer = OrderUpdateSerializer(order, data=request.data)
        if serializer.is_valid():
            # Проверяем чтобы новые данные не повторяли уже существующие,
            # чтобы лишний раз не обращаться к БД (refresh_from_db())
            if serializer.validated_data.get('status') == order.status:
                return Response({'message: Данный статус заказа уже установлен'}, status=400)
            serializer.save()
            if serializer.validated_data.get('status') == 'shipped':
                call_remote_api.delay('https://jsonplaceholder.typicode.com/users', 'api_cache')
            order.refresh_from_db()
            full_serializer = self.serializer_class(order)
            return Response(full_serializer.data, status=200)
        return Response({'message': 'Отсутствуют данные или они некорректны'}, status=400)

    @extend_schema(
        summary="Delete Order",
        description="""
                This endpoint allows a owner or admin2 to delete order.
            """,
        tags=tags,
    )
    @permission_classes([IsOwner, IsAdmin])
    def delete(self, request, pk):
        order = self.get_object(pk)
        # Проверяем возможность отмены заказа и возвращение товаров на склад
        if order.status in ('shipped', 'delivered'):
            return Response({'message': 'Заказ не может быть удален, так как уже произошла отправка'}, status=400)
        # Транзакция возвращающая все товары на склад с последующим удалением заказа
        with transaction.atomic():
            order_detail = Order.objects.prefetch_related('items__product').get(pk=order.pk)
            for item in order_detail.items.all():
                product = Product.objects.select_for_update().get(id=item.product.id)
                # Возвращаем количество каждого товара в заказе на баланс склада
                product.stock += item.quantity
                product.save()
            order.delete()
        return Response(status=204)

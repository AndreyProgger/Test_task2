import logging

from rest_framework.pagination import LimitOffsetPagination
from rest_framework.request import Request
from rest_framework.views import APIView
from rest_framework.response import Response
from django.http import Http404
from rest_framework.throttling import UserRateThrottle
from drf_spectacular.utils import extend_schema

from common.pagination import PAGINATION_PARAM_EXAMPLE
from products.utils import get_product
from .models import Cart, CartItem
from .serializers import CartSerializer, CartItemSerializer, AddCartItemSerializer, EditCartItemSerializer
from common.permissions import IsOwner
from rest_framework.permissions import IsAuthenticated
from .services import CartService

tags = ["carts"]
logger = logging.getLogger(__name__)


class CartClearView(APIView):
    throttle_classes = [UserRateThrottle]
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Delete all products from cart",
        description="This endpoint allows an owner to clear the cart.",
        tags=tags,
    )
    def delete(self, request: Request) -> Response:
        success = CartService.clear_cart(request.user)
        if success:
            logger.info(f'Пользователь: {request.user.username} очистил корзину.')
            return Response(status=204)
        else:
            raise Http404("Корзина не найдена")


class CartByUserListView(APIView):

    serializer_class = CartSerializer
    permission_classes = [IsAuthenticated]
    throttle_classes = [UserRateThrottle]
    pagination_class = LimitOffsetPagination

    @extend_schema(
        summary="Retrieve all products from cart by user",
        description="""
                This endpoint allows to retrieve all products from cart for request user.
            """,
        tags=tags,
        parameters=PAGINATION_PARAM_EXAMPLE,
    )
    def get(self, request: Request) -> Response:

        cart = Cart.objects.prefetch_related(
            'items__product'
        ).get(user=request.user)
        serializer = self.serializer_class(cart)
        logger.info(f'Пользователь: {request.user.username} успешно получил информацию о своей корзине')
        return Response(serializer.data)

    @extend_schema(
        summary="Create new order by user",
        description="""
                This endpoint allows a authenticated user to add new order.
            """,
        tags=tags,
    )
    def post(self, request: Request) -> Response:

        input_serializer = AddCartItemSerializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)

        product_id = input_serializer.validated_data['product_id']
        quantity = input_serializer.validated_data['quantity']

        if not product_id:
            return Response(
                {'error': 'product_id is required'},
                status=400
            )

        try:
            quantity = int(quantity)
            if quantity <= 0:
                raise ValueError
        except (TypeError, ValueError):
            return Response(
                {'error': 'quantity must be a positive integer'},
                status=400
            )

        product = get_product(product_id)

        cart, _ = Cart.objects.get_or_create(user=request.user)

        if quantity > product.stock:
            return Response(
                {'error': 'Нельзя добавить в корзину больше товаров чем на складе'},
                status=400
            )

        if product.seller == request.user:
            return Response(
                {'error': 'Нельзя добавить в корзину свой товар'},
                status=400
            )

        if not product.is_active:
            return Response(
                {'error': 'Нельзя добавить в корзину неактивный товар'},
                status=400
            )

        # Добавляем товар (или обновляем количество)
        cart_item, created = CartItem.objects.get_or_create(
            cart=cart,
            product=product,
            defaults={
                'quantity': quantity,
                'price': product.price
            }
        )

        if not created:
            cart_item.quantity += quantity
            cart_item.save()

        output_serializer = CartItemSerializer(cart_item)
        data = output_serializer.data

        return Response(
            data,
            status=201 if created else 200
        )


class CartItemView(APIView):
    """ Представление отвечающие за работу с конкретной категорией """

    serializer_class = EditCartItemSerializer
    throttle_classes = [UserRateThrottle]
    permission_classes = [IsAuthenticated, IsOwner]

    def get_object(self, pk: int) -> CartItem:
        """ Вспомогательная функция для получения объекта по pk """
        try:
            return CartItem.objects.get(pk=pk)
        except CartItem.DoesNotExist:
            raise Http404

    @extend_schema(
        summary="Edit CartItem",
        description="""
                This endpoint allows a user to edit the quality of cartItem.
            """,
        tags=tags,
    )
    def put(self, request: Request, pk: int) -> Response:
        cart_item = self.get_object(pk)
        self.check_object_permissions(request, cart_item)
        serializer = self.serializer_class(cart_item, data=request.data)
        if serializer.is_valid():
            cart_item.quantity += serializer.validated_data['quantity']
            cart_item.save()
            logger.info(f'Пользователь успешно обновил информацию о количестве товара: {cart_item.pk} в корзине')
            return Response(serializer.data)
        logger.warning(f'Ошибка при обновлении информации о количестве товара: {cart_item.pk} в корзине')
        return Response(serializer.errors, status=400)

    @extend_schema(
        summary="Delete CartItem",
        description="""
                This endpoint allows an user to delete cart item.
            """,
        tags=tags,
    )
    def delete(self, request: Request, pk: int) -> Response:
        cart_item = self.get_object(pk)
        self.check_object_permissions(request, cart_item)
        cart_item.delete()
        logger.info(f'Пользователь успешно удалил товар: {cart_item.pk} из корзины')
        return Response(status=204)
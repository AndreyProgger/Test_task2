from django.http import Http404
from django.core.cache import cache
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.throttling import UserRateThrottle, AnonRateThrottle
from drf_spectacular.utils import extend_schema

from .models import Product
from common.permissions import IsAdmin
from .serializers import ProductSerializer
from .filters import ProductFilter
from .schema_examples import PRODUCT_PARAM_EXAMPLE

tags = ["products"]


class ProductListView(APIView):
    """ Представление отвечающие за вывод списка продуктов и добавление в него новых """

    serializer_class = ProductSerializer
    pagination_class = LimitOffsetPagination
    throttle_classes = [UserRateThrottle, AnonRateThrottle]

    @extend_schema(
        summary="Retrieve all Products from shop",
        description="""
                This endpoint allows to retrieve all products.
            """,
        tags=tags,
        parameters=PRODUCT_PARAM_EXAMPLE,
    )
    @permission_classes([AllowAny])
    def get(self, request, *args, **kwargs):
        products = cache.get('cached_product_list')  # Пробуем получить из кэша, или кэшировать на 5 минут
        if products is None:
            products = Product.objects.all()
            cache.set('cached_product_list', list(products), 300)  # Кэшируем список
        filterset = ProductFilter(request.query_params, queryset=products)
        if filterset.is_valid():
            queryset = filterset.qs
            paginator = self.pagination_class()
            paginated_queryset = paginator.paginate_queryset(queryset, request, view=self)
            if paginated_queryset:
                serializer = self.serializer_class(paginated_queryset, many=True)
                return paginator.get_paginated_response(serializer.data)
            serializer = ProductSerializer(queryset, many=True)
            return Response(serializer.data)
        else:
            return Response(filterset.errors, status=400)

    @extend_schema(
        summary="Create new product in blog",
        description="""
                This endpoint allows a admin2 user to add new product.
            """,
        tags=tags,
    )
    @permission_classes([IsAdmin])
    def post(self, request):
        serializer = self.serializer_class(data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=201)
        else:
            return Response(
                {'error': 'Неверные данные', 'details': serializer.errors},
                status=400
            )


class ProductDetailView(APIView):
    """ Представление отвечающие за работу с конкретным продуктом """

    serializer_class = ProductSerializer
    throttle_classes = [UserRateThrottle]

    def get_object(self, pk):
        """ Вспомогательная функция для получения объекта по pk """
        # Сначала ищем объект в кэшированном списке
        products = cache.get('cached_product_list')
        if products:
            # Ищем продукт в кэшированном словаре
            product = products.get(pk)
            if product:
                return product
        try:
            return Product.objects.get(pk=pk)
        except Product.DoesNotExist:
            raise Http404

    @extend_schema(
        summary="Retrieve Product",
        description="""
                This endpoint allows an authenticated user to get detail information about the product.
            """,
        tags=tags,
    )
    @permission_classes([IsAuthenticated])
    def get(self, request, pk):
        product = self.get_object(pk)
        serializer = self.serializer_class(product)
        return Response(serializer.data)

    @extend_schema(
        summary="Edit Product",
        description="""
                This endpoint allows a admin2 to edit the product.
            """,
        tags=tags,
    )
    @permission_classes([IsAdmin])
    def put(self, request, pk):
        product = self.get_object(pk)
        # намеренно добавил частичное обновление, так как может измениться только цена или кол-во на складе
        serializer = self.serializer_class(product, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=400)

    @extend_schema(
        summary="Delete Product",
        description="""
                This endpoint allows an admin2 to delete product.
            """,
        tags=tags,
    )
    @permission_classes([IsAdmin])
    def delete(self, request, pk):
        product = self.get_object(pk)
        product.delete()
        return Response(status=204)

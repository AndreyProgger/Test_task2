import logging

from django.core.cache import cache
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.request import Request
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.throttling import UserRateThrottle, AnonRateThrottle
from drf_spectacular.utils import extend_schema

from common.pagination import PAGINATION_PARAM_EXAMPLE
from .models import Product, Category
from common.permissions import IsAdmin, IsSeller, IsOwner
from .serializers import ProductSerializer, CategorySerializer, ProductDetailSerializer
from .filters import ProductFilter
from .schema_examples import PRODUCT_PARAM_EXAMPLE
from .utils import get_product, get_category

tags = ["products"]

logger = logging.getLogger(__name__)
cache_logger = logging.getLogger('hit/miss_cache logger')


class ProductListView(APIView):
    """ Представление отвечающие за вывод списка продуктов и добавление в него новых """

    serializer_class = ProductSerializer
    pagination_class = LimitOffsetPagination
    throttle_classes = [UserRateThrottle, AnonRateThrottle]

    def get_permissions(self):
        """Динамически назначаем permission классы в зависимости от метода"""
        if self.request.method == 'GET':
            return [AllowAny()]
        elif self.request.method == 'POST':
            return [IsSeller()]
        return super().get_permissions()

    @extend_schema(
        summary="Retrieve all Products from shop",
        description="""
                This endpoint allows to retrieve all products.
            """,
        tags=tags,
        parameters=PRODUCT_PARAM_EXAMPLE,
    )
    def get(self, request: Request) -> Response:
        # Если есть параметры фильтрации или сортировки, не используем кэш
        has_filters = any(param in request.query_params for param in
                          ['category', 'seller', 'is_active', 'in_stock', 'min_price',
                           'max_price', 'search', 'ordering'])

        if has_filters:
            # Прямой запрос к БД с фильтрацией
            if request.user.is_authenticated and getattr(request.user, 'role', '') == 'admin':
                queryset = Product.objects.prefetch_related('images').all()
            else:
                # пользователям и продавцам показываем только доступные товары
                queryset = Product.available.prefetch_related('images').all()
            filterset = ProductFilter(request.query_params, queryset=queryset)
            if filterset.is_valid():
                filtered_qs = filterset.qs
                paginator = self.pagination_class()
                paginated_qs = paginator.paginate_queryset(filtered_qs, request, view=self)
                if paginated_qs is not None:
                    serializer = self.serializer_class(paginated_qs, many=True)
                    return paginator.get_paginated_response(serializer.data)
                serializer = self.serializer_class(filtered_qs, many=True)
                return Response(serializer.data)
            else:
                return Response(filterset.errors, status=400)
        else:
            if request.user.is_authenticated and getattr(request.user, 'role', '') == 'admin':
                products = Product.objects.prefetch_related('images').all()
                filterset = ProductFilter(request.query_params, queryset=products)
            else:
                products = cache.get('cached_product_list')  # Пробуем получить из кэша, или кэшировать на 5 минут
                if products is None:
                    products = Product.available.prefetch_related('images').all()
                    cache_logger.info('Get product list from bd (cache_miss)')
                    cache.set('cached_product_list', list(products), 300)  # Кэшируем список
                    filterset = ProductFilter(request.query_params, queryset=products)
                else:
                    cache_logger.info('Get product list from cache (cache_hit)')
                    # Если данные из кэша, создаем QuerySet из списка
                    product_ids = [product.id for product in products]
                    queryset_for_filter = Product.objects.filter(id__in=product_ids)
                    filterset = ProductFilter(request.query_params, queryset=queryset_for_filter)
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
                logger.debug('Ошибка при получении списка продуктов')
                return Response(filterset.errors, status=400)

    @extend_schema(
        summary="Create new product in shop",
        description="""
            This endpoint allows a seller to add a new product.
        """,
        tags=tags,
    )
    def post(self, request: Request) -> Response:
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            try:
                serializer.save(seller=request.user)
                logger.info('Продавец успешно добавил новый продукт')
                return Response(serializer.data, status=201)
            except ValidationError as e:
                # Перехватываем ошибки валидации модели (например, full_clean)
                logger.warning('Ошибка валидации модели при добавлении продукта')
                return Response(
                    {'error': 'Неверные данные'},
                    status=400
                )
        else:
            logger.warning('Ошибка при добавлении продукта: неверные данные')
            return Response(
                {'error': 'Неверные данные', 'details': serializer.errors},
                status=400
            )


class ProductDetailView(APIView):
    """ Представление отвечающие за работу с конкретным продуктом """

    serializer_class = ProductDetailSerializer
    throttle_classes = [UserRateThrottle]

    def get_permissions(self):
        """Динамически назначаем permission классы в зависимости от метода"""
        if self.request.method == 'GET':
            return [IsAuthenticated()]
        elif self.request.method in ['PUT', 'PATCH', 'DELETE']:
            return [IsAuthenticated(), IsOwner()]
        return super().get_permissions()

    @extend_schema(
        summary="Retrieve Product",
        description="""
                This endpoint allows an authenticated user to get detail information about the product.
            """,
        tags=tags,
    )
    def get(self, request: Request, pk: int) -> Response:
        product = get_product(pk)
        serializer = self.serializer_class(product)
        logger.info(f'Пользователь успешно получил информацию о товаре: {product.pk}')
        return Response(serializer.data)

    @extend_schema(
        summary="Edit Product",
        description="""
                This endpoint allows a admin2 to edit the product.
            """,
        tags=tags,
    )
    def put(self, request: Request, pk: int) -> Response:
        product = get_product(pk)
        self.check_object_permissions(request, product)
        # намеренно добавил частичное обновление, так как может измениться только цена или кол-во на складе
        serializer = ProductSerializer(product, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            logger.info(f'Администратор успешно обновил информацию о товаре: {product.pk}')
            return Response(serializer.data)
        logger.warning(f'Ошибка при обновлении информации о товаре: {product.pk}')
        return Response(serializer.errors, status=400)

    @extend_schema(
        summary="Delete Product",
        description="""
                This endpoint allows an admin2 to delete product.
            """,
        tags=tags,
    )
    def delete(self, request: Request, pk: int) -> Response:
        product = get_product(pk)
        self.check_object_permissions(request, product)
        product.is_deleted = True
        product.save()
        logger.info(f'Администратор или продавец успешно удалил информацию о товаре: {product.pk}')
        return Response(status=204)


class CategoryListView(APIView):
    """ Представление отвечающие за вывод списка продуктов и добавление в него новых """

    serializer_class = CategorySerializer
    pagination_class = LimitOffsetPagination
    throttle_classes = [UserRateThrottle, AnonRateThrottle]

    def get_permissions(self):
        """Динамически назначаем permission классы в зависимости от метода"""
        if self.request.method == 'GET':
            return [AllowAny()]
        elif self.request.method == 'POST':
            return [IsAdmin()]
        return super().get_permissions()

    @extend_schema(
        summary="Retrieve all Categories of products from shop",
        description="""
                This endpoint allows to retrieve all categories of products.
            """,
        tags=tags,
        parameters=PAGINATION_PARAM_EXAMPLE,
    )
    def get(self, request: Request) -> Response:
        categories = cache.get('cached_category_list')  # Пробуем получить из кэша, или кэшировать
        if categories is None:
            categories = Category.objects.all()
            cache_logger.info('Get categories list from bd (cache_miss)')
            # Поскольку категорий мало кэшируем их бессрочно
            cache.set('cached_category_list', list(categories), timeout=None)
            serializer = self.serializer_class(categories, many=True)
            return Response(serializer.data)
        else:
            cache_logger.info('Get product list from cache (cache_hit)')
            categories_ids = [category.id for category in categories]
            queryset = Category.objects.filter(id__in=categories_ids)
            # Применяем пагинацию
            paginator = self.pagination_class()
            paginated_queryset = paginator.paginate_queryset(queryset, request, view=self)
            if paginated_queryset:
                serializer = self.serializer_class(paginated_queryset, many=True)
                return paginator.get_paginated_response(serializer.data)
            # Если пагинация не используется
            serializer = self.serializer_class(queryset, many=True)
            return Response(serializer.data)

    @extend_schema(
        summary="Create new category in shop",
        description="""
                This endpoint allows a admin2 user to add new category.
            """,
        tags=tags,
    )
    def post(self, request: Request) -> Response:
        serializer = self.serializer_class(data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            logger.info('Администратор успешно добавил новую категорию')
            return Response(serializer.data, status=201)
        else:
            logger.warning('Ошибка при добавлении администратором новой категории')
            return Response(
                {'error': 'Неверные данные', 'details': serializer.errors},
                status=400
            )


class CategoryDetailView(APIView):
    """ Представление отвечающие за работу с конкретной категорией """

    serializer_class = CategorySerializer
    throttle_classes = [UserRateThrottle]

    def get_permissions(self):
        """Динамически назначаем permission классы в зависимости от метода"""
        if self.request.method == 'GET':
            return [IsAuthenticated()]
        elif self.request.method == 'POST':
            return [IsAdmin()]
        elif self.request.method == 'PUT':
            return [IsAdmin()]
        elif self.request.method == 'DELETE':
            return [IsAdmin()]
        return super().get_permissions()

    @extend_schema(
        summary="Retrieve Category",
        description="""
                This endpoint allows an authenticated user to get detail information about the category.
            """,
        tags=tags,
    )
    def get(self, request: Request, pk: int) -> Response:
        category = get_category(pk)
        serializer = self.serializer_class(category)
        logger.info(f'Пользователь успешно получил информацию о категории: {category.pk}')
        return Response(serializer.data)

    @extend_schema(
        summary="Edit Category",
        description="""
                This endpoint allows a admin2 to edit the category.
            """,
        tags=tags,
    )
    def put(self, request: Request, pk: int) -> Response:
        category = get_category(pk)
        serializer = self.serializer_class(category, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            logger.info(f'Администратор успешно обновил информацию о категории: {category.pk}')
            return Response(serializer.data)
        logger.warning(f'Ошибка при обновлении информации о категории: {category.pk}')
        return Response(serializer.errors, status=400)

    @extend_schema(
        summary="Delete Category",
        description="""
                This endpoint allows an admin2 to delete category.
            """,
        tags=tags,
    )
    def delete(self, request: Request, pk: int) -> Response:
        category = get_category(pk)
        # Проверка: есть ли товары, связанные с этой категорией
        if category.products.exists():
            logger.warning(
                f'Администратор {request.user.username} попытался удалить категорию {category.pk}, '
                f'но есть связанные товары'
            )
            return Response(
                {"error": f"Невозможно удалить категорию '{category.name}', так как к ней привязаны товары."},
                status=status.HTTP_400_BAD_REQUEST
            )
        category.delete()
        logger.info(f'Администратор успешно удалил информацию о категории: {category.pk}')
        return Response(status=204)

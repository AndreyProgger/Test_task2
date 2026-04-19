import logging

from django.http import Http404
from rest_framework.request import Request
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.throttling import UserRateThrottle, AnonRateThrottle
from drf_spectacular.utils import extend_schema

from common.pagination import PAGINATION_PARAM_EXAMPLE
from .models import Address
from common.permissions import IsOwner
from .serializers import AddressSerializer

tags = ["address"]

logger = logging.getLogger(__name__)


class AddressByUserListView(APIView):
    """ Представление отвечающие за вывод списка адресов конкретного пользователя """

    serializer_class = AddressSerializer
    pagination_class = LimitOffsetPagination
    throttle_classes = [UserRateThrottle, AnonRateThrottle]
    permission_classes = [IsAuthenticated]

    @extend_schema(
        summary="Retrieve all addresses from user",
        description="""
                This endpoint allows to retrieve all addresses from user.
            """,
        tags=tags,
        parameters=PAGINATION_PARAM_EXAMPLE,
    )
    def get(self, request: Request) -> Response:
        addresses = Address.objects.filter(user=request.user)
        paginator = self.pagination_class()
        paginated_addresses = paginator.paginate_queryset(addresses, request, view=self)
        serializer = self.serializer_class(paginated_addresses, many=True)
        logger.info(f'Пользователь: {request.user.username} успешно получил информацию о своих адресах')
        return Response(serializer.data)

    @extend_schema(
        summary="Create new address",
        description="""
                This endpoint allows an authenticated user to add new address.
            """,
        tags=tags,
    )
    def post(self, request: Request) -> Response:
        serializer = self.serializer_class(data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save(user=request.user)
            logger.info('Пользователь успешно добавил новый адрес')
            return Response(serializer.data, status=201)
        else:
            logger.warning('Ошибка при добавлении пользователем нового адреса')
            return Response(
                {'error': 'Неверные данные', 'details': serializer.errors},
                status=400
            )


class AddressDetailView(APIView):
    """ Представление отвечающие за работу с конкретным адресом """

    serializer_class = AddressSerializer
    throttle_classes = [UserRateThrottle]
    permission_classes = [IsOwner]

    def get_object(self, pk: int) -> Address:
        """ Вспомогательная функция для получения объекта по pk """
        try:
            return Address.objects.get(pk=pk)
        except Address.DoesNotExist:
            raise Http404

    @extend_schema(
        summary="Retrieve address",
        description="""
                This endpoint allows an authenticated user to get detail information about the address.
            """,
        tags=tags,
    )
    def get(self, request: Request, pk: int) -> Response:
        address = self.get_object(pk)
        self.check_object_permissions(request, address)
        serializer = self.serializer_class(address)
        logger.info(f'Пользователь успешно получил информацию об адресе: {address.pk}')
        return Response(serializer.data)

    @extend_schema(
        summary="Edit address",
        description="""
                This endpoint allows the owner to edit the address.
            """,
        tags=tags,
    )
    def put(self, request: Request, pk: int) -> Response:
        address = self.get_object(pk)
        self.check_object_permissions(request, address)
        serializer = self.serializer_class(address, data=request.data, context={'request': request}, partial=True)
        if serializer.is_valid():
            serializer.save()
            logger.info(f'Пользователь успешно обновил информацию о адресе: {address.pk}')
            return Response(serializer.data)
        logger.warning(f'Ошибка при обновлении информации о адресе: {address.pk}')
        return Response(serializer.errors, status=400)

    @extend_schema(
        summary="Delete address",
        description="""
                This endpoint allows an admin2 or owner to delete address.
            """,
        tags=tags,
    )
    def delete(self, request: Request, pk: int) -> Response:
        address = self.get_object(pk)
        self.check_object_permissions(request, address)
        address.delete()
        logger.info(f'Пользователь успешно удалил информацию о адресе: {address.pk}')
        return Response(status=204)

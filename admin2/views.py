from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle
from drf_spectacular.utils import extend_schema

from orders.models import Order
from common.permissions import IsAdmin
from orders.serializers import OrderSerializer
from .filters import OrderFilter
from .schema_examples import ORDERS_PARAM_EXAMPLE

tags = ["admin_orders"]


class OrdersListView(APIView):
    """ Представление для вывода всех заказов администратору """

    serializer_class = OrderSerializer
    permission_class = IsAdmin
    throttle_classes = [UserRateThrottle]

    @extend_schema(
        summary="Retrieve all Posts from blog",
        description="""
                This endpoint allows to retrieve all posts for every consumer.
            """,
        tags=tags,
        parameters=ORDERS_PARAM_EXAMPLE,
    )
    def get(self, request):
        orders = Order.objects.all()
        filterset = OrderFilter(request.query_params, queryset=orders)
        if filterset.is_valid():
            queryset = filterset.qs
            serializer = self.serializer_class(queryset, many=True)
            return Response(serializer.data)
        else:
            return Response(filterset.errors, status=400)

from drf_spectacular.utils import OpenApiParameter, OpenApiTypes

ORDERS_PARAM_EXAMPLE = [
    OpenApiParameter(
        name="status",
        description="Filter orders by status",
        required=False,
        type=OpenApiTypes.STR,
    ),
    OpenApiParameter(
        name="user",
        description="Filter orders by user, who makes order",
        required=False,
        type=OpenApiTypes.STR,
    ),
]

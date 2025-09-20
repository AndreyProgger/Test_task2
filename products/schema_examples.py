from drf_spectacular.utils import OpenApiParameter, OpenApiTypes

PRODUCT_PARAM_EXAMPLE = [
    OpenApiParameter(
        name="max_price",
        description="Filter products by MAX current price",
        required=False,
        type=OpenApiTypes.INT,
    ),
    OpenApiParameter(
        name="min_price",
        description="Filter products by MIN current price",
        required=False,
        type=OpenApiTypes.INT,
    ),
    OpenApiParameter(
        name="category",
        description="Filter products by category",
        required=False,
        type=OpenApiTypes.STR,
    ),
    OpenApiParameter(
        name="limit",
        description="Retrieve a starting number of elements",
        required=False,
        type=OpenApiTypes.INT,
    ),
    OpenApiParameter(
        name="offset",
        description="Retrieve a finish number of elements",
        required=False,
        type=OpenApiTypes.INT,
    ),
]

from drf_spectacular.utils import OpenApiParameter, OpenApiTypes

PRODUCT_PARAM_EXAMPLE = [
    OpenApiParameter(
        name="category",
        description="Filter by category slug (e.g., 'electronics')",
        required=False,
        type=OpenApiTypes.STR,
    ),
    OpenApiParameter(
        name="seller",
        description="Filter by seller user ID",
        required=False,
        type=OpenApiTypes.INT,
    ),
    OpenApiParameter(
        name="is_active",
        description="Filter by active status (true/false)",
        required=False,
        type=OpenApiTypes.BOOL,
    ),
    OpenApiParameter(
        name="in_stock",
        description="Filter products in stock (true = stock > 0)",
        required=False,
        type=OpenApiTypes.BOOL,
    ),
    OpenApiParameter(
        name="min_price",
        description="Minimum price filter",
        required=False,
        type=OpenApiTypes.INT,
    ),
    OpenApiParameter(
        name="max_price",
        description="Maximum price filter",
        required=False,
        type=OpenApiTypes.INT,
    ),
    OpenApiParameter(
        name="search",
        description="Search by name or description (case-insensitive)",
        required=False,
        type=OpenApiTypes.STR,
    ),
    OpenApiParameter(
        name="ordering",
        description="Sorting: 'price', '-price', 'created_at', '-created_at', 'rating', '-rating'",
        required=False,
        type=OpenApiTypes.STR,
    ),
    OpenApiParameter(
        name="limit",
        description="Number of results to return",
        required=False,
        type=OpenApiTypes.INT,
    ),
    OpenApiParameter(
        name="offset",
        description="The initial index from which to return the results",
        required=False,
        type=OpenApiTypes.INT,
    ),
]
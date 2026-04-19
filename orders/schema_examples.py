from drf_spectacular.utils import OpenApiParameter, OpenApiTypes

ORDER_PARAM_EXAMPLE = [
    OpenApiParameter(
        name="status",
        description="Filter by order status (e.g., 'pending', 'completed', 'cancelled')",
        required=False,
        type=OpenApiTypes.STR,
    ),

    OpenApiParameter(
        name="created_at_after",
        description="Filter orders created after this date (ISO format: YYYY-MM-DD)",
        required=False,
        type=OpenApiTypes.DATE,
    ),

    OpenApiParameter(
        name="created_at_before",
        description="Filter orders created before this date (ISO format: YYYY-MM-DD)",
        required=False,
        type=OpenApiTypes.DATE,
    ),

    OpenApiParameter(
        name="ordering",
        description="Sort by 'created_at' or '-created_at' (default: '-created_at')",
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

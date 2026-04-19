from drf_spectacular.utils import OpenApiParameter
from drf_spectacular.types import OpenApiTypes


PAGINATION_PARAM_EXAMPLE = [
    OpenApiParameter(
        name='limit',
        type=OpenApiTypes.INT,
        location=OpenApiParameter.QUERY,
        description='Number of results to return',
        required=False
    ),
    OpenApiParameter(
        name='offset',
        type=OpenApiTypes.INT,
        location=OpenApiParameter.QUERY,
        description='The initial index from which to return the results',
        required=False
    ),
]

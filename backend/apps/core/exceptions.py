"""API error contract shared by every view.

Every error response has the shape:
    { "error": "<CODE>", "detail": "<human readable>", "field": "<field or null>" }
"""

from rest_framework import status
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler


class DomainError(Exception):
    """Base for errors raised by the service layer that map onto the API error contract."""

    error_code = "ERROR"
    http_status = status.HTTP_400_BAD_REQUEST

    def __init__(self, detail, field=None):
        self.detail = detail
        self.field = field
        super().__init__(detail)


class GeocodingError(DomainError):
    error_code = "GEOCODING_FAILED"
    http_status = status.HTTP_400_BAD_REQUEST


class RoutingError(DomainError):
    error_code = "ROUTING_FAILED"
    http_status = status.HTTP_502_BAD_GATEWAY


class UpstreamTimeoutError(DomainError):
    error_code = "UPSTREAM_TIMEOUT"
    http_status = status.HTTP_504_GATEWAY_TIMEOUT


def eld_exception_handler(exc, context):
    if isinstance(exc, DomainError):
        return Response(
            {"error": exc.error_code, "detail": str(exc.detail), "field": exc.field},
            status=exc.http_status,
        )

    response = drf_exception_handler(exc, context)
    if response is not None and isinstance(exc, DRFValidationError):
        field, detail = _first_error(response.data)
        response.data = {"error": "VALIDATION_ERROR", "detail": detail, "field": field}
    return response


def _first_error(data):
    if isinstance(data, dict) and data:
        field, errors = next(iter(data.items()))
        field = None if field in ("non_field_errors", "__all__") else field
        if isinstance(errors, list) and errors:
            return field, str(errors[0])
        return field, str(errors)
    if isinstance(data, list) and data:
        return None, str(data[0])
    return None, str(data)

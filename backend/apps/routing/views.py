from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from .factory import get_geocoding_provider


class GeocodeResultSerializer(serializers.Serializer):
    label = serializers.CharField()
    lat = serializers.FloatField()
    lon = serializers.FloatField()


class GeocodeView(APIView):
    """GET /api/geocode/?q=... — typeahead proxy to the geocoding provider, cached."""

    @extend_schema(
        parameters=[OpenApiParameter("q", str, description="Free-text location query")],
        responses=GeocodeResultSerializer,
    )
    def get(self, request, *args, **kwargs):
        query = request.query_params.get("q", "").strip()
        if not query:
            return Response({"error": "VALIDATION_ERROR", "detail": "Query param 'q' is required.", "field": "q"}, status=400)

        result = get_geocoding_provider().geocode(query)
        return Response(GeocodeResultSerializer(result, context={"request": request}).data)

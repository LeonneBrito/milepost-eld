from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.generics import CreateAPIView, RetrieveAPIView
from rest_framework.response import Response

from apps.hos.exceptions import InvalidCycleHoursError, LogDayInvariantError, SimulationDidNotConverge

from .models import Trip
from .serializers import TripCreateSerializer, TripSerializer
from .services.planner import TripInput, TripPlanner


class TripCreateView(CreateAPIView):
    """POST /api/trips/ — plan a route + HOS schedule and persist it."""

    serializer_class = TripCreateSerializer

    @extend_schema(responses=TripSerializer)
    def post(self, request, *args, **kwargs):
        serializer = TripCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        trip_input = TripInput(
            current_location=data["current_location"],
            pickup_location=data["pickup_location"],
            dropoff_location=data["dropoff_location"],
            current_cycle_used_hours=data["current_cycle_used_hours"],
            start_datetime=data["start_datetime"],
            timezone=data["timezone"],
        )

        try:
            trip = TripPlanner().plan(trip_input)
        except InvalidCycleHoursError as exc:
            return Response(
                {"error": "VALIDATION_ERROR", "detail": str(exc), "field": "current_cycle_used_hours"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except (SimulationDidNotConverge, LogDayInvariantError) as exc:
            return Response(
                {"error": "SIMULATION_FAILED", "detail": str(exc), "field": None},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response(TripSerializer(trip).data, status=status.HTTP_201_CREATED)


class TripDetailView(RetrieveAPIView):
    """GET /api/trips/{id}/ — reload a previously planned trip."""

    queryset = Trip.objects.prefetch_related("stops", "logs__segments")
    serializer_class = TripSerializer
    lookup_field = "id"

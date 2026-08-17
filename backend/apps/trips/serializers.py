from datetime import datetime, timezone as dt_timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from .models import DutySegment, LogDay, Stop, Trip


class TripCreateSerializer(serializers.Serializer):
    current_location = serializers.CharField(max_length=255, allow_blank=False)
    pickup_location = serializers.CharField(max_length=255, allow_blank=False)
    dropoff_location = serializers.CharField(max_length=255, allow_blank=False)
    current_cycle_used_hours = serializers.DecimalField(max_digits=4, decimal_places=2, min_value=0)
    start_datetime = serializers.DateTimeField(required=False)
    timezone = serializers.CharField(max_length=64, required=False)

    def validate_current_cycle_used_hours(self, value):
        if value >= 70:
            raise serializers.ValidationError("current_cycle_used_hours must be less than 70.")
        return value

    def validate_timezone(self, value):
        try:
            ZoneInfo(value)
        except ZoneInfoNotFoundError as exc:
            raise serializers.ValidationError(f"Unknown timezone '{value}'.") from exc
        return value

    def validate(self, attrs):
        attrs.setdefault("start_datetime", datetime.now(dt_timezone.utc))
        attrs.setdefault("timezone", "America/Chicago")
        return attrs


class DutySegmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = DutySegment
        fields = ["status", "start_minute", "end_minute", "remark"]


class LogDayTotalsSerializer(serializers.Serializer):
    off_duty = serializers.FloatField()
    sleeper = serializers.FloatField()
    driving = serializers.FloatField()
    on_duty = serializers.FloatField()


class LogDaySerializer(serializers.ModelSerializer):
    segments = DutySegmentSerializer(many=True, read_only=True)
    totals = serializers.SerializerMethodField()

    class Meta:
        model = LogDay
        fields = ["date", "sequence", "total_miles_driving", "totals", "segments"]

    @extend_schema_field(LogDayTotalsSerializer)
    def get_totals(self, obj):
        return {
            "off_duty": obj.off_duty_hours,
            "sleeper": obj.sleeper_hours,
            "driving": obj.driving_hours,
            "on_duty": obj.on_duty_hours,
        }


class StopSerializer(serializers.ModelSerializer):
    class Meta:
        model = Stop
        fields = [
            "sequence",
            "kind",
            "label",
            "lat",
            "lon",
            "arrival",
            "departure",
            "duration_minutes",
            "distance_from_origin_miles",
        ]


class RouteSerializer(serializers.Serializer):
    geometry = serializers.JSONField()


class TripSummarySerializer(serializers.Serializer):
    total_distance_miles = serializers.FloatField()
    total_driving_hours = serializers.FloatField()
    total_duration_hours = serializers.FloatField()
    days = serializers.IntegerField()
    cycle_hours_remaining = serializers.FloatField()
    restart_required = serializers.BooleanField()


class TripSerializer(serializers.ModelSerializer):
    summary = serializers.SerializerMethodField()
    route = serializers.SerializerMethodField()
    stops = StopSerializer(many=True, read_only=True)
    logs = LogDaySerializer(many=True, read_only=True)

    class Meta:
        model = Trip
        fields = ["id", "summary", "route", "stops", "logs"]

    @extend_schema_field(RouteSerializer)
    def get_route(self, obj):
        return {"geometry": obj.route_geometry}

    @extend_schema_field(TripSummarySerializer)
    def get_summary(self, obj):
        logs = list(obj.logs.all())
        total_driving_hours = sum(day.driving_hours for day in logs)
        total_duration_hours = (obj.total_duration_minutes or 0) / 60
        return {
            "total_distance_miles": obj.total_distance_miles,
            "total_driving_hours": round(total_driving_hours, 2),
            "total_duration_hours": round(total_duration_hours, 2),
            "days": len(logs),
            "cycle_hours_remaining": obj.cycle_hours_remaining,
            "restart_required": obj.restart_required,
        }

import uuid

from django.db import models


class DutyStatus(models.TextChoices):
    OFF_DUTY = "OFF", "Off Duty"
    SLEEPER = "SB", "Sleeper Berth"
    DRIVING = "D", "Driving"
    ON_DUTY = "ON", "On Duty (Not Driving)"


class StopKind(models.TextChoices):
    START = "start", "Trip Start"
    PICKUP = "pickup", "Pickup"
    DROPOFF = "dropoff", "Dropoff"
    FUEL = "fuel", "Fuel Stop"
    BREAK_30 = "break_30", "30-Minute Break"
    REST_10 = "rest_10", "10-Hour Reset"
    RESTART_34 = "restart_34", "34-Hour Restart"


class Trip(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    current_location_text = models.CharField(max_length=255)
    current_lat = models.FloatField()
    current_lon = models.FloatField()

    pickup_location_text = models.CharField(max_length=255)
    pickup_lat = models.FloatField()
    pickup_lon = models.FloatField()

    dropoff_location_text = models.CharField(max_length=255)
    dropoff_lat = models.FloatField()
    dropoff_lon = models.FloatField()

    current_cycle_used_hours = models.DecimalField(max_digits=4, decimal_places=2)
    start_datetime = models.DateTimeField()
    timezone = models.CharField(max_length=64, default="America/Chicago")

    total_distance_miles = models.FloatField(null=True, blank=True)
    total_duration_minutes = models.IntegerField(null=True, blank=True)
    route_geometry = models.JSONField()  # GeoJSON LineString

    cycle_hours_remaining = models.FloatField(null=True, blank=True)
    restart_required = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.current_location_text} -> {self.pickup_location_text} -> {self.dropoff_location_text}"


class Stop(models.Model):
    trip = models.ForeignKey(Trip, related_name="stops", on_delete=models.CASCADE)
    sequence = models.PositiveIntegerField()
    kind = models.CharField(max_length=20, choices=StopKind.choices)
    label = models.CharField(max_length=255)
    lat = models.FloatField()
    lon = models.FloatField()
    arrival = models.DateTimeField()
    departure = models.DateTimeField()
    duration_minutes = models.IntegerField()
    distance_from_origin_miles = models.FloatField()

    class Meta:
        ordering = ["trip", "sequence"]
        constraints = [
            models.UniqueConstraint(fields=["trip", "sequence"], name="unique_stop_sequence_per_trip"),
        ]

    def __str__(self):
        return f"[{self.sequence}] {self.kind} — {self.label}"


class LogDay(models.Model):
    trip = models.ForeignKey(Trip, related_name="logs", on_delete=models.CASCADE)
    date = models.DateField()
    sequence = models.PositiveIntegerField()

    total_miles_driving = models.FloatField()
    off_duty_hours = models.FloatField()
    sleeper_hours = models.FloatField()
    driving_hours = models.FloatField()
    on_duty_hours = models.FloatField()

    class Meta:
        ordering = ["trip", "sequence"]
        constraints = [
            models.UniqueConstraint(fields=["trip", "sequence"], name="unique_log_day_sequence_per_trip"),
        ]

    def __str__(self):
        return f"Day {self.sequence} ({self.date})"


class DutySegment(models.Model):
    log_day = models.ForeignKey(LogDay, related_name="segments", on_delete=models.CASCADE)
    status = models.CharField(max_length=3, choices=DutyStatus.choices)
    start_minute = models.PositiveSmallIntegerField()  # 0..1440 from local midnight
    end_minute = models.PositiveSmallIntegerField()
    remark = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["log_day", "start_minute"]

    def __str__(self):
        return f"{self.status} {self.start_minute}-{self.end_minute}"

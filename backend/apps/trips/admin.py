from django.contrib import admin

from .models import DutySegment, LogDay, Stop, Trip


class StopInline(admin.TabularInline):
    model = Stop
    extra = 0
    ordering = ["sequence"]


class LogDayInline(admin.TabularInline):
    model = LogDay
    extra = 0
    ordering = ["sequence"]
    show_change_link = True


@admin.register(Trip)
class TripAdmin(admin.ModelAdmin):
    list_display = ["id", "current_location_text", "pickup_location_text", "dropoff_location_text", "created_at"]
    readonly_fields = ["id", "created_at"]
    inlines = [StopInline, LogDayInline]


class DutySegmentInline(admin.TabularInline):
    model = DutySegment
    extra = 0
    ordering = ["start_minute"]


@admin.register(LogDay)
class LogDayAdmin(admin.ModelAdmin):
    list_display = ["trip", "sequence", "date", "driving_hours"]
    inlines = [DutySegmentInline]


@admin.register(Stop)
class StopAdmin(admin.ModelAdmin):
    list_display = ["trip", "sequence", "kind", "label", "arrival"]

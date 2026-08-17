"""Orchestrates trip planning: geocode -> route -> HOS simulate -> build logs -> persist.

This is the only module that talks to both the I/O layer (apps/routing) and
the pure domain layer (apps/hos). Keeping it thin and pushing all regulatory
logic into apps/hos is what makes that logic unit-testable without a DB or
network — see apps/hos/engine.py and apps/hos/logsheet.py.
"""

import dataclasses
from datetime import datetime

from django.db import transaction

from apps.core.exceptions import RoutingError
from apps.hos import engine, logsheet, rules
from apps.hos.timeline import DutyStatus as HOSDutyStatus
from apps.hos.timeline import Event, EventKind, LegProfile
from apps.routing.base import Coord, GeocodingProvider, RoutingProvider
from apps.routing.factory import get_geocoding_provider, get_routing_provider

from ..models import DutySegment, LogDay, Stop, StopKind, Trip
from .geometry import build_mile_interpolator, nearest_label

_EVENT_KIND_TO_STOP_KIND = {
    EventKind.PICKUP: StopKind.PICKUP,
    EventKind.DROPOFF: StopKind.DROPOFF,
    EventKind.FUEL: StopKind.FUEL,
    EventKind.BREAK_30: StopKind.BREAK_30,
    EventKind.REST_10: StopKind.REST_10,
    EventKind.RESTART_34: StopKind.RESTART_34,
}
_LOCATIONLESS_KINDS = (EventKind.FUEL, EventKind.BREAK_30, EventKind.REST_10, EventKind.RESTART_34)


@dataclasses.dataclass
class TripInput:
    current_location: str
    pickup_location: str
    dropoff_location: str
    current_cycle_used_hours: float
    start_datetime: datetime
    timezone: str


class TripPlanner:
    def __init__(self, geocoder: GeocodingProvider = None, router: RoutingProvider = None):
        self.geocoder = geocoder or get_geocoding_provider()
        self.router = router or get_routing_provider()

    @transaction.atomic
    def plan(self, trip_input: TripInput) -> Trip:
        current = self.geocoder.geocode(trip_input.current_location)
        pickup = self.geocoder.geocode(trip_input.pickup_location)
        dropoff = self.geocoder.geocode(trip_input.dropoff_location)

        waypoints = [
            Coord(current.lat, current.lon),
            Coord(pickup.lat, pickup.lon),
            Coord(dropoff.lat, dropoff.lon),
        ]
        route = self.router.route(waypoints)
        if len(route.legs) != 2:
            raise RoutingError(
                f"Expected 2 route legs (current->pickup, pickup->dropoff), got {len(route.legs)}"
            )

        legs = [
            LegProfile("to_pickup", route.legs[0].distance_miles, route.legs[0].duration_minutes),
            LegProfile("to_dropoff", route.legs[1].distance_miles, route.legs[1].duration_minutes),
        ]
        cycle_used_minutes = float(trip_input.current_cycle_used_hours) * 60

        events = engine.simulate(
            legs=legs,
            start_datetime=trip_input.start_datetime,
            cycle_used_minutes=cycle_used_minutes,
            pickup_label=pickup.label,
            dropoff_label=dropoff.label,
            origin_label=current.label,
        )

        mile_to_coord = build_mile_interpolator(route.geometry, route.total_distance_miles)
        named_waypoints = [
            (current.label, current.lat, current.lon),
            (pickup.label, pickup.lat, pickup.lon),
            (dropoff.label, dropoff.lat, dropoff.lon),
        ]
        events = [self._augment_label(e, mile_to_coord, named_waypoints) for e in events]

        cycle_hours_remaining, restart_required = _final_cycle_state(events, cycle_used_minutes)
        total_duration_minutes = (events[-1].end - trip_input.start_datetime).total_seconds() / 60

        trip = Trip.objects.create(
            current_location_text=trip_input.current_location,
            current_lat=current.lat,
            current_lon=current.lon,
            pickup_location_text=trip_input.pickup_location,
            pickup_lat=pickup.lat,
            pickup_lon=pickup.lon,
            dropoff_location_text=trip_input.dropoff_location,
            dropoff_lat=dropoff.lat,
            dropoff_lon=dropoff.lon,
            current_cycle_used_hours=trip_input.current_cycle_used_hours,
            start_datetime=trip_input.start_datetime,
            timezone=trip_input.timezone,
            total_distance_miles=round(route.total_distance_miles, 1),
            total_duration_minutes=round(total_duration_minutes),
            route_geometry={"type": "LineString", "coordinates": [list(c) for c in route.geometry]},
            cycle_hours_remaining=round(cycle_hours_remaining, 2),
            restart_required=restart_required,
        )

        self._create_stops(trip, events, current, mile_to_coord)
        self._create_logs(trip, events, trip_input.timezone)

        return trip

    def _augment_label(self, event: Event, mile_to_coord, named_waypoints) -> Event:
        """Add a reverse-geocoded 'near City, ST' suffix to stops with no inherent location."""
        if event.kind not in _LOCATIONLESS_KINDS:
            return event

        lat, lon = mile_to_coord(event.start_mile)
        location = self.geocoder.reverse(lat, lon) or nearest_label(lat, lon, named_waypoints)
        if not location:
            return event
        return dataclasses.replace(event, label=f"{event.label} — near {location}")

    def _create_stops(self, trip: Trip, events: list[Event], current, mile_to_coord) -> None:
        Stop.objects.create(
            trip=trip,
            sequence=0,
            kind=StopKind.START,
            label=current.label,
            lat=current.lat,
            lon=current.lon,
            arrival=trip.start_datetime,
            departure=trip.start_datetime,
            duration_minutes=0,
            distance_from_origin_miles=0.0,
        )

        sequence = 1
        for event in events:
            stop_kind = _EVENT_KIND_TO_STOP_KIND.get(event.kind)
            if stop_kind is None:
                continue
            lat, lon = mile_to_coord(event.start_mile)
            Stop.objects.create(
                trip=trip,
                sequence=sequence,
                kind=stop_kind,
                label=event.label,
                lat=lat,
                lon=lon,
                arrival=event.start,
                departure=event.end,
                duration_minutes=round(event.duration_minutes),
                distance_from_origin_miles=round(event.start_mile, 1),
            )
            sequence += 1

    def _create_logs(self, trip: Trip, events: list[Event], timezone_name: str) -> None:
        for day in logsheet.build(events, timezone_name):
            log_day = LogDay.objects.create(
                trip=trip,
                date=day.date,
                sequence=day.sequence,
                total_miles_driving=day.total_miles_driving,
                off_duty_hours=day.totals.off_duty_hours,
                sleeper_hours=day.totals.sleeper_hours,
                driving_hours=day.totals.driving_hours,
                on_duty_hours=day.totals.on_duty_hours,
            )
            DutySegment.objects.bulk_create(
                DutySegment(
                    log_day=log_day,
                    status=seg.status.value,
                    start_minute=seg.start_minute,
                    end_minute=seg.end_minute,
                    remark=seg.remark,
                )
                for seg in day.segments
            )


def _final_cycle_state(events: list[Event], opening_cycle_minutes: float) -> tuple[float, bool]:
    """Cycle hours remaining at trip end, and whether a 34h restart occurred.

    Mirrors the engine's own cycle bookkeeping (driving + on-duty-not-driving
    accrue, everything else doesn't; a restart zeroes it) without needing the
    engine to expose its internal state.
    """
    cycle_minutes_used = opening_cycle_minutes
    restart_required = False
    for event in events:
        if event.kind == EventKind.RESTART_34:
            cycle_minutes_used = 0.0
            restart_required = True
        elif event.status in (HOSDutyStatus.DRIVING, HOSDutyStatus.ON_DUTY):
            cycle_minutes_used += event.duration_minutes
    return (rules.MAX_CYCLE_MINUTES - cycle_minutes_used) / 60, restart_required

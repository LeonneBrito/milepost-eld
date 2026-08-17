from dataclasses import dataclass
from datetime import date, datetime
from enum import Enum


class DutyStatus(str, Enum):
    OFF_DUTY = "OFF"
    SLEEPER = "SB"
    DRIVING = "D"
    ON_DUTY = "ON"


class EventKind(str, Enum):
    PICKUP = "pickup"
    DROPOFF = "dropoff"
    DRIVE = "drive"
    FUEL = "fuel"
    BREAK_30 = "break_30"
    REST_10 = "rest_10"
    RESTART_34 = "restart_34"
    INSPECTION = "inspection"


@dataclass(frozen=True)
class Event:
    """One HOS-relevant occurrence, emitted by the simulation in trip order."""

    kind: EventKind
    status: DutyStatus
    start: datetime  # tz-aware
    end: datetime  # tz-aware
    start_mile: float  # cumulative miles from trip origin
    end_mile: float
    label: str = ""

    @property
    def duration_minutes(self) -> float:
        return (self.end - self.start).total_seconds() / 60


@dataclass(frozen=True)
class LegProfile:
    """Distance/duration for one hop of the trip (e.g. current -> pickup)."""

    label: str
    distance_miles: float
    duration_minutes: float

    @property
    def speed_mph(self) -> float:
        hours = self.duration_minutes / 60
        return self.distance_miles / hours if hours > 0 else 0.0


@dataclass(frozen=True)
class DutySegment:
    status: DutyStatus
    start_minute: int  # minutes from local midnight, 0..1440
    end_minute: int
    remark: str = ""


@dataclass(frozen=True)
class LogDayTotals:
    off_duty_hours: float
    sleeper_hours: float
    driving_hours: float
    on_duty_hours: float

    @property
    def total_hours(self) -> float:
        return self.off_duty_hours + self.sleeper_hours + self.driving_hours + self.on_duty_hours


@dataclass(frozen=True)
class LogDay:
    date: date
    sequence: int
    total_miles_driving: float
    totals: LogDayTotals
    segments: list[DutySegment]

"""Unit tests for the pure HOS simulation engine (apps/hos/engine.py).

No Django, no network — these run in milliseconds and are the strongest
evidence of regulatory correctness in the whole codebase.
"""

from datetime import datetime, timezone

import pytest

from apps.hos import engine, rules
from apps.hos.exceptions import InvalidCycleHoursError
from apps.hos.timeline import DutyStatus, EventKind, LegProfile

START = datetime(2026, 3, 4, 6, 0, tzinfo=timezone.utc)


def leg(distance_miles, speed_mph=60.0, label="leg"):
    duration_minutes = distance_miles / speed_mph * 60
    return LegProfile(label=label, distance_miles=distance_miles, duration_minutes=duration_minutes)


def drive_minutes(events):
    return sum(e.duration_minutes for e in events if e.status == DutyStatus.DRIVING)


def kinds(events):
    return [e.kind for e in events]


class TestShortTripSingleDay:
    def test_no_break_or_reset_needed(self):
        events = engine.simulate(
            legs=[leg(100), leg(200)],
            start_datetime=START,
            cycle_used_minutes=0,
        )

        assert EventKind.BREAK_30 not in kinds(events)
        assert EventKind.REST_10 not in kinds(events)
        assert EventKind.RESTART_34 not in kinds(events)
        assert drive_minutes(events) == pytest.approx(300)

    def test_starts_and_ends_with_inspection(self):
        events = engine.simulate(legs=[leg(50)], start_datetime=START, cycle_used_minutes=0)
        assert events[0].kind == EventKind.INSPECTION
        assert events[-1].kind == EventKind.INSPECTION

    def test_pickup_then_dropoff_labels(self):
        events = engine.simulate(
            legs=[leg(50), leg(50)],
            start_datetime=START,
            cycle_used_minutes=0,
            pickup_label="St. Louis, MO",
            dropoff_label="Dallas, TX",
        )
        pickup = next(e for e in events if e.kind == EventKind.PICKUP)
        dropoff = next(e for e in events if e.kind == EventKind.DROPOFF)
        assert "St. Louis, MO" in pickup.label
        assert "Dallas, TX" in dropoff.label


class TestBreakInsertedAt8Hours:
    def test_break_at_exactly_8h_driving(self):
        # 550 continuous miles at 60mph: break should land at the 480-minute
        # (8h) driving mark, then the remaining 70 minutes resume after.
        events = engine.simulate(legs=[leg(550)], start_datetime=START, cycle_used_minutes=0)

        breaks = [e for e in events if e.kind == EventKind.BREAK_30]
        assert len(breaks) == 1

        driving_before_break = sum(
            e.duration_minutes for e in events if e.status == DutyStatus.DRIVING and e.end <= breaks[0].start
        )
        assert driving_before_break == pytest.approx(rules.MAX_DRIVING_BEFORE_BREAK_MINUTES)
        assert breaks[0].duration_minutes == rules.BREAK_MINUTES
        assert breaks[0].status == DutyStatus.OFF_DUTY

        assert drive_minutes(events) == pytest.approx(550)


class Test11HourDrivingLimit:
    def test_10h_reset_after_11h_driving(self):
        # 800 miles at 60mph, no fuel stop in range (<1000mi): the 11h
        # driving cap (660 min) binds before the trip completes.
        events = engine.simulate(legs=[leg(800)], start_datetime=START, cycle_used_minutes=0)

        resets = [e for e in events if e.kind == EventKind.REST_10]
        assert len(resets) == 1
        assert resets[0].duration_minutes == rules.RESET_MINUTES
        assert resets[0].status == DutyStatus.SLEEPER

        driving_before_reset = sum(
            e.duration_minutes for e in events if e.status == DutyStatus.DRIVING and e.end <= resets[0].start
        )
        assert driving_before_reset == pytest.approx(rules.MAX_DRIVING_MINUTES_PER_DUTY_PERIOD)

        driving_after_reset = sum(
            e.duration_minutes for e in events if e.status == DutyStatus.DRIVING and e.start >= resets[0].end
        )
        assert driving_after_reset == pytest.approx(800 - rules.MAX_DRIVING_MINUTES_PER_DUTY_PERIOD)


class Test14HourWindowBindsFirst:
    def test_window_forces_reset_before_11h_driving_limit(self):
        # Many short drives separated by 60-minute on-duty stops: the 14h
        # window fills up from stop time even though total driving stays low.
        legs = [leg(5) for _ in range(20)]
        events = engine.simulate(legs=legs, start_datetime=START, cycle_used_minutes=0)

        resets = [e for e in events if e.kind == EventKind.REST_10]
        assert resets, "expected the window to force a reset"

        first_reset = resets[0]
        driving_before_reset = sum(
            e.duration_minutes
            for e in events
            if e.status == DutyStatus.DRIVING and e.end <= first_reset.start
        )
        # Well under the 660-minute (11h) driving cap: the window bound first.
        assert driving_before_reset < rules.MAX_DRIVING_MINUTES_PER_DUTY_PERIOD / 2


class TestFuelEvery1000Miles:
    def test_exactly_two_fuel_stops_over_2400_miles(self):
        events = engine.simulate(legs=[leg(2400, speed_mph=50.0)], start_datetime=START, cycle_used_minutes=0)

        fuel_stops = [e for e in events if e.kind == EventKind.FUEL]
        assert len(fuel_stops) == 2
        for stop in fuel_stops:
            assert stop.duration_minutes == rules.FUEL_STOP_MINUTES
            assert stop.status == DutyStatus.ON_DUTY


class TestCycleExhaustion:
    def test_34h_restart_inserted_and_cycle_resets(self):
        # Start 68h into the 70h cycle; a couple hours of on-duty work
        # exhausts the cycle mid-trip and forces a restart.
        events = engine.simulate(
            legs=[leg(300)],
            start_datetime=START,
            cycle_used_minutes=68 * 60,
        )

        restarts = [e for e in events if e.kind == EventKind.RESTART_34]
        assert len(restarts) == 1
        assert restarts[0].duration_minutes == rules.RESTART_MINUTES
        assert restarts[0].status == DutyStatus.OFF_DUTY


class TestCycleAt70Rejected:
    def test_raises_when_cycle_already_at_cap(self):
        with pytest.raises(InvalidCycleHoursError):
            engine.simulate(legs=[leg(100)], start_datetime=START, cycle_used_minutes=70 * 60)

    def test_raises_when_cycle_over_cap(self):
        with pytest.raises(InvalidCycleHoursError):
            engine.simulate(legs=[leg(100)], start_datetime=START, cycle_used_minutes=71 * 60)


class TestTerminationGuard:
    def test_zero_speed_leg_does_not_hang(self, monkeypatch):
        # A leg with zero reported duration (upstream data glitch) must not
        # cause a divide-by-zero or infinite loop — it should fall back to
        # the default speed and still terminate.
        events = engine.simulate(
            legs=[LegProfile(label="broken", distance_miles=100, duration_minutes=0)],
            start_datetime=START,
            cycle_used_minutes=0,
        )
        assert drive_minutes(events) > 0

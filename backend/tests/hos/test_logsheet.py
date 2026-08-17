"""Tests for the pure log-sheet builder (apps/hos/logsheet.py).

Includes the two invariants the design doc calls out explicitly: every
LogDay's segments are contiguous and cover [0, 1440), and the four totals
always sum to exactly 24 hours. These are checked both on hand-picked
scenarios and, via Hypothesis, on randomly generated trips.
"""

from datetime import datetime, timedelta, timezone

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from apps.hos import engine, logsheet, rules
from apps.hos.timeline import LegProfile

TZ_NAME = "America/Chicago"
START = datetime(2026, 3, 4, 6, 0, tzinfo=timezone.utc)


def leg(distance_miles, speed_mph=55.0, label="leg"):
    return LegProfile(label=label, distance_miles=distance_miles, duration_minutes=distance_miles / speed_mph * 60)


def assert_day_is_valid(day):
    assert day.segments, f"day {day.date} has no segments"

    assert day.segments[0].start_minute == 0
    assert day.segments[-1].end_minute == rules.MINUTES_PER_DAY

    for prev, nxt in zip(day.segments, day.segments[1:]):
        assert prev.end_minute == nxt.start_minute, f"gap/overlap between {prev} and {nxt}"

    for seg in day.segments:
        assert 0 <= seg.start_minute < seg.end_minute <= rules.MINUTES_PER_DAY

    total_minutes = round(day.totals.total_hours * 60)
    assert total_minutes == rules.MINUTES_PER_DAY


class TestKnownScenario:
    def test_single_day_trip(self):
        events = engine.simulate(legs=[leg(100), leg(150)], start_datetime=START, cycle_used_minutes=0)
        days = logsheet.build(events, TZ_NAME)

        assert len(days) == 1
        assert days[0].sequence == 1
        assert_day_is_valid(days[0])
        # 6am UTC start on 2026-03-04 is midnight local (America/Chicago, CST=UTC-6)
        assert days[0].date.isoformat() == "2026-03-04"

    def test_pre_trip_time_padded_off_duty(self):
        # 06:00 UTC on 2026-03-04 is exactly local midnight in Chicago (pre-DST),
        # so push the start later in the local day to exercise the padding.
        mid_morning_start = START + timedelta(hours=6)
        events = engine.simulate(legs=[leg(50)], start_datetime=mid_morning_start, cycle_used_minutes=0)
        days = logsheet.build(events, TZ_NAME)

        first_segment = days[0].segments[0]
        assert first_segment.status.value == "OFF"
        assert first_segment.start_minute == 0
        assert first_segment.end_minute == 360

    def test_multi_day_trip_splits_across_calendar_days(self):
        events = engine.simulate(legs=[leg(800)], start_datetime=START, cycle_used_minutes=0)
        days = logsheet.build(events, TZ_NAME)

        assert len(days) >= 2
        for i, day in enumerate(days, start=1):
            assert day.sequence == i
            assert_day_is_valid(day)

    def test_total_miles_driving_matches_leg_distance(self):
        events = engine.simulate(legs=[leg(400)], start_datetime=START, cycle_used_minutes=0)
        days = logsheet.build(events, TZ_NAME)

        assert sum(d.total_miles_driving for d in days) == pytest.approx(400, rel=1e-2)


# --- property tests -------------------------------------------------------

trip_legs = st.lists(
    st.floats(min_value=20, max_value=900, allow_nan=False, allow_infinity=False),
    min_size=1,
    max_size=3,
).map(lambda distances: [leg(d) for d in distances])

cycle_used = st.integers(min_value=0, max_value=rules.MAX_CYCLE_MINUTES - 1)
start_offset_minutes = st.integers(min_value=0, max_value=rules.MINUTES_PER_DAY - 1)


@settings(max_examples=30, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(legs=trip_legs, cycle_used_minutes=cycle_used, offset=start_offset_minutes)
def test_every_log_day_is_contiguous_and_totals_24h(legs, cycle_used_minutes, offset):
    start = START + timedelta(minutes=offset)
    events = engine.simulate(legs=legs, start_datetime=start, cycle_used_minutes=cycle_used_minutes)
    days = logsheet.build(events, TZ_NAME)

    assert days
    for day in days:
        assert_day_is_valid(day)

    # sequences are 1-based and consecutive
    assert [d.sequence for d in days] == list(range(1, len(days) + 1))

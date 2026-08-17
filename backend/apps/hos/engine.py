"""Pure HOS simulation: a distance-consumption model run against FMCSA clocks.

No network, no ORM, no clock reads (the caller supplies `start_datetime`).
Given a distance/duration profile per leg and a starting cycle balance,
`simulate()` returns an ordered list of Events covering the whole trip,
pre-trip inspection through post-trip inspection.

Stop-selection priority when driving is blocked (§7.4 of the design doc —
the order matters):
  1. cycle exhausted (>= 70h used)          -> 34-hour restart, resets cycle
  2. 11h driving or 14h window reached       -> 10-hour reset (sleeper berth)
  3. 8h cumulative driving since last break  -> 30-minute break (off duty)
  4. 1,000 miles since last fuel             -> 30-minute fuel stop (on duty)

Note the asymmetry: a 10-hour reset also satisfies the 30-minute break and
the 14-hour window, but does NOT reduce cycle hours. Only a 34-hour restart
does that.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta

from . import rules
from .exceptions import InvalidCycleHoursError, SimulationDidNotConverge
from .timeline import DutyStatus, Event, EventKind, LegProfile

_EPS = 1e-6


@dataclass
class _State:
    clock: datetime
    position_miles: float = 0.0
    driving_minutes_today: float = 0.0
    window_minutes_elapsed: float = 0.0
    driving_since_break: float = 0.0
    cycle_minutes_used: float = 0.0
    miles_since_fuel: float = 0.0
    events: list[Event] = field(default_factory=list)


def simulate(
    legs: list[LegProfile],
    start_datetime: datetime,
    cycle_used_minutes: float,
    pickup_label: str = "Pickup",
    dropoff_label: str = "Dropoff",
    origin_label: str = "Origin",
) -> list[Event]:
    if cycle_used_minutes >= rules.MAX_CYCLE_MINUTES:
        raise InvalidCycleHoursError(
            f"cycle_used_minutes ({cycle_used_minutes}) must be below the "
            f"{rules.MAX_CYCLE_MINUTES}-minute (70h) cycle limit"
        )
    if not legs:
        raise ValueError("simulate() requires at least one leg")

    state = _State(clock=start_datetime, cycle_minutes_used=cycle_used_minutes)

    _on_duty_stop(state, rules.INSPECTION_MINUTES, EventKind.INSPECTION, f"{origin_label} — pre-trip inspection")

    last_index = len(legs) - 1
    for index, leg in enumerate(legs):
        _drive_leg(state, leg)
        is_last_leg = index == last_index
        stop_kind = EventKind.DROPOFF if is_last_leg else EventKind.PICKUP
        stop_label = dropoff_label if is_last_leg else pickup_label
        suffix = "dropoff" if is_last_leg else "pickup"
        _on_duty_stop(state, rules.PICKUP_DROPOFF_MINUTES, stop_kind, f"{stop_label} — {suffix}")

    _on_duty_stop(state, rules.INSPECTION_MINUTES, EventKind.INSPECTION, f"{dropoff_label} — post-trip inspection")

    return state.events


def _drive_leg(state: _State, leg: LegProfile) -> None:
    remaining_miles = leg.distance_miles
    speed_mph = leg.speed_mph or rules.DEFAULT_SPEED_MPH

    for _ in range(rules.MAX_SIMULATION_ITERATIONS):
        if remaining_miles <= _EPS:
            return

        minutes_to_go = _minutes_for_miles(remaining_miles, speed_mph)
        miles_until_fuel = max(rules.MILES_BETWEEN_FUEL_STOPS - state.miles_since_fuel, 0.0)
        minutes_to_fuel = _minutes_for_miles(miles_until_fuel, speed_mph)

        budget = min(
            rules.MAX_DRIVING_MINUTES_PER_DUTY_PERIOD - state.driving_minutes_today,
            rules.MAX_WINDOW_MINUTES - state.window_minutes_elapsed,
            rules.MAX_DRIVING_BEFORE_BREAK_MINUTES - state.driving_since_break,
            rules.MAX_CYCLE_MINUTES - state.cycle_minutes_used,
            minutes_to_fuel,
            minutes_to_go,
        )

        if budget <= _EPS:
            _resolve_constraint(state)
            continue

        miles = min(_miles_for_minutes(budget, speed_mph), remaining_miles)
        _drive(state, budget, miles)
        remaining_miles -= miles

    raise SimulationDidNotConverge(
        f"Exceeded {rules.MAX_SIMULATION_ITERATIONS} iterations simulating leg '{leg.label}' "
        "— likely a units bug in the budget calculation"
    )


def _resolve_constraint(state: _State) -> None:
    if state.cycle_minutes_used >= rules.MAX_CYCLE_MINUTES - _EPS:
        _restart_34(state)
        return

    if (
        state.driving_minutes_today >= rules.MAX_DRIVING_MINUTES_PER_DUTY_PERIOD - _EPS
        or state.window_minutes_elapsed >= rules.MAX_WINDOW_MINUTES - _EPS
    ):
        _reset_10(state)
        return

    if state.driving_since_break >= rules.MAX_DRIVING_BEFORE_BREAK_MINUTES - _EPS:
        _break_30(state)
        return

    if state.miles_since_fuel >= rules.MILES_BETWEEN_FUEL_STOPS - _EPS:
        _fuel_stop(state)
        return

    raise SimulationDidNotConverge(
        "Driving budget exhausted but no known constraint is at its limit — units bug"
    )


def _minutes_for_miles(miles: float, speed_mph: float) -> float:
    return miles / speed_mph * 60


def _miles_for_minutes(minutes: float, speed_mph: float) -> float:
    return minutes / 60 * speed_mph


def _drive(state: _State, minutes: float, miles: float) -> None:
    start, start_mile = state.clock, state.position_miles
    end, end_mile = start + timedelta(minutes=minutes), start_mile + miles

    state.driving_minutes_today += minutes
    state.window_minutes_elapsed += minutes
    state.driving_since_break += minutes
    state.cycle_minutes_used += minutes
    state.miles_since_fuel += miles
    state.position_miles = end_mile
    state.clock = end

    state.events.append(Event(EventKind.DRIVE, DutyStatus.DRIVING, start, end, start_mile, end_mile))


def _on_duty_stop(state: _State, minutes: float, kind: EventKind, label: str) -> None:
    """Pickup, dropoff, fuel, and inspections: on duty, not driving. Counts toward cycle."""
    start = state.clock
    end = start + timedelta(minutes=minutes)

    state.window_minutes_elapsed += minutes
    state.cycle_minutes_used += minutes
    state.clock = end

    state.events.append(
        Event(kind, DutyStatus.ON_DUTY, start, end, state.position_miles, state.position_miles, label)
    )


def _fuel_stop(state: _State) -> None:
    _on_duty_stop(state, rules.FUEL_STOP_MINUTES, EventKind.FUEL, "Fuel stop")
    state.miles_since_fuel = 0.0


def _break_30(state: _State) -> None:
    """30-minute break: off duty. Counts against the 14h window but not the cycle."""
    start = state.clock
    end = start + timedelta(minutes=rules.BREAK_MINUTES)

    state.window_minutes_elapsed += rules.BREAK_MINUTES
    state.driving_since_break = 0.0
    state.clock = end

    state.events.append(
        Event(
            EventKind.BREAK_30,
            DutyStatus.OFF_DUTY,
            start,
            end,
            state.position_miles,
            state.position_miles,
            "30-minute break",
        )
    )


def _reset_10(state: _State) -> None:
    """10-hour reset: sleeper berth. Clears the daily/window/break clocks, not the cycle."""
    start = state.clock
    end = start + timedelta(minutes=rules.RESET_MINUTES)

    state.driving_minutes_today = 0.0
    state.window_minutes_elapsed = 0.0
    state.driving_since_break = 0.0
    state.clock = end

    state.events.append(
        Event(
            EventKind.REST_10,
            DutyStatus.SLEEPER,
            start,
            end,
            state.position_miles,
            state.position_miles,
            "10-hour reset",
        )
    )


def _restart_34(state: _State) -> None:
    """34-hour restart: off duty. The only event that reduces cycle hours."""
    start = state.clock
    end = start + timedelta(minutes=rules.RESTART_MINUTES)

    state.cycle_minutes_used = 0.0
    state.driving_minutes_today = 0.0
    state.window_minutes_elapsed = 0.0
    state.driving_since_break = 0.0
    state.clock = end

    state.events.append(
        Event(
            EventKind.RESTART_34,
            DutyStatus.OFF_DUTY,
            start,
            end,
            state.position_miles,
            state.position_miles,
            "34-hour restart",
        )
    )

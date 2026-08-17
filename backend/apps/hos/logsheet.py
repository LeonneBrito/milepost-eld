"""Turn a flat Event timeline into per-calendar-day duty-status log sheets.

Pure function, no I/O: `build()` takes Events (UTC-aware) and a home-terminal
timezone name and returns one LogDay per calendar day touched by the trip.

Steps (§7.6 of the design doc):
  1. Convert every event's [start, end) to home-terminal local time.
  2. Split any event spanning local midnight into per-day pieces.
  3. Pad the first/last day so the day's pieces cover [0, 1440) — time before
     the trip starts or after it ends on a partial day is off duty.
  4. Snap boundaries to the nearest 15 minutes, cumulatively, so rounding
     error never accumulates past one quarter-hour.
  5. Merge consecutive same-status segments.
  6. Compute the four totals; assert they sum to exactly 1440 minutes.

Remarks are seeded from the source event's label (e.g. "St. Louis, MO —
pickup", "Fuel stop"). Reverse-geocoded "City, ST" labels for driving-status
changes are layered on afterward by the trips service layer, which has
network access; this module stays framework- and I/O-free.
"""

from collections import defaultdict
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from . import rules
from .exceptions import LogDayInvariantError
from .timeline import DutySegment, DutyStatus, Event, LogDay, LogDayTotals

_MINUTES_PER_DAY = rules.MINUTES_PER_DAY
_QUARTER = rules.QUARTER_HOUR_MINUTES


class _Piece:
    __slots__ = ("status", "start_local", "end_local", "remark", "start_mile", "end_mile")

    def __init__(self, status, start_local, end_local, remark, start_mile, end_mile):
        self.status = status
        self.start_local = start_local
        self.end_local = end_local
        self.remark = remark
        self.start_mile = start_mile
        self.end_mile = end_mile


def build(events: list[Event], timezone_name: str) -> list[LogDay]:
    tz = ZoneInfo(timezone_name)
    pieces_by_date: dict[date, list[_Piece]] = defaultdict(list)

    for event in events:
        for piece in _split_at_local_midnight(event, tz):
            pieces_by_date[piece.start_local.date()].append(piece)

    log_days = []
    for sequence, day in enumerate(sorted(pieces_by_date), start=1):
        log_days.append(_build_log_day(day, sequence, pieces_by_date[day], tz))
    return log_days


def _split_at_local_midnight(event: Event, tz: ZoneInfo) -> list[_Piece]:
    start_local = event.start.astimezone(tz)
    end_local = event.end.astimezone(tz)
    span_minutes = (event.end - event.start).total_seconds() / 60

    pieces = []
    cursor = start_local
    while cursor < end_local:
        day_start = datetime(cursor.year, cursor.month, cursor.day, tzinfo=tz)
        next_midnight = day_start + timedelta(days=1)
        piece_end = min(end_local, next_midnight)

        if span_minutes > 0:
            frac_start = (cursor - start_local).total_seconds() / 60 / span_minutes
            frac_end = (piece_end - start_local).total_seconds() / 60 / span_minutes
        else:
            frac_start = frac_end = 0.0

        mile_span = event.end_mile - event.start_mile
        pieces.append(
            _Piece(
                event.status,
                cursor,
                piece_end,
                event.label,
                event.start_mile + frac_start * mile_span,
                event.start_mile + frac_end * mile_span,
            )
        )
        cursor = piece_end

    return pieces


def _build_log_day(day: date, sequence: int, pieces: list[_Piece], tz: ZoneInfo) -> LogDay:
    day_start = datetime(day.year, day.month, day.day, tzinfo=tz)
    day_end = day_start + timedelta(days=1)

    pieces = _fill_gaps(pieces, day_start, day_end)

    total_miles_driving = sum(
        p.end_mile - p.start_mile for p in pieces if p.status == DutyStatus.DRIVING
    )

    raw_boundaries = sorted(
        {0.0, float(_MINUTES_PER_DAY)}
        | {(p.start_local - day_start).total_seconds() / 60 for p in pieces}
        | {(p.end_local - day_start).total_seconds() / 60 for p in pieces}
    )
    snapped = _snap_cumulative(raw_boundaries)
    boundary_map = dict(zip(raw_boundaries, snapped))

    segments = []
    for p in pieces:
        start_minute = boundary_map[(p.start_local - day_start).total_seconds() / 60]
        end_minute = boundary_map[(p.end_local - day_start).total_seconds() / 60]
        if end_minute > start_minute:
            segments.append(DutySegment(p.status, int(start_minute), int(end_minute), p.remark))

    segments.sort(key=lambda s: s.start_minute)
    segments = _merge_adjacent(segments)

    totals = _compute_totals(segments)
    total_minutes = round(totals.total_hours * 60)
    if total_minutes != _MINUTES_PER_DAY:
        raise LogDayInvariantError(
            f"Log day {day} totals {total_minutes} minutes, expected {_MINUTES_PER_DAY}"
        )

    return LogDay(
        date=day,
        sequence=sequence,
        total_miles_driving=round(total_miles_driving, 1),
        totals=totals,
        segments=segments,
    )


def _fill_gaps(pieces: list[_Piece], day_start: datetime, day_end: datetime) -> list[_Piece]:
    pieces = sorted(pieces, key=lambda p: p.start_local)
    filled = []
    cursor = day_start
    for p in pieces:
        if p.start_local > cursor:
            filled.append(_Piece(DutyStatus.OFF_DUTY, cursor, p.start_local, "", p.start_mile, p.start_mile))
        filled.append(p)
        cursor = max(cursor, p.end_local)
    if cursor < day_end:
        last_mile = pieces[-1].end_mile if pieces else 0.0
        filled.append(_Piece(DutyStatus.OFF_DUTY, cursor, day_end, "", last_mile, last_mile))
    return filled


def _snap_cumulative(raw_boundaries: list[float]) -> list[float]:
    """Round each *cumulative* boundary to the nearest quarter-hour.

    Rounding the absolute position (rather than each segment's duration)
    means rounding error never compounds across segments — each boundary is
    off by at most half a quantum from its raw value, full stop. The first
    and last boundaries are pinned to 0 and 1440 exactly.
    """
    snapped = []
    prev = 0.0
    last_index = len(raw_boundaries) - 1
    for i, raw in enumerate(raw_boundaries):
        if i == 0:
            value = 0.0
        elif i == last_index:
            value = float(_MINUTES_PER_DAY)
        else:
            value = round(raw / _QUARTER) * _QUARTER
            value = min(max(value, prev), float(_MINUTES_PER_DAY))
        snapped.append(value)
        prev = value
    return snapped


def _merge_adjacent(segments: list[DutySegment]) -> list[DutySegment]:
    if not segments:
        return []
    merged = [segments[0]]
    for seg in segments[1:]:
        last = merged[-1]
        if seg.status == last.status and seg.start_minute == last.end_minute:
            merged[-1] = DutySegment(last.status, last.start_minute, seg.end_minute, last.remark or seg.remark)
        else:
            merged.append(seg)
    return merged


def _compute_totals(segments: list[DutySegment]) -> LogDayTotals:
    sums = defaultdict(int)
    for seg in segments:
        sums[seg.status] += seg.end_minute - seg.start_minute
    return LogDayTotals(
        off_duty_hours=sums[DutyStatus.OFF_DUTY] / 60,
        sleeper_hours=sums[DutyStatus.SLEEPER] / 60,
        driving_hours=sums[DutyStatus.DRIVING] / 60,
        on_duty_hours=sums[DutyStatus.ON_DUTY] / 60,
    )

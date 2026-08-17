"""FMCSA Part 395 constants used by the HOS engine.

All time constants are in minutes, all distance constants in miles. This
module has no Django imports — apps/hos is a pure domain library, testable
without a database. See design doc §3 for the regulatory sources and the
explicit modelling assumptions (no adverse-driving-conditions exception, no
split sleeper berth, single-block resets only).
"""

MAX_DRIVING_MINUTES_PER_DUTY_PERIOD = 11 * 60  # Sec. 395.3(a)(3)
MAX_WINDOW_MINUTES = 14 * 60  # Sec. 395.3(a)(2)
MAX_DRIVING_BEFORE_BREAK_MINUTES = 8 * 60  # Sec. 395.3(a)(3)(ii)
BREAK_MINUTES = 30
RESET_MINUTES = 10 * 60  # Sec. 395.3(a)(1)
RESTART_MINUTES = 34 * 60  # Sec. 395.3(c), optional
MAX_CYCLE_MINUTES = 70 * 60  # Sec. 395.3(b)(2), 70h / 8 days

MILES_BETWEEN_FUEL_STOPS = 1000  # assessment brief; regulation sets no interval
FUEL_STOP_MINUTES = 30  # operational assumption; regulation sets no duration

PICKUP_DROPOFF_MINUTES = 60  # assessment brief
INSPECTION_MINUTES = 15  # pre-/post-trip, on duty not driving

QUARTER_HOUR_MINUTES = 15  # paper log resolution
MINUTES_PER_DAY = 24 * 60

MAX_SIMULATION_ITERATIONS = 500  # termination guard against unit-conversion bugs

DEFAULT_SPEED_MPH = 45.0  # fallback only, used if a leg reports zero duration

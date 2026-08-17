class SimulationDidNotConverge(Exception):
    """Raised when the driving loop exceeds MAX_SIMULATION_ITERATIONS.

    Almost always means a units bug (e.g. minutes vs. hours) rather than a
    genuinely stuck trip — legitimate trips resolve in a handful of stops.
    """


class LogDayInvariantError(Exception):
    """Raised when a built LogDay's segments don't cover exactly 24 hours."""


class InvalidCycleHoursError(ValueError):
    """Raised when the opening cycle balance is already at or over the 70-hour cap."""

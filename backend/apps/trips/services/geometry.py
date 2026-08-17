"""Geometry helpers for placing HOS stops on the actual route polyline.

Per the design doc's stated assumption: rest/fuel stops are placed at the
interpolated point on the route polyline where the clock expires, not at a
real truck stop — no free, reliable POI dataset fits the time budget.
"""

import bisect
import math


def haversine_miles(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    earth_radius_miles = 3958.7613
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlambda / 2) ** 2
    return 2 * earth_radius_miles * math.asin(min(1.0, math.sqrt(a)))


def build_mile_interpolator(geometry: list[tuple[float, float]], total_distance_miles: float):
    """Return a function mapping cumulative miles -> (lat, lon) along the route.

    `geometry` is (lon, lat) pairs in travel order, as returned by the routing
    provider. Cumulative distance is computed via haversine between vertices
    and rescaled to match `total_distance_miles` (the routing provider's own
    road-following figure), so a mile marker anywhere in [0, total_distance]
    is guaranteed to land inside the polyline.
    """
    if not geometry:
        raise ValueError("Route geometry is empty")
    if len(geometry) == 1:
        lon, lat = geometry[0]
        return lambda mile: (lat, lon)

    cumulative = [0.0]
    for (lon1, lat1), (lon2, lat2) in zip(geometry, geometry[1:]):
        cumulative.append(cumulative[-1] + haversine_miles(lat1, lon1, lat2, lon2))

    raw_total = cumulative[-1]
    if raw_total > 0 and total_distance_miles > 0:
        scale = total_distance_miles / raw_total
        cumulative = [c * scale for c in cumulative]

    def interpolate(mile: float) -> tuple[float, float]:
        clamped = max(0.0, min(mile, cumulative[-1]))
        idx = bisect.bisect_right(cumulative, clamped) - 1
        idx = max(0, min(idx, len(geometry) - 2))

        seg_start, seg_end = cumulative[idx], cumulative[idx + 1]
        t = (clamped - seg_start) / (seg_end - seg_start) if seg_end > seg_start else 0.0

        lon1, lat1 = geometry[idx]
        lon2, lat2 = geometry[idx + 1]
        return (lat1 + t * (lat2 - lat1), lon1 + t * (lon2 - lon1))

    return interpolate


def nearest_label(lat: float, lon: float, named_points: list[tuple[str, float, float]]) -> str:
    """Fall back to the closest known waypoint name when reverse geocoding fails."""
    if not named_points:
        return ""
    return min(named_points, key=lambda p: haversine_miles(lat, lon, p[1], p[2]))[0]

import pytest

from apps.trips.services.geometry import build_mile_interpolator, haversine_miles, nearest_label


def test_haversine_known_distance():
    # Chicago -> St. Louis is roughly 260 miles as the crow flies.
    miles = haversine_miles(41.8781, -87.6298, 38.6270, -90.1994)
    assert miles == pytest.approx(260, rel=0.05)


def test_interpolator_endpoints():
    geometry = [(-87.63, 41.88), (-90.2, 38.63)]
    interpolate = build_mile_interpolator(geometry, total_distance_miles=300.0)

    start_lat, start_lon = interpolate(0.0)
    end_lat, end_lon = interpolate(300.0)

    assert (start_lat, start_lon) == pytest.approx((41.88, -87.63))
    assert (end_lat, end_lon) == pytest.approx((38.63, -90.2))


def test_interpolator_midpoint_is_between_endpoints():
    geometry = [(-87.63, 41.88), (-90.2, 38.63)]
    interpolate = build_mile_interpolator(geometry, total_distance_miles=300.0)

    mid_lat, mid_lon = interpolate(150.0)

    assert 38.63 < mid_lat < 41.88
    assert -90.2 < mid_lon < -87.63


def test_interpolator_clamps_out_of_range_miles():
    geometry = [(-87.63, 41.88), (-90.2, 38.63)]
    interpolate = build_mile_interpolator(geometry, total_distance_miles=300.0)

    assert interpolate(-50.0) == interpolate(0.0)
    assert interpolate(999.0) == interpolate(300.0)


def test_nearest_label_picks_closest_point():
    points = [("Chicago, IL", 41.8781, -87.6298), ("Dallas, TX", 32.7767, -96.7970)]
    label = nearest_label(41.5, -87.9, points)
    assert label == "Chicago, IL"


def test_nearest_label_empty_list_returns_empty_string():
    assert nearest_label(0.0, 0.0, []) == ""

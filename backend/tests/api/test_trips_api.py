"""API-level test with fixture geocoding/routing providers.

No network access: FixtureGeocodingProvider and FixtureRoutingProvider stand
in for Nominatim/OSRM, injected by patching the factory functions where
apps.trips.services.planner imports them. This is the one place the whole
pipeline (view -> serializer -> planner -> hos engine -> logsheet -> ORM) is
exercised end to end.
"""

import pytest

from apps.core.exceptions import GeocodingError
from apps.routing.base import GeocodeResult, GeocodingProvider, RouteLeg, RouteResult, RoutingProvider

_KNOWN_PLACES = {
    "chicago, il": GeocodeResult("Chicago, IL", "Chicago, IL", 41.8781, -87.6298),
    "st. louis, mo": GeocodeResult("St. Louis, MO", "St. Louis, MO", 38.6270, -90.1994),
    "dallas, tx": GeocodeResult("Dallas, TX", "Dallas, TX", 32.7767, -96.7970),
}


class FixtureGeocodingProvider(GeocodingProvider):
    def geocode(self, query):
        result = _KNOWN_PLACES.get(query.strip().lower())
        if result is None:
            raise GeocodingError(f"Could not resolve '{query}'", field=None)
        return result

    def reverse(self, lat, lon):
        return "Springfield, MO"


class FixtureRoutingProvider(RoutingProvider):
    def route(self, waypoints):
        legs = [
            RouteLeg(distance_miles=300.0, duration_minutes=300.0),
            RouteLeg(distance_miles=550.0, duration_minutes=550.0),
        ]
        geometry = [(w.lon, w.lat) for w in waypoints]
        return RouteResult(legs=legs, geometry=geometry)


@pytest.fixture(autouse=True)
def fixture_providers(mocker):
    mocker.patch(
        "apps.trips.services.planner.get_geocoding_provider", return_value=FixtureGeocodingProvider()
    )
    mocker.patch(
        "apps.trips.services.planner.get_routing_provider", return_value=FixtureRoutingProvider()
    )


def _payload(**overrides):
    payload = {
        "current_location": "Chicago, IL",
        "pickup_location": "St. Louis, MO",
        "dropoff_location": "Dallas, TX",
        "current_cycle_used_hours": 12.5,
        "start_datetime": "2026-03-04T06:00:00-06:00",
    }
    payload.update(overrides)
    return payload


@pytest.mark.django_db
def test_create_trip_returns_a_full_plan(client):
    response = client.post("/api/trips/", data=_payload(), content_type="application/json")

    assert response.status_code == 201
    data = response.json()

    assert data["summary"]["total_distance_miles"] == pytest.approx(850.0, rel=1e-3)
    assert data["summary"]["days"] == len(data["logs"])
    assert data["stops"][0]["kind"] == "start"
    assert data["stops"][0]["sequence"] == 0
    assert any(stop["kind"] == "pickup" for stop in data["stops"])
    assert any(stop["kind"] == "dropoff" for stop in data["stops"])

    assert data["logs"], "expected at least one log day"
    for day in data["logs"]:
        assert sum(day["totals"].values()) == pytest.approx(24.0, abs=0.01)
        segments = day["segments"]
        assert segments[0]["start_minute"] == 0
        assert segments[-1]["end_minute"] == 1440
        for prev, nxt in zip(segments, segments[1:]):
            assert prev["end_minute"] == nxt["start_minute"]


@pytest.mark.django_db
def test_get_trip_reloads_the_same_plan(client):
    create_response = client.post("/api/trips/", data=_payload(), content_type="application/json")
    trip_id = create_response.json()["id"]

    response = client.get(f"/api/trips/{trip_id}/")

    assert response.status_code == 200
    assert response.json()["id"] == trip_id
    assert response.json()["summary"] == create_response.json()["summary"]


@pytest.mark.django_db
def test_cycle_hours_at_70_is_rejected(client):
    response = client.post(
        "/api/trips/", data=_payload(current_cycle_used_hours=70), content_type="application/json"
    )

    assert response.status_code == 400
    body = response.json()
    assert body["error"] == "VALIDATION_ERROR"
    assert body["field"] == "current_cycle_used_hours"


@pytest.mark.django_db
def test_missing_field_returns_validation_error(client):
    payload = _payload()
    del payload["pickup_location"]

    response = client.post("/api/trips/", data=payload, content_type="application/json")

    assert response.status_code == 400
    assert response.json()["error"] == "VALIDATION_ERROR"


@pytest.mark.django_db
def test_unresolvable_location_returns_geocoding_failed(client):
    response = client.post(
        "/api/trips/", data=_payload(current_location="Nowhereville, ZZ"), content_type="application/json"
    )

    assert response.status_code == 400
    assert response.json()["error"] == "GEOCODING_FAILED"

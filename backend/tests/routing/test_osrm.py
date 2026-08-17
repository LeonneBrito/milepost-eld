import httpx
import pytest

from apps.core.exceptions import RoutingError, UpstreamTimeoutError
from apps.routing.base import Coord
from apps.routing.osrm import OSRMProvider

WAYPOINTS = [Coord(41.8781, -87.6298), Coord(38.6270, -90.1994)]


def _osrm_payload():
    return {
        "code": "Ok",
        "routes": [
            {
                "legs": [{"distance": 482803.0, "duration": 17280.0}],
                "geometry": {"type": "LineString", "coordinates": [[-87.63, 41.88], [-90.2, 38.63]]},
            }
        ],
    }


class _FakeResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise httpx.HTTPStatusError("error", request=None, response=self)

    def json(self):
        return self._payload


def test_route_parses_osrm_response(mocker):
    mocker.patch("apps.routing.osrm.cache.get", return_value=None)
    mocker.patch("apps.routing.osrm.cache.set")
    mocker.patch("httpx.get", return_value=_FakeResponse(_osrm_payload()))

    result = OSRMProvider(base_url="https://osrm.test").route(WAYPOINTS)

    assert len(result.legs) == 1
    assert result.legs[0].distance_miles == pytest.approx(300.0, rel=1e-3)
    assert result.legs[0].duration_minutes == pytest.approx(288.0, rel=1e-3)
    assert result.geometry == [(-87.63, 41.88), (-90.2, 38.63)]


def test_route_uses_cache_when_present(mocker):
    cached = {"legs": [(10.0, 20.0)], "geometry": [[-87.63, 41.88], [-90.2, 38.63]]}
    mocker.patch("apps.routing.osrm.cache.get", return_value=cached)
    get_spy = mocker.patch("httpx.get")

    result = OSRMProvider(base_url="https://osrm.test").route(WAYPOINTS)

    get_spy.assert_not_called()
    assert result.legs[0].distance_miles == 10.0


def test_no_route_raises_routing_error(mocker):
    mocker.patch("apps.routing.osrm.cache.get", return_value=None)
    mocker.patch("httpx.get", return_value=_FakeResponse({"code": "NoRoute", "routes": []}))

    with pytest.raises(RoutingError):
        OSRMProvider(base_url="https://osrm.test").route(WAYPOINTS)


def test_timeout_raises_upstream_timeout_error(mocker):
    mocker.patch("apps.routing.osrm.cache.get", return_value=None)
    mocker.patch("httpx.get", side_effect=httpx.TimeoutException("timed out"))

    with pytest.raises(UpstreamTimeoutError):
        OSRMProvider(base_url="https://osrm.test").route(WAYPOINTS)


def test_single_waypoint_rejected():
    with pytest.raises(RoutingError):
        OSRMProvider(base_url="https://osrm.test").route([WAYPOINTS[0]])

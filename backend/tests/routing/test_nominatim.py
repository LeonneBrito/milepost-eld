import httpx
import pytest

from apps.core.exceptions import GeocodingError, UpstreamTimeoutError
from apps.routing.nominatim import NominatimProvider


class _FakeResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise httpx.HTTPStatusError("error", request=None, response=self)

    def json(self):
        return self._payload


def test_geocode_returns_top_result(mocker):
    mocker.patch("apps.routing.nominatim.cache.get", return_value=None)
    mocker.patch("apps.routing.nominatim.cache.set")
    mocker.patch(
        "httpx.get",
        return_value=_FakeResponse([{"display_name": "Chicago, IL, USA", "lat": "41.8781", "lon": "-87.6298"}]),
    )

    result = NominatimProvider(base_url="https://nominatim.test", user_agent="test-agent").geocode("Chicago, IL")

    assert result.lat == pytest.approx(41.8781)
    assert result.lon == pytest.approx(-87.6298)
    assert result.label == "Chicago, IL, USA"


def test_geocode_empty_result_raises_geocoding_error(mocker):
    mocker.patch("apps.routing.nominatim.cache.get", return_value=None)
    mocker.patch("httpx.get", return_value=_FakeResponse([]))

    with pytest.raises(GeocodingError):
        NominatimProvider(base_url="https://nominatim.test", user_agent="test-agent").geocode("Nowhereville, ZZ")


def test_geocode_uses_cache(mocker):
    cached = {"query": "Chicago, IL", "label": "Chicago, IL, USA", "lat": 41.8781, "lon": -87.6298}
    mocker.patch("apps.routing.nominatim.cache.get", return_value=cached)
    get_spy = mocker.patch("httpx.get")

    result = NominatimProvider(base_url="https://nominatim.test", user_agent="test-agent").geocode("Chicago, IL")

    get_spy.assert_not_called()
    assert result.label == "Chicago, IL, USA"


def test_geocode_timeout_raises_upstream_timeout_error(mocker):
    mocker.patch("apps.routing.nominatim.cache.get", return_value=None)
    mocker.patch("httpx.get", side_effect=httpx.TimeoutException("timed out"))

    with pytest.raises(UpstreamTimeoutError):
        NominatimProvider(base_url="https://nominatim.test", user_agent="test-agent").geocode("Chicago, IL")


def test_reverse_returns_empty_string_on_failure(mocker):
    mocker.patch("apps.routing.nominatim.cache.get", return_value=None)
    mocker.patch("httpx.get", side_effect=httpx.TimeoutException("timed out"))

    label = NominatimProvider(base_url="https://nominatim.test", user_agent="test-agent").reverse(41.87, -87.63)

    assert label == ""


def test_reverse_prefers_city_and_state(mocker):
    mocker.patch("apps.routing.nominatim.cache.get", return_value=None)
    mocker.patch("apps.routing.nominatim.cache.set")
    mocker.patch(
        "httpx.get",
        return_value=_FakeResponse(
            {"address": {"city": "Springfield", "state": "Missouri"}, "display_name": "Springfield, Missouri, USA"}
        ),
    )

    label = NominatimProvider(base_url="https://nominatim.test", user_agent="test-agent").reverse(37.2, -93.3)

    assert label == "Springfield, Missouri"

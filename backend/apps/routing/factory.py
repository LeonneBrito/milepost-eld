"""Wiring between settings and concrete provider implementations.

Swapping OSRM for OpenRouteService (e.g. the OSRM demo server is down on
review day) is a settings change, not a code change. If ORS is configured
(ORS_API_KEY set), it is used as an automatic fallback when the primary
routing provider raises RoutingError/UpstreamTimeoutError.
"""

from django.conf import settings

from apps.core.exceptions import RoutingError, UpstreamTimeoutError

from .base import Coord, GeocodingProvider, RouteResult, RoutingProvider
from .nominatim import NominatimProvider
from .ors import ORSProvider
from .osrm import OSRMProvider


class FallbackRoutingProvider(RoutingProvider):
    def __init__(self, primary: RoutingProvider, fallback: RoutingProvider | None):
        self.primary = primary
        self.fallback = fallback

    def route(self, waypoints: list[Coord]) -> RouteResult:
        try:
            return self.primary.route(waypoints)
        except (RoutingError, UpstreamTimeoutError):
            if self.fallback is None:
                raise
            return self.fallback.route(waypoints)


def get_geocoding_provider() -> GeocodingProvider:
    return NominatimProvider()


def get_routing_provider() -> RoutingProvider:
    primary = OSRMProvider()
    fallback = ORSProvider() if settings.ORS_API_KEY else None
    return FallbackRoutingProvider(primary, fallback)

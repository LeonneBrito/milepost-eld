import httpx
from django.conf import settings
from django.core.cache import cache

from apps.core.exceptions import RoutingError, UpstreamTimeoutError

from .base import (
    Coord,
    RouteLeg,
    RouteResult,
    RoutingProvider,
    route_cache_key,
    route_from_cache,
    route_to_cache,
)

METERS_PER_MILE = 1609.344
CACHE_TTL_SECONDS = 60 * 60 * 24


class ORSProvider(RoutingProvider):
    """Fallback adapter for OpenRouteService, used when OSRM is unreachable."""

    def __init__(self, base_url=None, api_key=None, timeout=None):
        self.base_url = base_url or settings.ORS_BASE_URL
        self.api_key = api_key or settings.ORS_API_KEY
        self.timeout = timeout or settings.UPSTREAM_TIMEOUT_SECONDS

    def route(self, waypoints: list[Coord]) -> RouteResult:
        if len(waypoints) < 2:
            raise RoutingError("At least two waypoints are required to route")
        if not self.api_key:
            raise RoutingError("ORS_API_KEY is not configured")

        key = route_cache_key(waypoints)
        cached = cache.get(key)
        if cached is not None:
            return route_from_cache(cached)

        try:
            response = httpx.post(
                f"{self.base_url}/v2/directions/driving-hgv/geojson",
                json={"coordinates": [[w.lon, w.lat] for w in waypoints]},
                headers={"Authorization": self.api_key, "Content-Type": "application/json"},
                timeout=self.timeout,
            )
            response.raise_for_status()
        except httpx.TimeoutException as exc:
            raise UpstreamTimeoutError("OpenRouteService timed out computing the route") from exc
        except httpx.HTTPError as exc:
            raise RoutingError(f"OpenRouteService routing request failed: {exc}") from exc

        payload = response.json()
        features = payload.get("features") or []
        if not features:
            raise RoutingError("OpenRouteService returned no route")

        feature = features[0]
        segments = feature["properties"]["segments"]
        legs = [
            RouteLeg(
                distance_miles=segment["distance"] / METERS_PER_MILE,
                duration_minutes=segment["duration"] / 60,
            )
            for segment in segments
        ]
        geometry = [tuple(c) for c in feature["geometry"]["coordinates"]]
        result = RouteResult(legs=legs, geometry=geometry)

        cache.set(key, route_to_cache(result), CACHE_TTL_SECONDS)
        return result

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
CACHE_TTL_SECONDS = 60 * 60 * 24  # routes are stable enough to cache for a day


class OSRMProvider(RoutingProvider):
    """Adapter for the OSRM driving-routing API (public demo server by default)."""

    def __init__(self, base_url=None, timeout=None):
        self.base_url = base_url or settings.OSRM_BASE_URL
        self.timeout = timeout or settings.UPSTREAM_TIMEOUT_SECONDS

    def route(self, waypoints: list[Coord]) -> RouteResult:
        if len(waypoints) < 2:
            raise RoutingError("At least two waypoints are required to route")

        key = route_cache_key(waypoints)
        cached = cache.get(key)
        if cached is not None:
            return route_from_cache(cached)

        coord_str = ";".join(f"{w.lon:.5f},{w.lat:.5f}" for w in waypoints)
        try:
            response = httpx.get(
                f"{self.base_url}/route/v1/driving/{coord_str}",
                params={"overview": "full", "geometries": "geojson", "steps": "false"},
                timeout=self.timeout,
            )
            response.raise_for_status()
        except httpx.TimeoutException as exc:
            raise UpstreamTimeoutError("OSRM timed out computing the route") from exc
        except httpx.HTTPError as exc:
            raise RoutingError(f"OSRM routing request failed: {exc}") from exc

        payload = response.json()
        if payload.get("code") != "Ok" or not payload.get("routes"):
            raise RoutingError(
                f"No route found between waypoints: {payload.get('message', payload.get('code'))}"
            )

        route = payload["routes"][0]
        legs = [
            RouteLeg(
                distance_miles=leg["distance"] / METERS_PER_MILE,
                duration_minutes=leg["duration"] / 60,
            )
            for leg in route["legs"]
        ]
        geometry = [tuple(c) for c in route["geometry"]["coordinates"]]
        result = RouteResult(legs=legs, geometry=geometry)

        cache.set(key, route_to_cache(result), CACHE_TTL_SECONDS)
        return result

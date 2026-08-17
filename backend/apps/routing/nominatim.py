import hashlib

import httpx
from django.conf import settings
from django.core.cache import cache

from apps.core.exceptions import DomainError, GeocodingError, UpstreamTimeoutError

from .base import GeocodeResult, GeocodingProvider

CACHE_TTL_SECONDS = 60 * 60 * 24 * 7  # addresses don't move; cache a week


def _cache_key(*parts: str) -> str:
    # Hashed rather than raw text: free-text queries contain spaces/punctuation
    # that memcached (a realistic prod CACHES backend) rejects as key characters.
    digest = hashlib.sha1("|".join(parts).encode()).hexdigest()
    return f"geocode:{digest}"


class NominatimProvider(GeocodingProvider):
    """Adapter for the Nominatim (OpenStreetMap) geocoding API.

    Nominatim's usage policy caps public demo traffic at ~1 req/s and
    requires a real User-Agent, so every result is cached.
    """

    def __init__(self, base_url=None, user_agent=None, timeout=None):
        self.base_url = base_url or settings.NOMINATIM_BASE_URL
        self.user_agent = user_agent or settings.NOMINATIM_USER_AGENT
        self.timeout = timeout or settings.UPSTREAM_TIMEOUT_SECONDS

    def geocode(self, query: str) -> GeocodeResult:
        key = _cache_key("search", query.strip().lower())
        cached = cache.get(key)
        if cached is not None:
            return GeocodeResult(**cached)

        data = self._get("/search", {"q": query, "format": "jsonv2", "limit": 1}, query=query)
        if not data:
            raise GeocodingError(f"Could not resolve '{query}'", field=None)

        top = data[0]
        result = GeocodeResult(
            query=query,
            label=top.get("display_name", query),
            lat=float(top["lat"]),
            lon=float(top["lon"]),
        )
        cache.set(key, result.__dict__, CACHE_TTL_SECONDS)
        return result

    def reverse(self, lat: float, lon: float) -> str:
        rounded_lat, rounded_lon = round(lat, 3), round(lon, 3)
        key = _cache_key("reverse", str(rounded_lat), str(rounded_lon))
        cached = cache.get(key)
        if cached is not None:
            return cached

        try:
            data = self._get(
                "/reverse", {"lat": lat, "lon": lon, "format": "jsonv2", "zoom": 10}, query=None
            )
        except DomainError:
            # Best-effort: the caller falls back to the nearest known waypoint name.
            return ""

        address = data.get("address", {}) if isinstance(data, dict) else {}
        city = (
            address.get("city")
            or address.get("town")
            or address.get("village")
            or address.get("county")
        )
        state = address.get("state")
        label = ", ".join(part for part in (city, state) if part) or data.get("display_name", "")
        cache.set(key, label, CACHE_TTL_SECONDS)
        return label

    def _get(self, path, params, query):
        try:
            response = httpx.get(
                f"{self.base_url}{path}",
                params=params,
                headers={"User-Agent": self.user_agent},
                timeout=self.timeout,
            )
            response.raise_for_status()
        except httpx.TimeoutException as exc:
            raise UpstreamTimeoutError(
                f"Nominatim timed out on '{query}'" if query else "Nominatim timed out"
            ) from exc
        except httpx.HTTPError as exc:
            raise GeocodingError(
                f"Could not resolve '{query}'" if query else f"Nominatim request failed: {exc}",
                field=None,
            ) from exc
        return response.json()

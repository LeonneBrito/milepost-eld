"""Provider-agnostic contracts for geocoding and routing.

Views and the trip planner depend only on these dataclasses and ABCs, never
on a specific vendor. Swap OSRM for OpenRouteService, or Nominatim for
something else, by changing a settings value — see apps/routing/factory.py.
"""

import hashlib
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class Coord:
    lat: float
    lon: float


@dataclass(frozen=True)
class GeocodeResult:
    query: str
    label: str
    lat: float
    lon: float


@dataclass(frozen=True)
class RouteLeg:
    """One hop of the trip, e.g. current -> pickup, or pickup -> dropoff."""

    distance_miles: float
    duration_minutes: float


@dataclass(frozen=True)
class RouteResult:
    legs: list[RouteLeg]
    geometry: list[tuple[float, float]]  # (lon, lat) pairs in travel order

    @property
    def total_distance_miles(self) -> float:
        return sum(leg.distance_miles for leg in self.legs)

    @property
    def total_duration_minutes(self) -> float:
        return sum(leg.duration_minutes for leg in self.legs)


class GeocodingProvider(ABC):
    @abstractmethod
    def geocode(self, query: str) -> GeocodeResult: ...

    @abstractmethod
    def reverse(self, lat: float, lon: float) -> str:
        """Best-effort 'City, ST' label. Returns '' rather than raising."""
        ...


class RoutingProvider(ABC):
    @abstractmethod
    def route(self, waypoints: list[Coord]) -> RouteResult:
        """Route through waypoints in order, one leg per consecutive pair."""
        ...


def route_cache_key(waypoints: list[Coord]) -> str:
    """Cache key rounded to ~11m precision so repeat trips reliably hit cache."""
    rounded = ",".join(f"{w.lat:.4f}:{w.lon:.4f}" for w in waypoints)
    digest = hashlib.sha1(rounded.encode()).hexdigest()
    return f"route:{digest}"


def route_to_cache(result: RouteResult) -> dict:
    return {
        "legs": [(leg.distance_miles, leg.duration_minutes) for leg in result.legs],
        "geometry": result.geometry,
    }


def route_from_cache(data: dict) -> RouteResult:
    return RouteResult(
        legs=[RouteLeg(distance_miles=d, duration_minutes=m) for d, m in data["legs"]],
        geometry=[tuple(c) for c in data["geometry"]],
    )

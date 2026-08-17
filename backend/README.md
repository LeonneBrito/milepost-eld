# ELD Trip Planner — Backend

Django REST backend for the Spotter AI full-stack assessment. Given a
current location, pickup, dropoff, and current 70-hour/8-day cycle usage, it
returns a routed itinerary with every mandatory HOS stop, plus fully
computed daily ELD log sheets ready for the frontend to draw. See
`docs/design.md` (or the original design doc shared with this repo) for the
full spec this implements; this README covers setup, what's implemented,
and the assumptions baked into the regulatory simulation.

## Architecture

```
apps/
├── core/      exceptions.py (API error contract), health check
├── routing/   RoutingProvider / GeocodingProvider ABCs + OSRM, ORS,
│              Nominatim adapters, cached, with OSRM->ORS fallback
├── trips/     models, serializers, views, TripPlanner orchestration
└── hos/       pure domain library — no Django imports, no I/O:
               rules.py (Part 395 constants), engine.py (simulation),
               logsheet.py (day-splitting + totals)
```

`apps/hos` is deliberately framework-free: `engine.simulate()` takes a
distance/duration profile and a starting cycle balance and returns a list of
`Event`s; `logsheet.build()` turns those into per-calendar-day duty-status
segments. Both are pure functions, so the regulatory logic is unit-tested in
milliseconds with no database — see `tests/hos/`.

`apps/trips/services/planner.py` is the only module that touches both the
I/O layer (`apps/routing`) and the pure domain layer (`apps/hos`): it
geocodes the three locations, requests a route, runs the simulation,
interpolates stop coordinates along the route polyline, reverse-geocodes
stops with no inherent location (fuel/break/reset/restart), and persists
`Trip` / `Stop` / `LogDay` / `DutySegment` rows.

## Setup

```bash
cd backend
python -m venv .venv
.venv/Scripts/activate        # .venv/bin/activate on macOS/Linux
pip install -r requirements-dev.txt
cp .env.example .env          # defaults work as-is for local dev
python manage.py migrate
python manage.py createsuperuser   # optional, for /admin/
python manage.py runserver
```

Health check: `GET http://localhost:8000/api/health/`
API docs: `http://localhost:8000/api/docs/` (OpenAPI schema at `/api/schema/`)

## Running tests

```bash
pytest
```

32 tests, no network access required (routing/geocoding provider tests mock
`httpx`; the API test injects fixture providers). Runtime is well under a
second. The property-based tests in `tests/hos/test_logsheet.py` use
[Hypothesis](https://hypothesis.readthedocs.io/) to generate randomized
trips and assert the two invariants the design calls out explicitly: every
`LogDay`'s segments are contiguous and cover `[0, 1440)`, and its four
totals always sum to exactly 24 hours.

## API

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/api/trips/` | Plan a trip: geocode, route, simulate HOS, build logs, persist |
| `GET` | `/api/trips/{id}/` | Reload a previously planned trip (shareable URL) |
| `GET` | `/api/geocode/?q=` | Typeahead proxy to the geocoding provider, cached |
| `GET` | `/api/health/` | Uptime check |
| `GET` | `/api/docs/`, `/api/schema/` | Swagger UI / OpenAPI schema |

Errors follow one shape: `{"error": "<CODE>", "detail": "...", "field": "<field or null>"}`,
with `VALIDATION_ERROR` (400), `GEOCODING_FAILED` (400), `ROUTING_FAILED`
(502), and `UPSTREAM_TIMEOUT` (504).

## Regulatory assumptions

The engine implements 49 CFR Part 395 as described in the FMCSA *Interstate
Truck Driver's Guide to Hours of Service*, with the following explicit
simplifications — stated here so the model being graded is unambiguous:

- **Adverse driving conditions exception**: not applied.
- **Split sleeper berth (§395.1(g))**: not implemented. Every reset is a
  single 10-hour block, logged as Sleeper Berth.
- **Fuel stop duration**: 30 minutes, on-duty not driving. Part 395 sets no
  duration for fueling; this is an operational assumption. Fuel stops are
  inserted every 1,000 miles per the assessment brief (the regulation sets
  no interval either).
- **30-minute break**: logged **off duty**. It may legally be logged
  on-duty-not-driving or sleeper berth; off duty is the conventional choice.
- **34-hour restart**: only inserted when the 70-hour cycle is exhausted
  mid-trip — never chosen speculatively to "get ahead" of the clock.
- **8-day rolling window**: approximated. The driver's prior-8-day history
  is unknown to this system, so `current_cycle_used_hours` is treated as a
  single opening balance that only decreases via a 34-hour restart. Hours do
  not "roll off" a day at a time during the simulated trip. This is the
  correct reading of the input the brief provides, not an oversight.
- **Stop placement**: rest and fuel stops are placed at the interpolated
  point on the route polyline where the relevant clock expires — not at a
  real truck stop. No free, reliable truck-stop POI dataset fits the time
  budget. Coordinates are guaranteed to lie on the returned route geometry.
- **Pickup/dropoff duration**: 1 hour each, on-duty not driving, per the
  assessment brief.
- **Average speed**: derived per-leg from the routing provider's own
  `distance / duration`, not a fixed assumption — this keeps the map and the
  logs consistent with each other.

### Stop-selection priority (when driving is blocked)

Order matters and mirrors `apps/hos/engine.py`'s `_resolve_constraint`:

1. **Cycle exhausted** (≥70h used) → 34-hour restart; resets the cycle.
2. **11h driving or 14h window reached** → 10-hour reset (sleeper berth);
   resets the daily/window/break clocks, **not** the cycle.
3. **8h cumulative driving since the last break** → 30-minute break (off
   duty); resets only the break clock.
4. **1,000 miles since the last fuel stop** → 30-minute fuel stop (on duty).

The asymmetry worth remembering: a 10-hour reset also satisfies the 14-hour
window and the 30-minute break requirement, but does **not** reduce cycle
hours — only a 34-hour restart does.

## External services

| Service | Role | Notes |
|---|---|---|
| Nominatim (OSM) | Geocoding + reverse geocoding | Free, no key. Results cached (hashed keys, memcached-safe) for a week. Requires a real `User-Agent` — set `NOMINATIM_USER_AGENT` per its [usage policy](https://operations.osmfoundation.org/policies/nominatim/). |
| OSRM public demo | Routing | Free, best-effort, no SLA. Route results cached for a day, keyed on rounded coordinates. |
| OpenRouteService | Routing fallback | Used automatically if OSRM raises and `ORS_API_KEY` is set — see `apps/routing/factory.py`. |

Both providers sit behind `RoutingProvider`/`GeocodingProvider` ABCs
(`apps/routing/base.py`), so tests inject fixtures and the vendor can be
swapped via settings without touching call sites.

## Deployment

Backend → **Render** (see `render.yaml` at the repo root), frontend →
**Vercel**. A long-running Django service is a poor fit for Vercel's
serverless model; Render (or Railway/Fly) is simpler and gives a free
Postgres instance. `Procfile` runs migrations on release and serves via
Gunicorn; static files are served by WhiteNoise so no separate static host
is needed.

Required env vars in production: `SECRET_KEY`, `ALLOWED_HOSTS`,
`CORS_ALLOWED_ORIGINS` (set to the deployed frontend origin, not `*`),
`DATABASE_URL`, `NOMINATIM_USER_AGENT`. See `.env.example` for the full list.

## Out of scope

Per the assessment brief: map/log-grid rendering (frontend), authentication
and multi-tenant carriers, ELD hardware integration, the adverse-driving and
short-haul exceptions, and split sleeper berth.

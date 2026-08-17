# Milepost — Frontend

React SPA for the Spotter AI full-stack assessment. Collects four trip
inputs, submits them to the Django API, and renders the returned plan as an
interactive route map and a set of FMCSA daily log sheets drawn to look like
the real paper form. See `FRONTEND_SDD.md` (or the design doc shared with
this repo) for the full spec; this README covers setup and what's
implemented.

**The frontend does no HOS arithmetic.** Every timestamp, coordinate, and
duty segment arrives pre-computed from the API — the client renders,
navigates, and stays out of the way.

## Stack

Vite 5 + React 19 + TypeScript, Tailwind CSS v4 (`@theme` tokens, no
`tailwind.config.js`), TanStack Query v5, TanStack Form v1 + Zod, React
Router v7, React Leaflet + CARTO dark tiles, Vitest.

## Architecture

```
src/
├── app/            query client, router, providers
├── features/
│   ├── trip-form/      the input form — combobox-free location fields
│   │                    (see "Deviations from the design doc" below)
│   ├── route-map/       Leaflet map, stop markers, route polyline
│   ├── stop-timeline/   the stop list, hover-linked to the map
│   ├── hos-meters/       the 4-clock meter strip
│   └── log-sheet/       the paper log — the most-graded piece
│       ├── grid-geometry.ts   pure math (minute↔pixel, path building),
│       │                      unit-tested with no rendering involved
│       ├── LogGrid.tsx        the SVG grid + ink path
│       ├── LogSheet.tsx       paper card + sr-only accessible table
│       └── LogSheetPager.tsx  day paging, keyboard nav, print handling
├── lib/            typed API client, types mirroring the backend
│                    serializers, formatting helpers
├── components/ui/  small hand-rolled primitives (button, input, slider…)
└── pages/          PlanTripPage ("/"), TripPage ("/trip/:id")
```

## Setup

```bash
cd frontend
npm install
cp .env.example .env   # VITE_API_URL — defaults to http://localhost:8000
npm run dev
```

Runs at `http://localhost:3000` (fixed port — the backend's dev CORS config
allows exactly that origin).

## Running tests

```bash
npm run test        # vitest run
```

The log sheet's geometry module (`grid-geometry.ts`) has the unit test
coverage — path building, coordinate mapping, hour ticks. It's the one piece
of client-side logic worth testing in isolation; everything else is either
API-driven rendering or presentational.

## Deviations from the design doc

The design doc was written slightly ahead of the finalized backend contract.
Two things changed once the real API shape was confirmed:

- **`GET /api/geocode/`** returns a single best match (Nominatim, `limit=1`),
  not a list — so `LocationField` confirms one candidate inline instead of
  paging a `Command`/`Popover` combobox. The backend also always re-geocodes
  from free text on trip submission, so no lat/lon is stashed client-side.
- **The HOS meter strip** shows the *selected day's* clocks (driving,
  14-hour duty window, time since the last qualifying break, cycle used),
  derived from that day's already-computed segments and totals — not a
  live/real-time snapshot, since this is a planning tool, not an ELD device.
  The scans in `hos-meters/derive.ts` only measure elapsed time between
  segment boundaries the backend already decided; they never make a legality
  call themselves.

## Deployment

Vercel, pointed at the deployed Render API via `VITE_API_URL`. See the root
README for running both services together.

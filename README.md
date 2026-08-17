# Milepost

Full-stack take-home for Spotter AI: given a current location, pickup,
dropoff, and current 70-hour/8-day cycle usage, plan a route with every
mandatory HOS stop and render fully compliant FMCSA daily log sheets.

```
backend/    Django REST API — routing, HOS simulation, log-sheet generation
frontend/   React SPA — trip form, route map, and the paper log renderer
```

Each half has its own README with full setup, architecture, and the
assumptions baked into it: [`backend/README.md`](backend/README.md),
[`frontend/README.md`](frontend/README.md). This one is just the "run both
at once" quick start.

## Running both together

Two terminals, backend first (the frontend's dev server expects it at
`http://localhost:8000`).

**Terminal 1 — backend**

```bash
cd backend
python -m venv .venv
.venv/Scripts/activate        # .venv/bin/activate on macOS/Linux
pip install -r requirements-dev.txt
cp .env.example .env          # defaults work as-is for local dev
python manage.py migrate
python manage.py runserver    # http://localhost:8000
```

**Terminal 2 — frontend**

```bash
cd frontend
npm install
cp .env.example .env          # VITE_API_URL defaults to http://localhost:8000
npm run dev                   # http://localhost:3000
```

Open `http://localhost:3000`, fill in the trip form (e.g. Chicago, IL →
St. Louis, MO → Dallas, TX), and submit — that hits the real Django API,
which geocodes through Nominatim and routes through OSRM, so the first
request takes a few seconds. The port choice isn't arbitrary: the backend's
dev `CORS_ALLOWED_ORIGINS` only allows `http://localhost:3000`, so the
frontend's dev server is pinned to that port in `vite.config.ts`.

Useful checks while both are up:

- `GET http://localhost:8000/api/health/` — backend liveness
- `GET http://localhost:8000/api/docs/` — Swagger UI for the API
- `cd backend && pytest` — backend test suite (32 tests, no network needed)
- `cd frontend && npm run test` — frontend unit tests (log-sheet geometry)

## Deployment

Backend → Render (`render.yaml` at the repo root), frontend → Vercel. See
each README's "Deployment" section for the required environment variables.

## Design docs

The design docs this implements (backend architecture/regulatory
assumptions, frontend component spec) were shared alongside this repo and
aren't reproduced here — see each service's README for what was actually
built, including a couple of places the frontend diverges from the original
spec once the real API contract was finalized.

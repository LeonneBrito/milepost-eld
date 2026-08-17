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

Two supported paths — pick one, they're not meant to be run together:

- **Render + Vercel**: backend → Render (`render.yaml` at the repo root),
  frontend → Vercel. See each README's "Deployment" section for details.
- **Railway** (both services in one project): see below.

### Deploy to Railway

Railway doesn't read a single repo-root manifest the way Render's
`render.yaml` does — you create one service per app in the dashboard, each
pointed at a subdirectory, and each picks up its own `railway.json`
(`backend/railway.json`, `frontend/railway.json` — build/start commands and
health checks, already committed).

1. **New Project** → **Deploy from GitHub repo** → select this repo.
2. **Add the database**: `+ New` → `Database` → `PostgreSQL`.
3. **Add the backend service**: `+ New` → `GitHub Repo` → this repo again →
   in its Settings, set **Root Directory** to `backend`. It'll pick up
   `backend/railway.json` automatically.
4. **Add the frontend service** the same way, with **Root Directory** set
   to `frontend`.
5. For each service, `Settings` → `Networking` → `Generate Domain`, so both
   get a public `*.up.railway.app` URL.
6. Set environment variables (`Variables` tab per service):

   **Backend**
   | Key | Value |
   |---|---|
   | `DJANGO_SETTINGS_MODULE` | `config.settings.prod` |
   | `SECRET_KEY` | generate one (Railway's variable editor has a "generate" option), or `python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"` |
   | `DEBUG` | `False` |
   | `ALLOWED_HOSTS` | the backend's own `*.up.railway.app` domain from step 5 |
   | `CORS_ALLOWED_ORIGINS` | the frontend's `*.up.railway.app` domain from step 5 |
   | `DATABASE_URL` | `${{Postgres.DATABASE_URL}}` (references the Postgres service added in step 2 — adjust the name if you renamed it) |
   | `NOMINATIM_USER_AGENT` | e.g. `milepost (you@example.com)` — required by Nominatim's usage policy |
   | `ORS_API_KEY` | optional — OpenRouteService fallback if OSRM's demo server is unreachable |

   **Frontend**
   | Key | Value |
   |---|---|
   | `VITE_API_URL` | the backend's `*.up.railway.app` domain from step 5, e.g. `https://milepost-backend.up.railway.app` |

   Steps 5 and 6 are circular (each service's domain feeds the other's env
   vars), so generate both domains first, *then* fill in `ALLOWED_HOSTS`,
   `CORS_ALLOWED_ORIGINS`, and `VITE_API_URL`, then redeploy both.
7. Redeploy both services once the variables are set.

Health checks: `backend/railway.json` polls `/api/health/`,
`frontend/railway.json` polls `/`.

## Design docs

The design docs this implements (backend architecture/regulatory
assumptions, frontend component spec) were shared alongside this repo and
aren't reproduced here — see each service's README for what was actually
built, including a couple of places the frontend diverges from the original
spec once the real API contract was finalized.

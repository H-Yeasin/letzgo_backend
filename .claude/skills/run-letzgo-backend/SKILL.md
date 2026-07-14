---
name: run-letzgo-backend
description: Build, launch, and smoke-test the LetzGo backend API server. Use when asked to start the backend, run its tests, or verify API endpoints.
---

The LetzGo backend is a Python FastAPI server at [`letzgo_backend/`](../../). An agent drives it via `.claude/skills/run-letzgo-backend/smoke.sh` — a runner that launches the server, runs curl-based smoke tests, and stops it.

All paths below are relative to `letzgo_backend/`.

## Prerequisites

- Python 3.11+ (3.14 in this environment)
- pip packages (see requirements.txt)
- PostgreSQL database — the `.env` file has a working Supabase PostgreSQL connection string

## Setup

```bash
pip install -r requirements.txt
```

The `.env` at repo root provides the database URL, JWT secret, and other config. It uses a Supabase PostgreSQL instance. To use a local database, set `DATABASE_URL` to your local connection string.

## Build

No build step — this is a Python project. Run directly from source.

## Run (agent path)

Use the `smoke.sh` driver for launching, testing, and stopping:

```bash
# Full cycle: launch → smoke tests → stop
bash .claude/skills/run-letzgo-backend/smoke.sh

# Just launch the server (stays in background)
bash .claude/skills/run-letzgo-backend/smoke.sh --launch

# Run smoke tests against a running server
bash .claude/skills/run-letzgo-backend/smoke.sh --test

# Stop the server
bash .claude/skills/run-letzgo-backend/smoke.sh --stop
```

The server listens on **port 8000** by default. Override with `PORT=4000 ./smoke.sh`.

Logs → `/tmp/letzgo-backend.log`. PID file → `/tmp/letzgo-backend.pid`.

### Manual smoke test (curl)

```bash
curl -s http://localhost:8000/         # → {"app":"LetzGo","version":"0.1.0","status":"running"}
curl -s http://localhost:8000/health    # → {"status":"healthy"}
```

### API docs

When `DEBUG=true` (the default), Swagger UI and ReDoc are available:
- `http://localhost:8000/docs` — Swagger UI
- `http://localhost:8000/redoc` — ReDoc
- `http://localhost:8000/openapi.json` — OpenAPI schema

## Run (human path)

```bash
python scripts/run.py
# → Uvicorn running on http://0.0.0.0:8000. Ctrl-C to stop.
```

## Test

```bash
cd letzgo_backend
pytest
```

## Unauthenticated endpoints (no auth token needed)

- `GET /health`
- `GET /`
- `POST /api/v1/auth/register`
- `POST /api/v1/auth/login`

## Endpoints that use the database

- `POST /api/v1/auth/register` — creates a user
- `POST /api/v1/auth/login` — returns a JWT
- `GET /api/v1/users/me` — requires `Authorization: Bearer <jwt>`
- `POST /api/v1/pings` — create a ride ping (requires auth)
- See `/docs` (Swagger UI) for the full list

## Gotchas

- **Database must be reachable.** The server won't start if the database connection fails. The `.env` uses a Supabase PostgreSQL pooler URL. If it's unreachable, replace `DATABASE_URL` with a local PostgreSQL instance or a cloud connection string you have access to.
- **Hot reload is on by default.** `scripts/run.py` passes `reload=True` to uvicorn. For production-like testing, run without reload: `uvicorn app.main:app --host 0.0.0.0 --port 8000`.
- **Rate limiting is active.** `slowapi` limits are in place. If you get 429 responses, you're being rate-limited.
- **Redis is optional.** The `REDIS_URL` env var is commented out in `.env` — Redis features are not enabled by default.

## Troubleshooting

- **`ModuleNotFoundError: No module named 'geoalchemy2'`**: dependencies not installed. Run `pip install -r requirements.txt`.
- **Server starts but 404s everything**: the server is the hot-reload parent process — wait for "Application startup complete" in logs.
- **`Relation "users" does not exist`**: database hasn't been migrated. Run `alembic upgrade head`.

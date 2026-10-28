#!/usr/bin/env bash
# Production entrypoint for the Dastyor backend.
#
# Usage on a host (Render/Railway/Fly/plain VPS):
#     ./start.sh
#
# Everything is read from the environment — see .env.example for the full
# list. Nothing here contains secrets.
set -euo pipefail

# Most managed hosts inject the port they routed to your service. Fall
# back to 8586, which is what the Dockerfile EXPOSEs.
PORT="${PORT:-8586}"
HOST="${HOST:-0.0.0.0}"

# Single worker on purpose. The daily AI-call counter in app/ai_service.py
# lives in process memory, not the database, so a second worker would keep
# its own count and the cap would silently stop being enforced. Move that
# counter to Postgres/Redis before raising this.
WORKERS="${WEB_CONCURRENCY:-1}"

if [ -z "${DATABASE_URL:-}" ]; then
    echo "FATAL: DATABASE_URL is not set. Copy .env.example to .env (or set" >&2
    echo "       the variables in your host's dashboard) before starting." >&2
    exit 1
fi

if [ -z "${AI_API_KEY:-}" ]; then
    echo "WARNING: AI_API_KEY is empty — every generation will fail until" >&2
    echo "         at least one AI key is configured." >&2
fi

# Tables are created on startup by app/database.py's create_all (see the
# lifespan handler in app/main.py), so there is no separate migration step
# to run here.
echo "Starting Dastyor backend on ${HOST}:${PORT} (workers=${WORKERS})"
exec uvicorn app.main:app \
    --host "$HOST" \
    --port "$PORT" \
    --workers "$WORKERS" \
    --proxy-headers \
    --forwarded-allow-ips '*'

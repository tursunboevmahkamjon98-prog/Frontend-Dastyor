#!/usr/bin/env bash
# Production entrypoint for the Dastyor frontend (Next.js).
#
#     ./start.sh
#
# Everything is read from the environment — nothing here holds a secret.
# See .env.production.example for the full list.
set -euo pipefail

cd "$(dirname "$0")"

PORT="${PORT:-8090}"

# Deliberately BIND_HOST and not HOSTNAME. Bash sets HOSTNAME itself, to
# the machine's name, on every shell — so "${HOSTNAME:-0.0.0.0}" never
# reaches its default and the server binds to the machine name instead of
# all interfaces. That looks like it worked (the server prints Ready) and
# then refuses every connection to 127.0.0.1, which is exactly what a
# reverse proxy in front of it will be using.
BIND_HOST="${BIND_HOST:-0.0.0.0}"

# Where /api and /uploads get forwarded (see next.config.ts). Read when
# THIS process starts, so pointing the site at a different backend is a
# restart, not a rebuild.
export BACKEND_ORIGIN="${BACKEND_ORIGIN:-http://localhost:8009}"

# ── Checks that fail loudly here instead of quietly at 3am ──────────────

if [ ! -d node_modules ]; then
    echo "FATAL: node_modules is missing. Run 'npm ci' first." >&2
    exit 1
fi

SERVER=".next/standalone/server.js"
if [ ! -f "$SERVER" ]; then
    echo "FATAL: there is no build to serve ($SERVER is missing)." >&2
    echo "       Run 'npm run build' first — and read the note below about" >&2
    echo "       NEXT_PUBLIC_API_URL, because it is baked in at BUILD time." >&2
    exit 1
fi

# NEXT_PUBLIC_* values are compiled into the browser bundle by `npm run
# build`; setting one here changes nothing at all. Saying so out loud
# because the failure is otherwise baffling: the variable is plainly set
# in the environment, and the browser still calls the old address.
if [ -n "${NEXT_PUBLIC_API_URL:-}" ]; then
    echo "NOTE: NEXT_PUBLIC_API_URL is set in this environment, but it only" >&2
    echo "      takes effect at BUILD time. If it changed, rebuild:" >&2
    echo "      NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL npm run build" >&2
fi

# next.config.ts sets output:"standalone", which means `next start` is NOT
# the way to run this — Next refuses it with a warning and serves nothing
# useful. server.js is self-contained, but Next leaves the static assets
# out of it on purpose (the Dockerfile copies them in as separate layers),
# so a plain host has to place them itself. Copied on every start rather
# than once: it is a few MB, and the alternative is a rebuild silently
# serving yesterday's CSS.
mkdir -p .next/standalone/.next
cp -r .next/static .next/standalone/.next/
[ -d public ] && cp -r public .next/standalone/

# A backend that isn't answering is worth one line now rather than a
# stream of 502s later. Not fatal: the backend may simply be starting in
# parallel, and refusing to serve the site over that would be worse.
if command -v curl >/dev/null 2>&1; then
    if ! curl -fsS --max-time 3 "${BACKEND_ORIGIN}/api/health" >/dev/null 2>&1; then
        echo "WARNING: no healthy backend at ${BACKEND_ORIGIN}/api/health —" >&2
        echo "         the site will load but every API call will fail." >&2
    fi
fi

echo "Starting Dastyor frontend on ${BIND_HOST}:${PORT}"
echo "  proxying /api and /uploads -> ${BACKEND_ORIGIN}"

# server.js reads these two by name; HOSTNAME is its own spelling for the
# bind address, which is why BIND_HOST is translated into it only here.
export PORT
export HOSTNAME="$BIND_HOST"
exec node "$SERVER"

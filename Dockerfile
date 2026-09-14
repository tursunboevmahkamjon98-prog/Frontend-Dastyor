# ── deps ─────────────────────────────────────────────────────────────────
FROM node:20-alpine AS deps
WORKDIR /app
# Only the manifests, so this layer (the slow one) is reused on every
# build where the dependencies did not change.
COPY package.json package-lock.json ./
RUN npm ci

# ── build ────────────────────────────────────────────────────────────────
FROM node:20-alpine AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .

# Baked into the client bundle at build time (the Next.js NEXT_PUBLIC_*
# rule) — it CANNOT be changed later by setting an env var on the running
# container. Two sane values:
#
#   /api                        the browser calls this same server and
#                               next.config.ts's rewrites forward it to
#                               BACKEND_ORIGIN. No CORS, backend never
#                               exposed publicly. This is the default.
#
#   https://api.example.com/api the browser calls the backend directly.
#                               Then that origin must appear in the
#                               backend's CORS_ORIGINS or every request
#                               fails in the browser only.
ARG NEXT_PUBLIC_API_URL=/api
ARG NEXT_PUBLIC_GOOGLE_CLIENT_ID
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
ENV NEXT_PUBLIC_GOOGLE_CLIENT_ID=$NEXT_PUBLIC_GOOGLE_CLIENT_ID

# BACKEND_ORIGIN is ALSO a build-time value, despite being a plain
# (non-NEXT_PUBLIC_) variable read server-side — next.config.ts uses it
# inside rewrites(), and Next calls rewrites() during `next build`, then
# serializes the resolved destination strings into routes-manifest.json /
# required-server-files.json. The standalone server reads those manifests
# at boot; it never re-evaluates next.config.ts. Confirmed by grepping a
# real build: the literal origin appears in routes-manifest.json,
# required-server-files.json AND server.js.
#
# This cost a live outage: compose passed BACKEND_ORIGIN only as a
# runtime `environment:`, so the image shipped with next.config.ts's
# localhost fallback baked in, and every /api/* call proxied to a port
# inside the frontend's own container — nginx passed the resulting Next
# 500 straight through, while the backend itself was healthy the whole
# time. The runtime ENV further down is kept, but it is NOT what makes
# the proxy work; this ARG is.
ARG BACKEND_ORIGIN=http://backend:8586
ENV BACKEND_ORIGIN=$BACKEND_ORIGIN
RUN npm run build

# ── runtime ──────────────────────────────────────────────────────────────
FROM node:20-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production

# curl for the healthcheck below; --no-cache so it does not leave an apk
# index behind in the layer.
RUN apk add --no-cache curl

# Never run the server as root: a bug in a dependency then owns a
# throwaway account rather than the container.
RUN addgroup --system --gid 1001 nodejs \
    && adduser --system --uid 1001 nextjs

# next.config.ts's output:"standalone" produces a minimal server.js plus
# only the node_modules each page actually needs — no full npm install in
# this final layer.
COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs

# Unlike NEXT_PUBLIC_* above, this one IS a real runtime variable: it is
# read when the server starts, so the same image can be pointed at a
# different backend with `docker run -e BACKEND_ORIGIN=...` and no
# rebuild. Defaults to the compose service name + the port backend/
# Dockerfile actually listens on (8586), NOT "localhost" — inside Docker
# "localhost" is this container, so a localhost default is wrong for
# every case this image is built for. docker-compose.yml sets the same
# value explicitly; this just makes a bare `docker run` behave sanely
# on a network where a container named "backend" exists.
ENV BACKEND_ORIGIN=http://backend:8586

EXPOSE 8090
ENV PORT=8090
ENV HOSTNAME=0.0.0.0

# Hits the app itself, not the backend: this reports whether the web
# server is serving, which is what the orchestrator can actually act on
# by restarting. A backend outage is the backend's healthcheck to fail.
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -f http://localhost:8090/ || exit 1

CMD ["node", "server.js"]

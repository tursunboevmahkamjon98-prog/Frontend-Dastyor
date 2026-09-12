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
# rebuild. Inside Docker, "localhost" is this container — use the
# compose service name (e.g. http://backend:8001) or a real host.
ENV BACKEND_ORIGIN=http://localhost:8009

EXPOSE 8090
ENV PORT=8090
ENV HOSTNAME=0.0.0.0

# Hits the app itself, not the backend: this reports whether the web
# server is serving, which is what the orchestrator can actually act on
# by restarting. A backend outage is the backend's healthcheck to fail.
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl -f http://localhost:8090/ || exit 1

CMD ["node", "server.js"]

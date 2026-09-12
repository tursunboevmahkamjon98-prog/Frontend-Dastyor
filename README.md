# Dastyor — frontend

Next.js 16 (App Router) frontend for Dastyor, the AI teaching-materials
platform for schools in Tajikistan. Three interface languages: Tajik,
Russian and English.

The backend (FastAPI) lives in a separate, private repository. This one
holds no keys, no passwords and no database — it is safe to be public.

---

## Quick start

```bash
npm ci
npm run dev          # http://localhost:3000
```

Development needs no configuration: `next.config.ts` forwards `/api` to
`http://localhost:8009` unless told otherwise.

---

## Production

```bash
npm ci
NEXT_PUBLIC_API_URL=/api npm run build
BACKEND_ORIGIN=http://127.0.0.1:8009 ./start.sh     # port 8090
```

`start.sh` checks the build exists, warns if the backend is unreachable,
copies the static assets into place and starts the server. Override
`PORT`, `BIND_HOST` or `BACKEND_ORIGIN` in the environment.

### The one thing that catches everybody

`NEXT_PUBLIC_*` variables are compiled **into the browser bundle** when
you run `npm run build`. Setting one on a running server changes nothing.
If the API address changes, you must **rebuild** — restarting is not
enough.

Everything else (`BACKEND_ORIGIN`, `PORT`, `BIND_HOST`) is read at server
start, so those only need a restart.

### Two ways to reach the API

| `NEXT_PUBLIC_API_URL` | What happens | CORS |
|---|---|---|
| `/api` *(recommended)* | Browser calls this server; it forwards to `BACKEND_ORIGIN` | Nothing to configure, and the backend never needs a public address |
| `https://api.example.com/api` | Browser calls the backend directly | That exact origin must be in the backend's `CORS_ORIGINS` |

See `.env.production.example` for every variable.

---

## Docker

```bash
docker build -t dastyor-frontend \
  --build-arg NEXT_PUBLIC_API_URL=/api .

docker run -p 8090:8090 \
  -e BACKEND_ORIGIN=http://backend:8001 \
  dastyor-frontend
```

Multi-stage, runs as a non-root user, and ships only Next's
`output: "standalone"` bundle rather than the full `node_modules`.

Inside a container `localhost` means the container itself — point
`BACKEND_ORIGIN` at the compose service name or a real host.

---

## Behind nginx

```nginx
location / {
    proxy_pass http://127.0.0.1:8090;
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-For $remote_addr;
}
```

If the frontend proxies the API (`NEXT_PUBLIC_API_URL=/api`), that single
block is the whole configuration — `/api` and `/uploads` travel through
the same server.

Generating materials can take minutes, so give the proxy room:
`proxy_read_timeout 300s;`

---

## Layout

```
src/app/          routes (App Router)
src/components/   shared UI
src/lib/          API client, i18n messages, material types
public/           static assets
```

## Scripts

| Command | Does |
|---|---|
| `npm run dev` | development server |
| `npm run build` | production build |
| `npm run lint` | eslint |
| `./start.sh` | serve the production build on 8090 |

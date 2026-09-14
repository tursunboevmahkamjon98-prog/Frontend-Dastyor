import type { NextConfig } from "next";

// Where this server forwards /api and /uploads.
//
// Read at BUILD time, not at server start — this comment used to claim
// the opposite ("changing it needs a restart, not a rebuild") and that
// was simply wrong. Next calls rewrites() during `next build` and writes
// the resolved destination into .next/routes-manifest.json and
// .next/required-server-files.json; the standalone server reads those at
// boot and never re-evaluates this file. Verified by grepping a real
// build for the literal origin — it is in both manifests and server.js.
//
// Consequence, learned the hard way on a live deploy: setting
// BACKEND_ORIGIN only as a runtime env var on the container does
// NOTHING. The image ships with whatever value was present at build, so
// a production frontend built without it proxies /api to the localhost
// fallback below, inside its own container, where nothing is listening —
// the site loads fine and every single API call 500s. Docker builds must
// pass it via --build-arg / compose's build.args (both are set up in
// this repo's Dockerfile and docker-compose.yml).
//
// The localhost fallback is kept so plain local development (backend run
// directly on the host, port 8009 — see README) needs no .env at all.
const BACKEND_ORIGIN =
  process.env.BACKEND_ORIGIN?.replace(/\/+$/, "") ?? "http://localhost:8009";

const nextConfig: NextConfig = {
  // Hides the floating "N" dev-mode build-activity badge (dev-only, never
  // shows in production builds) — purely cosmetic, distracting during testing.
  devIndicators: false,
  // Bundles a minimal, self-contained server (only the deps each page
  // actually uses) into .next/standalone — lets the Docker image skip
  // shipping the full node_modules tree. Dev (`next dev`) is unaffected.
  output: "standalone",
  // Next's built-in rewrites() proxy (below) kills the upstream connection
  // after 30s by default (see next/dist/server/lib/router-utils/
  // proxy-request.js) — fine for normal API calls, but /materials/
  // generate-all fans out 4 AI calls at once and Cerebras's free-tier rate
  // limit (429 "tokens per minute") makes each one retry with 2s sleeps
  // across up to 5 keys, easily pushing total time past 30s. When that
  // happened the proxy would abort with ECONNRESET and the frontend showed
  // an error — even though the backend, unaware its client disconnected,
  // kept going and saved the materials anyway (confusing: "creation
  // failed" but the materials show up in the list moments later). 5
  // minutes comfortably covers the slowest realistic generate-all.
  experimental: {
    proxyTimeout: 300000,
  },
  // Lets ONE public URL (e.g. a Cloudflare Tunnel pointed only at this
  // Next.js server, port 3000) serve both the site and the API — the
  // browser calls same-origin /api/... and /uploads/..., and this server
  // silently forwards those to the FastAPI backend on localhost:8001.
  // Set up for a home-laptop deployment specifically because a free
  // `cloudflared tunnel --url` gets a NEW random *.trycloudflare.com
  // domain on every restart: without this, the backend would need its own
  // separate tunnel whose URL would have to be copied into
  // NEXT_PUBLIC_API_URL and rebuilt every time it changed. With it,
  // NEXT_PUBLIC_API_URL is just the relative path "/api" — nothing to
  // update, ever, no matter what the tunnel URL is this session.
  async rewrites() {
    return [
      { source: "/api/:path*", destination: `${BACKEND_ORIGIN}/api/:path*` },
      { source: "/uploads/:path*", destination: `${BACKEND_ORIGIN}/uploads/:path*` },
    ];
  },
  // Cloudflare quick tunnels get a new random *.trycloudflare.com host each
  // restart — allow any subdomain of it so the dev server's HMR/static
  // chunks aren't blocked as cross-origin (see run log warning this fixes).
  allowedDevOrigins: ["*.trycloudflare.com"],
};

export default nextConfig;

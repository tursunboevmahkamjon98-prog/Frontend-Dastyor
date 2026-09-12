import type { NextConfig } from "next";

// Where this server forwards /api and /uploads. Read at SERVER start, not
// at build time — unlike NEXT_PUBLIC_*, changing it needs a restart, not a
// rebuild, so one image can be pointed at staging or production.
//
// It used to be the literal "http://localhost:8009", which is correct on
// the laptop and wrong everywhere else: on a hosting box nothing answers
// on localhost:8009, so every proxied call 502s while the site itself
// loads fine — a login page that looks healthy and cannot log anyone in.
// The default is kept so local development still needs no .env at all.
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

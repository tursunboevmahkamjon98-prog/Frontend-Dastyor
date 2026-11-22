import type { NextConfig } from "next";
import { BILLING_ENABLED } from "./src/lib/features";










const BACKEND_ORIGIN =
  process.env.BACKEND_ORIGIN?.replace(/\/+$/, "") ?? "http://localhost:8010";

const nextConfig: NextConfig = {
  
  
  devIndicators: false,
  
  
  
  output: "standalone",
  // Keep development/build artifacts separate from the stale .next output.
  // This prevents Turbopack from reprocessing a concurrent standalone build.
  distDir: ".next-dev",
  async redirects() {
    return BILLING_ENABLED ? [] : [{
      source: "/dashboard/billing/:path*",
      destination: "/dashboard",
      permanent: false,
    }];
  },
  
  
  
  
  
  
  
  
  
  
  
  experimental: {
    proxyTimeout: 300000,
  },
  
  
  
  
  
  
  
  
  
  
  
  async rewrites() {
    return [
      { source: "/api/:path*", destination: `${BACKEND_ORIGIN}/api/:path*` },
      { source: "/uploads/:path*", destination: `${BACKEND_ORIGIN}/uploads/:path*` },
    ];
  },
  
  
  
  allowedDevOrigins: ["*.trycloudflare.com", "127.0.0.1", "localhost"],
};

export default nextConfig;

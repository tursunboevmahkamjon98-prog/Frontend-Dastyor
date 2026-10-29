import type { NextConfig } from "next";










const BACKEND_ORIGIN =
  process.env.BACKEND_ORIGIN?.replace(/\/+$/, "") ?? "http://localhost:8009";

const nextConfig: NextConfig = {
  
  
  devIndicators: false,
  
  
  
  output: "standalone",
  
  
  
  
  
  
  
  
  
  
  
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

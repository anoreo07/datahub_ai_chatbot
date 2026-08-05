import type { NextConfig } from "next";

const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:8000";

const nextConfig: NextConfig = {
  // Proxy backend calls through Next so the browser stays same-origin
  // and no CORS changes are required on the FastAPI side. Streaming
  // (SSE) responses pass through untouched.
  async rewrites() {
    return [
      { source: "/api/:path*", destination: `${BACKEND_URL}/api/:path*` },
      { source: "/ready/:path*", destination: `${BACKEND_URL}/ready/:path*` },
      { source: "/ready", destination: `${BACKEND_URL}/ready` },
    ];
  },
};

export default nextConfig;
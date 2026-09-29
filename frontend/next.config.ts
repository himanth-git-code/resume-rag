import type { NextConfig } from "next";

const backendUrl = process.env.BACKEND_URL ?? "http://localhost:8000";

const nextConfig: NextConfig = {
  // The browser only calls same-origin paths; Next proxies them to Django and
  // sets X-Forwarded-Host so Django builds URLs for the frontend origin.
  async rewrites() {
    return [
      // Django REST routes end with "/", Next strips trailing slashes, so re-add it here.
      {
        source: "/api/:path*",
        destination: `${backendUrl}/api/:path*/`,
      },
      // allauth headless API (no trailing slashes) — forwarded unchanged.
      {
        source: "/_allauth/:path*",
        destination: `${backendUrl}/_allauth/:path*`,
      },
      // OAuth provider callbacks (e.g. /accounts/google/login/callback/).
      {
        source: "/accounts/:path*",
        destination: `${backendUrl}/accounts/:path*/`,
      },
    ];
  },
};

export default nextConfig;

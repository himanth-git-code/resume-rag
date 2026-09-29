import type { NextConfig } from "next";

const backendUrl = process.env.BACKEND_URL ?? "http://localhost:8000";

const nextConfig: NextConfig = {
  // The browser only calls same-origin /api/*; Next proxies to Django.
  // Django routes end with "/", Next strips trailing slashes, so re-add it here.
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${backendUrl}/api/:path*/`,
      },
    ];
  },
};

export default nextConfig;

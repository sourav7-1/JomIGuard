import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  experimental: { useTypeScriptCli: true },
  cacheComponents: true,
  partialPrefetching: true,
  async rewrites() {
    const backend = process.env.BACKEND_INTERNAL_URL || "http://localhost:8000";
    return [{ source: "/api/:path*", destination: `${backend}/:path*` }];
  },
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
};

export default nextConfig;

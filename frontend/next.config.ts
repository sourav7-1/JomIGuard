import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  experimental: {
    useTypeScriptCli: true,
    // Every page sits behind the client-side AuthGuard, which holds the page back until the
    // session is confirmed, so dev-only instant-navigation validation reported every route as
    // a "dropped segment". Validate only segments that opt in with `export const instant`.
    instantInsights: { validationLevel: "manual-warning" },
  },
  cacheComponents: true,
  partialPrefetching: true,
  async rewrites() {
    const backend = process.env.BACKEND_INTERNAL_URL || "http://localhost:8000";
    // FastAPI's docs/schema stay on the backend port only; the public proxy never forwards them
    return [
      {
        source: "/api/:path((?!(?:docs|redoc|openapi\\.json)(?:/|$)).*)",
        destination: `${backend}/:path`,
      },
    ];
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

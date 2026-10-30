import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Build plain HTML/JS/CSS into out/ for a static host (Firebase Hosting).
  // The site has no server code: the browser talks to the API directly.
  // (So no cacheComponents / partialPrefetching: both need a Next.js server.)
  output: "export",
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

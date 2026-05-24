import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000",
  },
  // Empty turbopack config to enable Turbopack (Next.js 16 default)
  turbopack: {},
};

export default nextConfig;

import type { NextConfig } from "next"
import path from "path"

const nextConfig: NextConfig = {
  // Pin Turbopack root so it doesn't pick up another lockfile outside ./frontend
  turbopack: {
    root: __dirname,
  },
  webpack: (config) => {
    // Ensure @/* alias resolves both in webpack and during type checking
    config.resolve.alias = {
      ...(config.resolve.alias || {}),
      "@": path.join(__dirname),
    }
    return config
  },
}

export default nextConfig

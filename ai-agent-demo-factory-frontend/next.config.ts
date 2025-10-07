import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: 'standalone',
  eslint: {
    ignoreDuringBuilds: true,
  },
  webpack: (config, { isServer }) => {
    // Fix for Windows EISDIR issue
    config.resolve.symlinks = false;
    return config;
  },
};

export default nextConfig;

import type { NextConfig } from 'next';

const nextConfig: NextConfig = {
  // Phones on your Wi-Fi: next dev blocks its JS bundles from non-localhost origins otherwise.
  allowedDevOrigins: ['192.168.*.*', '10.*.*.*', '172.16.*.*', '*.local'],
  devIndicators: false,
  poweredByHeader: false,
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: 'http://127.0.0.1:8000/api/:path*',
        
      },
    ];
  },
};

export default nextConfig;

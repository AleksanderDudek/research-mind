import type { NextConfig } from 'next'

const config: NextConfig = {
  async rewrites() {
    return [
      {
        source: '/api/backend/:path*',
        destination: `${process.env.BACKEND_URL ?? 'http://localhost:8001'}/:path*`,
      },
    ]
  },
}

export default config

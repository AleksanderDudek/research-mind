import type { NextConfig } from 'next'

const config: NextConfig = {
  output: 'export',
  // basePath is set by NEXT_PUBLIC_BASE_PATH at build time (e.g. /research-mind for GitHub Pages).
  // Empty string in local dev — the env var is not set there.
  basePath: process.env.NEXT_PUBLIC_BASE_PATH ?? '',
  trailingSlash: true,
  images: { unoptimized: true },
}

export default config

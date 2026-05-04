'use client'

import { createBrowserClient } from '@supabase/ssr'

// Empty-string fallbacks prevent a build-time crash when env vars are absent
// during SSR pre-rendering. At runtime in the browser the real values are used.
export const supabase = createBrowserClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL  ?? '',
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY ?? '',
)

export type AppRole = 'superadmin' | 'admin' | 'user'

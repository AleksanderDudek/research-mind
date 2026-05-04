'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useLocale } from 'next-intl'
import { supabase } from '@/lib/supabase'

/**
 * Supabase redirects here after email magic-link clicks.
 * The URL fragment contains the access + refresh tokens; Supabase SSR
 * exchanges them automatically — we just need to wait and redirect.
 */
export default function AuthCallbackPage() {
  const router = useRouter()
  const locale = useLocale()

  useEffect(() => {
    supabase.auth.onAuthStateChange((event) => {
      if (event === 'SIGNED_IN') {
        router.push(`/${locale}`)
      }
    })
  }, [router, locale])

  return (
    <div className="min-h-dvh flex items-center justify-center bg-background">
      <p className="text-muted-foreground animate-pulse">Signing you in…</p>
    </div>
  )
}

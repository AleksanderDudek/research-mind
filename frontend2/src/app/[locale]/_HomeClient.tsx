'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { useLocale } from 'next-intl'
import { supabase, type AppRole } from '@/lib/supabase'
import { useAppStore } from '@/lib/store'
import { ContextPanel } from '@/components/context/ContextPanel'
import { ContextView }  from '@/components/context/ContextView'

export default function HomeClient() {
  const router        = useRouter()
  const locale        = useLocale()
  const activeContext = useAppStore(s => s.activeContext)
  const setAuth       = useAppStore(s => s.setAuth)
  const clearAuth     = useAppStore(s => s.clearAuth)
  const [ready, setReady] = useState(false)

  useEffect(() => {
    const init = async () => {
      const { data: { session } } = await supabase.auth.getSession()
      if (!session) {
        clearAuth()
        router.replace(`/${locale}/auth/login`)
        return
      }

      // Load profile (org_id + role) from Supabase
      const { data: profile } = await supabase
        .from('profiles')
        .select('org_id, role, full_name')
        .eq('id', session.user.id)
        .single()

      if (profile) {
        setAuth(
          session.user.id,
          profile.org_id ?? '',
          (profile.role ?? 'user') as AppRole,
          profile.full_name ?? session.user.email ?? '',
        )
      }
      setReady(true)
    }

    init()

    const { data: { subscription } } = supabase.auth.onAuthStateChange(async (event, session) => {
      if (event === 'SIGNED_OUT' || !session) {
        clearAuth()
        router.replace(`/${locale}/auth/login`)
      }
    })

    return () => subscription.unsubscribe()
  }, [locale, router, setAuth, clearAuth])

  if (!ready) {
    return (
      <div className="min-h-dvh flex items-center justify-center bg-background">
        <p className="text-muted-foreground animate-pulse">Loading…</p>
      </div>
    )
  }

  return activeContext ? <ContextView /> : <ContextPanel />
}

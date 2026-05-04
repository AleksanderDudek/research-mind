'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { supabase, type AppRole } from '@/lib/supabase'
import { useAppStore } from '@/lib/store'
import { ContextPanel } from '@/components/context/ContextPanel'
import { ContextView }  from '@/components/context/ContextView'

export default function HomeClient() {
  const router        = useRouter()
  const activeContext = useAppStore(s => s.activeContext)
  const setAuth       = useAppStore(s => s.setAuth)
  const setLang       = useAppStore(s => s.setLang)
  const clearAuth     = useAppStore(s => s.clearAuth)
  const [ready, setReady] = useState(false)

  useEffect(() => {
    const init = async () => {
      const { data: { session } } = await supabase.auth.getSession()
      if (!session) {
        clearAuth()
        router.replace('/auth/login')
        return
      }

      // Fetch core profile fields. language is optional — queried separately
      // so a missing column never blocks the entire login.
      const { data: profile, error: profileErr } = await supabase
        .from('profiles')
        .select('org_id, role, full_name')
        .eq('id', session.user.id)
        .single()

      if (profileErr || !profile) {
        // Profile row missing (registered before trigger, or DB error).
        // Log it clearly and continue as a plain user so the app still loads.
        console.error('[auth] profile not found:', profileErr?.message ?? 'no row')
        setReady(true)
        return
      }

      setAuth(
        session.user.id,
        profile.org_id ?? '',
        (profile.role ?? 'user') as AppRole,
        profile.full_name ?? session.user.email ?? '',
      )

      // Language preference is optional — gracefully ignore if column absent
      const { data: langRow } = await supabase
        .from('profiles')
        .select('language')
        .eq('id', session.user.id)
        .single()

      if (langRow?.language) setLang(langRow.language as 'en' | 'pl')

      setReady(true)
    }

    init()

    const { data: { subscription } } = supabase.auth.onAuthStateChange(async (event, session) => {
      if (event === 'SIGNED_OUT' || !session) {
        clearAuth()
        router.replace('/auth/login')
      }
    })

    return () => subscription.unsubscribe()
  }, [router, setAuth, setLang, clearAuth])

  if (!ready) {
    return (
      <div className="min-h-dvh flex items-center justify-center bg-background">
        <p className="text-muted-foreground animate-pulse">Loading…</p>
      </div>
    )
  }

  return activeContext ? <ContextView /> : <ContextPanel />
}

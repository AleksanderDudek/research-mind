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

      const { data: profile } = await supabase
        .from('profiles')
        .select('org_id, role, full_name, language')
        .eq('id', session.user.id)
        .single()

      if (profile) {
        setAuth(
          session.user.id,
          profile.org_id ?? '',
          (profile.role ?? 'user') as AppRole,
          profile.full_name ?? session.user.email ?? '',
        )
        if (profile.language) setLang(profile.language as 'en' | 'pl')
      }
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

'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { supabase, type AppRole } from '@/lib/supabase'
import { useAppStore } from '@/lib/store'
import { RouteGuard } from '@/components/auth/RouteGuard'
import { ContextPanel } from '@/components/context/ContextPanel'
import { ContextView }  from '@/components/context/ContextView'

export default function HomeClient() {
  const router        = useRouter()
  const activeContext = useAppStore(s => s.activeContext)
  const setAuth       = useAppStore(s => s.setAuth)
  const setAuthReady  = useAppStore(s => s.setAuthReady)
  const setLang       = useAppStore(s => s.setLang)
  const clearAuth     = useAppStore(s => s.clearAuth)

  useEffect(() => {
    const init = async () => {
      const { data: { session } } = await supabase.auth.getSession()
      if (!session) {
        clearAuth()          // also sets authReady: false
        router.replace('/auth/login')
        return
      }

      // Fetch core profile fields (language queried separately — optional column)
      const { data: profile, error: profileErr } = await supabase
        .from('profiles')
        .select('org_id, role, full_name')
        .eq('id', session.user.id)
        .single()

      if (profileErr || !profile) {
        console.error('[auth] profile missing:', profileErr?.message ?? 'no row')
        // Profile row doesn't exist yet (e.g. trigger hasn't fired).
        // Treat as a plain authenticated user so the app loads gracefully.
        setAuth(session.user.id, '', 'user', session.user.email ?? '')
      } else {
        setAuth(
          session.user.id,
          profile.org_id ?? '',
          (profile.role ?? 'user') as AppRole,
          profile.full_name ?? session.user.email ?? '',
        )

        // Language preference is optional (column may not exist yet)
        const { data: langRow } = await supabase
          .from('profiles')
          .select('language')
          .eq('id', session.user.id)
          .single()

        if (langRow?.language) setLang(langRow.language as 'en' | 'pl')
      }

      setAuthReady(true)
    }

    init()

    const { data: { subscription } } = supabase.auth.onAuthStateChange(async (event, session) => {
      if (event === 'SIGNED_OUT' || !session) {
        clearAuth()
        router.replace('/auth/login')
      }
    })

    return () => subscription.unsubscribe()
  }, [router, setAuth, setAuthReady, setLang, clearAuth])

  return (
    <RouteGuard require="auth">
      {activeContext ? <ContextView /> : <ContextPanel />}
    </RouteGuard>
  )
}

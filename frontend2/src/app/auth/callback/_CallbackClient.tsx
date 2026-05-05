'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { supabase } from '@/lib/supabase'

export default function CallbackClient() {
  const router = useRouter()

  useEffect(() => {
    const { data: { subscription } } = supabase.auth.onAuthStateChange((event) => {
      if (event === 'SIGNED_IN') router.push('/')
    })
    return () => subscription.unsubscribe()
  }, [router])

  return (
    <div className="min-h-dvh flex items-center justify-center bg-background">
      <p className="text-muted-foreground animate-pulse">Signing you in…</p>
    </div>
  )
}

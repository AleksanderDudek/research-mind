'use client'

import { useState } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { useTranslations } from 'next-intl'
import { supabase } from '@/lib/supabase'
import { Button } from '@/components/ui/button'
import { Input  } from '@/components/ui/input'

export default function LoginClient() {
  const t      = useTranslations()
  const router = useRouter()

  const [email,    setEmail]    = useState('')
  const [password, setPassword] = useState('')
  const [error,    setError]    = useState<string | null>(null)
  const [loading,  setLoading]  = useState(false)

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setLoading(true)
    const { error: authErr } = await supabase.auth.signInWithPassword({ email, password })
    setLoading(false)
    if (authErr) { setError(authErr.message); return }
    router.push('/')
  }

  return (
    <div className="min-h-dvh flex items-center justify-center bg-background px-4">
      <div className="w-full max-w-sm space-y-6">
        <div className="text-center">
          <p className="text-2xl font-bold">📚 ResearchMind</p>
          <p className="text-sm text-muted-foreground mt-1">{t('authSignInSubtitle')}</p>
        </div>

        <form onSubmit={handleLogin} className="space-y-4">
          <Input type="email" placeholder={t('authEmail')} value={email}
            onChange={e => setEmail(e.target.value)} required />
          <Input type="password" placeholder={t('authPassword')} value={password}
            onChange={e => setPassword(e.target.value)} required />
          {error && <p className="text-sm text-destructive">{error}</p>}
          <Button type="submit" className="w-full" disabled={loading}>
            {loading ? t('authSigningIn') : t('authSignIn')}
          </Button>
        </form>

        <p className="text-center text-sm text-muted-foreground">
          {t('authNoAccount')}{' '}
          <Link href="/auth/signup" className="text-primary hover:underline">
            {t('authSignUp')}
          </Link>
        </p>
      </div>
    </div>
  )
}

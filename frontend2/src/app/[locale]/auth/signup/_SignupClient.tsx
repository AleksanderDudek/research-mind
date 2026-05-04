'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { useTranslations, useLocale } from 'next-intl'
import { supabase } from '@/lib/supabase'
import { Button } from '@/components/ui/button'
import { Input  } from '@/components/ui/input'

export default function SignupPage() {
  const t      = useTranslations()
  const locale = useLocale()
  const router = useRouter()

  const [fullName, setFullName] = useState('')
  const [orgName,  setOrgName]  = useState('')
  const [email,    setEmail]    = useState('')
  const [password, setPassword] = useState('')
  const [error,    setError]    = useState<string | null>(null)
  const [loading,  setLoading]  = useState(false)

  const handleSignup = async (e: React.FormEvent) => {
    e.preventDefault()
    if (password.length < 8) { setError(t('authPasswordMin')); return }
    setError(null)
    setLoading(true)
    const { error: authErr } = await supabase.auth.signUp({
      email,
      password,
      options: {
        data: { full_name: fullName, org_name: orgName || undefined },
      },
    })
    setLoading(false)
    if (authErr) { setError(authErr.message); return }
    // Supabase may send a confirmation email — redirect to login
    router.push(`/${locale}/auth/login`)
  }

  return (
    <div className="min-h-dvh flex items-center justify-center bg-background px-4">
      <div className="w-full max-w-sm space-y-6">
        <div className="text-center">
          <p className="text-2xl font-bold">📚 ResearchMind</p>
          <p className="text-sm text-muted-foreground mt-1">{t('authCreateAccount')}</p>
        </div>

        <form onSubmit={handleSignup} className="space-y-4">
          <Input
            placeholder={t('authFullName')}
            value={fullName}
            onChange={e => setFullName(e.target.value)}
            required
          />
          <Input
            placeholder={t('authOrgName')}
            value={orgName}
            onChange={e => setOrgName(e.target.value)}
          />
          <Input
            type="email"
            placeholder={t('authEmail')}
            value={email}
            onChange={e => setEmail(e.target.value)}
            required
          />
          <Input
            type="password"
            placeholder={t('authPassword')}
            value={password}
            onChange={e => setPassword(e.target.value)}
            required
          />
          {error && <p className="text-sm text-destructive">{error}</p>}
          <Button type="submit" className="w-full" disabled={loading}>
            {loading ? t('authCreatingAccount') : t('authCreateAccount')}
          </Button>
        </form>

        <p className="text-center text-sm text-muted-foreground">
          {t('authHaveAccount')}{' '}
          <a href={`/${locale}/auth/login`} className="text-primary hover:underline">
            {t('authSignIn')}
          </a>
        </p>
      </div>
    </div>
  )
}

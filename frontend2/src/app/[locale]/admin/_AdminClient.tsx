'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useLocale, useTranslations } from 'next-intl'
import { useAppStore } from '@/lib/store'
import { UserList }   from '@/components/admin/UserList'
import { InviteForm } from '@/components/admin/InviteForm'
import Link from 'next/link'

export default function AdminPage() {
  const t      = useTranslations()
  const locale = useLocale()
  const router = useRouter()
  const role   = useAppStore(s => s.role)

  useEffect(() => {
    if (role && role === 'user') router.replace(`/${locale}`)
  }, [role, locale, router])

  return (
    <div className="min-h-dvh bg-background">
      <header className="border-b bg-card px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Link href={`/${locale}`} className="text-sm text-muted-foreground hover:text-primary transition-colors">
            ← {t('back')}
          </Link>
          <span className="text-muted-foreground">/</span>
          <p className="font-semibold">{t('adminPanel')}</p>
        </div>
      </header>

      <main className="max-w-2xl mx-auto px-4 py-8 space-y-8">
        <section>
          <p className="text-xs font-semibold text-muted-foreground uppercase tracking-widest mb-3">
            {t('adminInviteUser')}
          </p>
          <InviteForm />
        </section>

        <section>
          <p className="text-xs font-semibold text-muted-foreground uppercase tracking-widest mb-3">
            {t('adminMembers')}
          </p>
          <UserList />
        </section>
      </main>
    </div>
  )
}

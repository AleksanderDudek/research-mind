'use client'

import { useEffect } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { useTranslations } from 'next-intl'
import { useAppStore } from '@/lib/store'
import { UserList }   from '@/components/admin/UserList'
import { InviteForm } from '@/components/admin/InviteForm'

export default function AdminClient() {
  const t      = useTranslations()
  const router = useRouter()
  const role   = useAppStore(s => s.role)

  useEffect(() => {
    if (role && role === 'user') router.replace('/')
  }, [role, router])

  return (
    <div className="min-h-dvh bg-background">
      <header className="border-b bg-card px-6 py-4 flex items-center gap-3">
        <Link href="/" className="text-sm text-muted-foreground hover:text-primary transition-colors">
          ← {t('back')}
        </Link>
        <span className="text-muted-foreground">/</span>
        <p className="font-semibold">{t('adminPanel')}</p>
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

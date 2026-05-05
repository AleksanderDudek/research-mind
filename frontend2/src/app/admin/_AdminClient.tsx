'use client'

import { useEffect } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { useTranslations } from 'next-intl'
import { Building2, ChevronRight } from 'lucide-react'
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

        {/* Superadmin shortcut — visible only to superadmins */}
        {role === 'superadmin' && (
          <section>
            <p className="text-xs font-semibold text-muted-foreground uppercase tracking-widest mb-3">
              {t('navAllOrgs')}
            </p>
            <Link
              href="/superadmin"
              className="flex items-center gap-3 rounded-xl border bg-card px-4 py-3 hover:border-primary/40 hover:bg-accent/30 transition-all group"
            >
              <div className="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center text-primary shrink-0">
                <Building2 size={15} />
              </div>
              <p className="flex-1 text-sm font-medium">{t('adminAllOrgs')}</p>
              <ChevronRight size={15} className="text-muted-foreground group-hover:text-primary transition-colors" />
            </Link>
          </section>
        )}
      </main>
    </div>
  )
}

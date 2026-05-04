'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { useLocale, useTranslations } from 'next-intl'
import { useQuery } from '@tanstack/react-query'
import { org as orgApi } from '@/lib/api'
import { useAppStore } from '@/lib/store'
import { Badge } from '@/components/ui/badge'

export function generateStaticParams() {
  return [{ locale: 'en' }, { locale: 'pl' }]
}

export default function SuperAdminPage() {
  const t      = useTranslations()
  const locale = useLocale()
  const router = useRouter()
  const role   = useAppStore(s => s.role)

  useEffect(() => {
    if (role && role !== 'superadmin') router.replace(`/${locale}`)
  }, [role, locale, router])

  const { data: orgs = [], isLoading } = useQuery({
    queryKey: ['superadmin', 'orgs'],
    queryFn:  orgApi.allOrgs,
    enabled:  role === 'superadmin',
  })

  return (
    <div className="min-h-dvh bg-background">
      <header className="border-b bg-card px-6 py-4 flex items-center gap-3">
        <a href={`/${locale}`} className="text-sm text-muted-foreground hover:text-primary transition-colors">
          ← {t('back')}
        </a>
        <span className="text-muted-foreground">/</span>
        <p className="font-semibold">{t('superAdminPanel')}</p>
      </header>

      <main className="max-w-3xl mx-auto px-4 py-8">
        <p className="text-xs font-semibold text-muted-foreground uppercase tracking-widest mb-4">
          {t('adminAllOrgs')}
        </p>

        {isLoading && (
          <div className="space-y-2">
            {[1, 2, 3].map(i => <div key={i} className="h-14 rounded-xl bg-muted animate-pulse" />)}
          </div>
        )}

        {!isLoading && (
          <ul className="space-y-2">
            {orgs.map(o => (
              <li key={o.id} className="flex items-center gap-3 rounded-xl border bg-card px-4 py-3">
                <div className="flex-1 min-w-0">
                  <p className="font-medium text-sm truncate">{o.name}</p>
                  <p className="text-xs text-muted-foreground">
                    {new Date(o.created_at).toLocaleDateString()}
                  </p>
                </div>
                <Badge variant="secondary">{o.id.slice(0, 8)}</Badge>
              </li>
            ))}
          </ul>
        )}
      </main>
    </div>
  )
}

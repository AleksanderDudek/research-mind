'use client'

import { BookOpen } from 'lucide-react'
import { useTranslations } from 'next-intl'

export function EmptyState() {
  const t = useTranslations()
  return (
    <div className="flex flex-col items-center justify-center py-20 px-6 text-center gap-4">
      <div className="w-16 h-16 rounded-2xl bg-accent flex items-center justify-center text-primary">
        <BookOpen size={28} />
      </div>
      <div>
        <p className="font-semibold text-foreground mb-1">{t('noContexts')}</p>
        <p className="text-sm text-muted-foreground">{t('emptyContextHint')}</p>
      </div>
    </div>
  )
}

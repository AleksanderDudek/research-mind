'use client'

import { useQuery } from '@tanstack/react-query'
import { useTranslations } from 'next-intl'
import { history as histApi } from '@/lib/api'
import { useAppStore } from '@/lib/store'
import { ScrollArea } from '@/components/ui/scroll-area'

const ACTION_ICON: Record<string, string> = {
  source_added:   '➕',
  source_edited:  '✏️',
  source_deleted: '🗑️',
}

export function HistoryPanel() {
  const t   = useTranslations()
  const ctx = useAppStore(s => s.activeContext)!

  const { data: entries = [], isLoading } = useQuery({
    queryKey: ['history', ctx.context_id],
    queryFn:  () => histApi.list(ctx.context_id),
  })

  return (
    <ScrollArea className="h-full">
      <div className="px-5 py-5">
        <p className="text-xs font-semibold text-muted-foreground uppercase tracking-widest mb-4">
          {t('activityLog')}
        </p>

        {isLoading && (
          <div className="space-y-2">
            {[1,2,3].map(i => <div key={i} className="h-10 rounded-xl bg-muted animate-pulse" />)}
          </div>
        )}

        {!isLoading && entries.length === 0 && (
          <p className="text-sm text-muted-foreground text-center py-10">{t('noHistory')}</p>
        )}

        {!isLoading && entries.length > 0 && (
          <ul className="space-y-1">
            {entries.slice(0, 50).map((e, i) => (
              <li key={`${e.timestamp}-${i}`} className="flex items-start gap-3 py-2.5 border-b last:border-0">
                <span className="text-base shrink-0 mt-0.5">{ACTION_ICON[e.action] ?? '•'}</span>
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-foreground truncate">{e.detail}</p>
                  <p className="text-xs text-muted-foreground mt-0.5">
                    {new Date(e.timestamp).toLocaleString(undefined, {
                      month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit',
                    })}
                  </p>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>
    </ScrollArea>
  )
}

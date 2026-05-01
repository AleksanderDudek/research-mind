'use client'

import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { AnimatePresence, motion } from 'framer-motion'
import { toast } from 'sonner'
import { Plus, Search } from 'lucide-react'
import { useTranslations, useLocale } from 'next-intl'
import { contexts as api } from '@/lib/api'
import type { Context } from '@/lib/types'
import { useAppStore } from '@/lib/store'
import { Button }   from '@/components/ui/button'
import { Input }    from '@/components/ui/input'
import { ContextCard } from './ContextCard'
import { EmptyState  } from './EmptyState'

export function ContextPanel() {
  const t         = useTranslations()
  const locale    = useLocale()
  const setActive = useAppStore(s => s.setActiveContext)
  const qc        = useQueryClient()

  const [name,   setName]   = useState('')
  const [search, setSearch] = useState('')

  const { data: ctxList = [], isLoading } = useQuery({ queryKey: ['contexts'], queryFn: api.list })

  const create = useMutation({
    mutationFn: () => api.create(name.trim() || undefined),
    onSuccess:  (ctx: Context) => {
      qc.invalidateQueries({ queryKey: ['contexts'] })
      setName('')
      toast.success(`"${ctx.name}" created`)
    },
    onError: (e: Error) => toast.error(e.message),
  })

  const sorted   = [...ctxList].sort((a, b) => b.created_at.localeCompare(a.created_at))
  const filtered = search.trim()
    ? sorted.filter(c => c.name.toLowerCase().includes(search.toLowerCase()))
    : sorted

  const targetLocale = locale === 'en' ? 'pl' : 'en'

  return (
    <div className="min-h-dvh flex flex-col">
      {/* Header */}
      <header className="sticky top-0 z-20 border-b bg-background/90 backdrop-blur-sm">
        <div className="max-w-content mx-auto px-4 h-14 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <span className="text-xl">📚</span>
            <span className="font-bold text-foreground tracking-tight">{t('appTitle')}</span>
          </div>
          <a
            href={`/${targetLocale}`}
            className="text-sm text-muted-foreground hover:text-primary transition-colors"
          >
            {t('langToggle')}
          </a>
        </div>
      </header>

      {/* Main */}
      <main className="flex-1 max-w-content mx-auto w-full px-4 py-8 space-y-8">
        {/* Create */}
        <section>
          <p className="text-xs font-semibold text-muted-foreground uppercase tracking-widest mb-3">
            {t('newContextSection')}
          </p>
          <div className="flex gap-2">
            <Input
              value={name}
              onChange={e => setName(e.target.value)}
              placeholder={t('contextName')}
              onKeyDown={e => { if (e.key === 'Enter') create.mutate() }}
              className="flex-1"
            />
            <Button onClick={() => create.mutate()} disabled={create.isPending} className="shrink-0 gap-1.5">
              <Plus size={15} /> {t('createContext')}
            </Button>
          </div>
        </section>

        {/* List */}
        <section>
          <div className="flex items-center justify-between mb-3">
            <p className="text-xs font-semibold text-muted-foreground uppercase tracking-widest">
              {t('recentContexts')}
            </p>
            {sorted.length > 0 && (
              <div className="relative w-44">
                <Search size={13} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-muted-foreground" />
                <input
                  value={search}
                  onChange={e => setSearch(e.target.value)}
                  placeholder={t('filterPlaceholder')}
                  className="w-full rounded-md border bg-muted/40 pl-7 pr-3 py-1.5 text-xs text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring"
                />
              </div>
            )}
          </div>

          {isLoading && (
            <div className="space-y-3">
              {[1, 2, 3].map(i => <div key={i} className="h-[72px] rounded-xl bg-muted animate-pulse" />)}
            </div>
          )}
          {!isLoading && filtered.length === 0 && search && (
            <p className="text-sm text-muted-foreground py-8 text-center">{t('noContextsMatch', { search })}</p>
          )}
          {!isLoading && filtered.length === 0 && !search && <EmptyState />}
          {!isLoading && filtered.length > 0 && (
            <motion.ul className="space-y-2.5" layout>
              <AnimatePresence initial={false}>
                {filtered.map((ctx, i) => (
                  <motion.li
                    key={ctx.context_id}
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0, transition: { delay: i * 0.04 } }}
                    exit={{ opacity: 0, scale: 0.98 }}
                    layout
                  >
                    <ContextCard ctx={ctx} onOpen={setActive} />
                  </motion.li>
                ))}
              </AnimatePresence>
            </motion.ul>
          )}
        </section>
      </main>
    </div>
  )
}

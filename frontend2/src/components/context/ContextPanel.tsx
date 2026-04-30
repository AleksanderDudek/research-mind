'use client'

import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { AnimatePresence, motion } from 'framer-motion'
import { toast } from 'sonner'
import { Plus, Search } from 'lucide-react'
import { contexts as api } from '@/lib/api'
import type { Context } from '@/lib/types'
import { useT, useLang } from '@/i18n/config'
import { useAppStore } from '@/lib/store'
import { Button } from '@/components/ui/Button'
import { Input  } from '@/components/ui/Input'
import { ContextCard } from './ContextCard'
import { EmptyState  } from './EmptyState'

export function ContextPanel() {
  const t         = useT()
  const lang      = useLang()
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
    onError: (e) => toast.error(String(e)),
  })

  const sorted   = [...ctxList].sort((a, b) => b.created_at.localeCompare(a.created_at))
  const filtered = search.trim()
    ? sorted.filter(c => c.name.toLowerCase().includes(search.toLowerCase()))
    : sorted

  return (
    <div className="min-h-dvh flex flex-col">
      {/* Header */}
      <header className="sticky top-0 z-20 border-b border-border bg-surface/90 backdrop-blur-sm">
        <div className="max-w-content mx-auto px-4 h-14 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <span className="text-xl">📚</span>
            <span className="font-bold text-slate-900 tracking-tight">ResearchMind</span>
          </div>
          <a
            href={`?lang=${lang === 'en' ? 'pl' : 'en'}`}
            className="text-sm text-slate-500 hover:text-brand transition-colors"
          >
            {t('langToggle')}
          </a>
        </div>
      </header>

      {/* Main */}
      <main className="flex-1 max-w-content mx-auto w-full px-4 py-8 space-y-8">
        {/* Create context */}
        <section>
          <h2 className="text-xs font-semibold text-slate-400 uppercase tracking-widest mb-3">
            New context
          </h2>
          <div className="flex gap-2">
            <Input
              value={name}
              onChange={e => setName(e.target.value)}
              placeholder={t('contextName')}
              onKeyDown={e => { if (e.key === 'Enter') { create.mutate() } }}
              className="flex-1"
            />
            <Button
              variant="primary"
              onClick={() => create.mutate()}
              loading={create.isPending}
              className="shrink-0 gap-1.5"
            >
              <Plus size={15} /> {t('createContext')}
            </Button>
          </div>
        </section>

        {/* Context list */}
        <section>
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-xs font-semibold text-slate-400 uppercase tracking-widest">
              Recent contexts
            </h2>
            {sorted.length > 4 && (
              <div className="relative w-44">
                <Search size={13} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-400" />
                <input
                  value={search}
                  onChange={e => setSearch(e.target.value)}
                  placeholder="Filter…"
                  className="w-full rounded-lg border border-border bg-surface-2 pl-7 pr-3 py-1.5 text-xs text-slate-700 placeholder:text-slate-400 focus:outline-none focus:ring-1 focus:ring-brand/60"
                />
              </div>
            )}
          </div>

          {isLoading ? (
            <div className="space-y-3">
              {[1, 2, 3].map(i => (
                <div key={i} className="h-[68px] rounded-xl bg-surface-2 animate-pulse" />
              ))}
            </div>
          ) : filtered.length === 0 && search ? (
            <p className="text-sm text-slate-400 py-8 text-center">No contexts match &quot;{search}&quot;</p>
          ) : filtered.length === 0 ? (
            <EmptyState />
          ) : (
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

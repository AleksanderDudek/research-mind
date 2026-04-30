'use client'

import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { contexts as api } from '@/lib/api'
import type { Context } from '@/lib/types'
import { useT, useLang } from '@/i18n/config'
import { useAppStore } from '@/lib/store'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { Spinner } from '@/components/ui/Spinner'
import { ContextCard } from './ContextCard'

export function ContextPanel() {
  const t         = useT()
  const lang      = useLang()
  const setActive = useAppStore(s => s.setActiveContext)
  const qc        = useQueryClient()
  const [name, setName] = useState('')

  const { data: ctxList = [], isLoading } = useQuery({
    queryKey: ['contexts'],
    queryFn:  api.list,
  })

  const create = useMutation({
    mutationFn: () => api.create(name.trim() || undefined),
    onSuccess:  () => { qc.invalidateQueries({ queryKey: ['contexts'] }); setName('') },
  })

  const sorted = [...ctxList].sort((a, b) =>
    b.created_at.localeCompare(a.created_at)
  )

  return (
    <div className="max-w-content mx-auto px-5 pt-6 pb-24">
      {/* Header */}
      <div className="flex items-baseline justify-between mb-1">
        <h1 className="text-2xl font-bold text-slate-900">📚 ResearchMind</h1>
        <a
          href={`?lang=${lang === 'en' ? 'pl' : 'en'}`}
          className="text-sm text-indigo-600 hover:underline"
        >
          {t('langToggle')}
        </a>
      </div>
      <p className="text-sm text-slate-500 mb-6">{t('appCaption')}</p>

      {/* Create */}
      <div className="flex gap-2 mb-8">
        <Input
          value={name}
          onChange={e => setName(e.target.value)}
          placeholder={t('contextName')}
          onKeyDown={e => { if (e.key === 'Enter') create.mutate() }}
        />
        <Button
          variant="primary"
          onClick={() => create.mutate()}
          disabled={create.isPending}
          className="shrink-0"
        >
          {create.isPending ? <Spinner /> : t('createContext')}
        </Button>
      </div>

      {/* List */}
      {isLoading ? (
        <div className="flex justify-center py-10"><Spinner className="w-6 h-6" /></div>
      ) : sorted.length === 0 ? (
        <p className="text-center text-slate-400 py-10 text-sm">{t('noContexts')}</p>
      ) : (
        <div className="space-y-3">
          {sorted.map(ctx => (
            <ContextCard key={ctx.context_id} ctx={ctx} onOpen={setActive} />
          ))}
        </div>
      )}
    </div>
  )
}

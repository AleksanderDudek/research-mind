'use client'

import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { contexts as api } from '@/lib/api'
import type { Context } from '@/lib/types'
import { useT } from '@/i18n/config'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'

interface Props {
  ctx:    Context
  onOpen: (ctx: Context) => void
}

export function ContextCard({ ctx, onOpen }: Props) {
  const t   = useT()
  const qc  = useQueryClient()
  const [confirmDel, setConfirmDel] = useState(false)
  const [renaming,   setRenaming]   = useState(false)
  const [newName,    setNewName]     = useState(ctx.name)

  const del    = useMutation({ mutationFn: () => api.delete(ctx.context_id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['contexts'] }) })
  const rename = useMutation({ mutationFn: (n: string) => api.rename(ctx.context_id, n),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['contexts'] }); setRenaming(false) } })

  if (confirmDel) return (
    <div className="rounded-2xl border border-amber-200 bg-amber-50 p-4 space-y-3">
      <p className="text-sm font-medium text-amber-800">{t('confirmDelete')}: <strong>{ctx.name}</strong></p>
      <div className="flex gap-2">
        <Button variant="danger"     size="sm" onClick={() => del.mutate()}          disabled={del.isPending}>
          {del.isPending ? '…' : t('deleteContext')}
        </Button>
        <Button variant="secondary"  size="sm" onClick={() => setConfirmDel(false)}>{t('cancel')}</Button>
      </div>
    </div>
  )

  if (renaming) return (
    <div className="rounded-2xl border border-slate-200 p-4 space-y-2">
      <Input autoFocus value={newName} onChange={e => setNewName(e.target.value)}
        onKeyDown={e => { if (e.key === 'Enter') rename.mutate(newName) }}
        placeholder={ctx.name} />
      <div className="flex gap-2">
        <Button variant="primary"    size="sm" onClick={() => rename.mutate(newName)} disabled={rename.isPending || !newName.trim()}>
          {rename.isPending ? '…' : t('save')}
        </Button>
        <Button variant="secondary"  size="sm" onClick={() => setRenaming(false)}>{t('cancel')}</Button>
      </div>
    </div>
  )

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-4 hover:border-indigo-200 hover:shadow-sm transition-all">
      <div className="flex items-start justify-between gap-2 mb-3">
        <div>
          <p className="font-semibold text-slate-900 text-sm">{ctx.name}</p>
          <p className="text-xs text-slate-400 mt-0.5">{ctx.created_at.slice(0, 10)}</p>
        </div>
        <div className="flex gap-1 shrink-0">
          <Button variant="ghost" size="sm" onClick={() => setRenaming(true)}  title={t('renameContext')}>✏️</Button>
          <Button variant="ghost" size="sm" onClick={() => setConfirmDel(true)} title={t('deleteContext')}>🗑️</Button>
        </div>
      </div>
      <Button variant="primary" className="w-full" onClick={() => onOpen(ctx)}>
        {t('openContext')}
      </Button>
    </div>
  )
}

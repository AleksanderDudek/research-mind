'use client'

import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { Trash2 } from 'lucide-react'
import { contexts as ctxApi } from '@/lib/api'
import { useAppStore } from '@/lib/store'
import { useT } from '@/i18n/config'
import { Button } from '@/components/ui/Button'
import { Input  } from '@/components/ui/Input'

export function SettingsPanel() {
  const t         = useT()
  const ctx       = useAppStore(s => s.activeContext)!
  const setActive = useAppStore(s => s.setActiveContext)
  const qc        = useQueryClient()

  const [name,    setName]    = useState(ctx.name)
  const [confirm, setConfirm] = useState(false)

  const rename = useMutation({
    mutationFn: () => ctxApi.rename(ctx.context_id, name.trim()),
    onSuccess:  () => { qc.invalidateQueries({ queryKey: ['contexts'] }); toast.success('Renamed') },
    onError:    (e) => toast.error(String(e)),
  })

  const del = useMutation({
    mutationFn: () => ctxApi.delete(ctx.context_id),
    onSuccess:  () => { qc.invalidateQueries({ queryKey: ['contexts'] }); setActive(null); toast.success('Context deleted') },
    onError:    (e) => toast.error(String(e)),
  })

  return (
    <div className="px-5 py-5 space-y-8 max-w-sm">
      {/* Rename */}
      <section>
        <p className="text-xs font-semibold text-slate-400 uppercase tracking-widest mb-3">Context name</p>
        <div className="flex gap-2">
          <Input value={name} onChange={e => setName(e.target.value)}
            onKeyDown={e => { if (e.key === 'Enter') { rename.mutate() } }}
          />
          <Button variant="primary" onClick={() => rename.mutate()}
            disabled={!name.trim() || name === ctx.name} loading={rename.isPending}>
            {t('save')}
          </Button>
        </div>
      </section>

      {/* Danger zone */}
      <section>
        <p className="text-xs font-semibold text-slate-400 uppercase tracking-widest mb-3">Danger zone</p>
        <div className="rounded-xl border border-red-200 bg-red-50 p-4 space-y-3">
          <div>
            <p className="text-sm font-medium text-red-800">Delete this context</p>
            <p className="text-xs text-red-600 mt-0.5">
              Removes all sources, messages, and history. This action cannot be undone.
            </p>
          </div>
          {confirm ? (
            <div className="flex gap-2">
              <Button variant="danger" size="sm" onClick={() => del.mutate()} loading={del.isPending}>
                <Trash2 size={13} /> Yes, delete permanently
              </Button>
              <Button variant="ghost" size="sm" onClick={() => setConfirm(false)}>{t('cancel')}</Button>
            </div>
          ) : (
            <Button variant="danger" size="sm" onClick={() => setConfirm(true)}>
              <Trash2 size={13} /> {t('deleteContext')}
            </Button>
          )}
        </div>
      </section>
    </div>
  )
}

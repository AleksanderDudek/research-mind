'use client'

import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { Trash2, Volume2, VolumeX } from 'lucide-react'
import { useTranslations } from 'next-intl'
import { contexts as ctxApi } from '@/lib/api'
import { useAppStore } from '@/lib/store'
import { Button } from '@/components/ui/button'
import { Input  } from '@/components/ui/input'

export function SettingsPanel() {
  const t             = useTranslations()
  const ctx           = useAppStore(s => s.activeContext)!
  const setActive     = useAppStore(s => s.setActiveContext)
  const ttsEnabled    = useAppStore(s => s.ttsEnabled)
  const setTtsEnabled = useAppStore(s => s.setTtsEnabled)
  const qc            = useQueryClient()

  const [name,    setName]    = useState(ctx.name)
  const [confirm, setConfirm] = useState(false)

  const rename = useMutation({
    mutationFn: () => ctxApi.rename(ctx.context_id, name.trim()),
    onSuccess:  () => { qc.invalidateQueries({ queryKey: ['contexts'] }); toast.success(t('renamedOk')) },
    onError:    (e: Error) => toast.error(e.message),
  })

  const del = useMutation({
    mutationFn: () => ctxApi.delete(ctx.context_id),
    onSuccess:  () => { qc.invalidateQueries({ queryKey: ['contexts'] }); setActive(null); toast.success(t('contextDeleted')) },
    onError:    (e: Error) => toast.error(e.message),
  })

  return (
    <div className="px-5 py-5 space-y-8 max-w-sm">
      {/* Voice */}
      <section>
        <p className="text-xs font-semibold text-muted-foreground uppercase tracking-widest mb-3">{t('voiceSection')}</p>
        <div className="flex items-center justify-between rounded-xl border bg-card p-4">
          <div className="flex items-center gap-3">
            {ttsEnabled
              ? <Volume2 size={18} className="text-primary" />
              : <VolumeX size={18} className="text-muted-foreground" />}
            <div>
              <p className="text-sm font-medium">{t('agentVoiceLabel')}</p>
              <p className="text-xs text-muted-foreground mt-0.5">{t('agentVoiceDesc')}</p>
            </div>
          </div>
          <button
            type="button"
            role="switch"
            aria-checked={ttsEnabled}
            onClick={() => setTtsEnabled(!ttsEnabled)}
            className={`relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring ${ttsEnabled ? 'bg-primary' : 'bg-muted'}`}
          >
            <span className={`pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow-sm transition-transform ${ttsEnabled ? 'translate-x-5' : 'translate-x-0'}`} />
          </button>
        </div>
      </section>

      {/* Rename */}
      <section>
        <p className="text-xs font-semibold text-muted-foreground uppercase tracking-widest mb-3">{t('contextNameSection')}</p>
        <div className="flex gap-2">
          <Input
            value={name}
            onChange={e => setName(e.target.value)}
            onKeyDown={e => { if (e.key === 'Enter') rename.mutate() }}
          />
          <Button onClick={() => rename.mutate()} disabled={!name.trim() || name === ctx.name || rename.isPending}>
            {t('save')}
          </Button>
        </div>
      </section>

      {/* Danger zone */}
      <section>
        <p className="text-xs font-semibold text-muted-foreground uppercase tracking-widest mb-3">{t('dangerZone')}</p>
        <div className="rounded-xl border border-destructive/30 bg-destructive/5 p-4 space-y-3">
          <div>
            <p className="text-sm font-medium text-destructive">{t('deleteContextTitle')}</p>
            <p className="text-xs text-muted-foreground mt-0.5">{t('deleteContextDesc')}</p>
          </div>
          {confirm ? (
            <div className="flex gap-2">
              <Button variant="destructive" size="sm" onClick={() => del.mutate()} disabled={del.isPending}>
                <Trash2 size={13} className="mr-1.5" /> {t('deletePermanently')}
              </Button>
              <Button variant="ghost" size="sm" onClick={() => setConfirm(false)}>{t('cancel')}</Button>
            </div>
          ) : (
            <Button variant="destructive" size="sm" onClick={() => setConfirm(true)}>
              <Trash2 size={13} className="mr-1.5" /> {t('deleteContext')}
            </Button>
          )}
        </div>
      </section>
    </div>
  )
}

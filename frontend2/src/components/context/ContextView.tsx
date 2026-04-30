'use client'

import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { ArrowLeft, Mic, Pencil, Check, X } from 'lucide-react'
import { contexts as ctxApi } from '@/lib/api'
import { useAppStore } from '@/lib/store'
import { useT } from '@/i18n/config'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/Tabs'
import { ChatView }    from '@/components/chat/ChatView'
import { IngestPanel } from '@/components/ingest/IngestPanel'
import { VoiceMode }   from '@/components/voice/VoiceMode'

export function ContextView() {
  const t         = useT()
  const ctx       = useAppStore(s => s.activeContext)!
  const setActive = useAppStore(s => s.setActiveContext)
  const qc        = useQueryClient()

  const [renaming, setRenaming] = useState(false)
  const [newName,  setNewName]  = useState(ctx.name)
  const [voiceOn,  setVoiceOn]  = useState(false)

  const rename = useMutation({
    mutationFn: () => ctxApi.rename(ctx.context_id, newName.trim()),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['contexts'] })
      setRenaming(false)
      toast.success('Context renamed')
    },
    onError: (e) => toast.error(String(e)),
  })

  if (voiceOn) return <VoiceMode onExit={() => setVoiceOn(false)} />

  return (
    <div className="flex flex-col h-dvh bg-white">
      {/* Sticky header */}
      <header className="flex items-center gap-2 px-4 py-3 border-b border-slate-100 sticky top-0 z-10 bg-white/95 backdrop-blur-sm">
        <Button variant="ghost" size="sm" onClick={() => setActive(null)}>
          <ArrowLeft size={15} /> {t('back')}
        </Button>

        {renaming ? (
          <>
            <Input
              autoFocus
              value={newName}
              onChange={e => setNewName(e.target.value)}
              onKeyDown={e => { if (e.key === 'Enter') rename.mutate() }}
              className="flex-1 py-1.5 text-sm h-8"
            />
            <Button variant="primary" size="sm" onClick={() => rename.mutate()}
              disabled={rename.isPending || !newName.trim()}>
              <Check size={14} />
            </Button>
            <Button variant="ghost"   size="sm" onClick={() => setRenaming(false)}>
              <X size={14} />
            </Button>
          </>
        ) : (
          <>
            <span className="flex-1 font-semibold text-slate-800 text-sm truncate">{ctx.name}</span>
            <Button variant="ghost" size="sm" onClick={() => setRenaming(true)} title={t('renameContext')}>
              <Pencil size={14} />
            </Button>
          </>
        )}

        <Button
          variant={voiceOn ? 'primary' : 'secondary'}
          size="sm"
          onClick={() => setVoiceOn(v => !v)}
          title={t('voiceMode')}
        >
          <Mic size={14} /> 🗣️
        </Button>
      </header>

      {/* Radix-based tab navigation */}
      <Tabs defaultValue="chat" className="flex flex-col flex-1 overflow-hidden">
        <TabsList>
          <TabsTrigger value="chat">💬 {t('chat')}</TabsTrigger>
          <TabsTrigger value="sources">📥 {t('addSource')}</TabsTrigger>
        </TabsList>

        <TabsContent value="chat"    className="flex flex-col flex-1 overflow-hidden">
          <ChatView />
        </TabsContent>
        <TabsContent value="sources" className="flex-1 overflow-y-auto">
          <IngestPanel />
        </TabsContent>
      </Tabs>
    </div>
  )
}

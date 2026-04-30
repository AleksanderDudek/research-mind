'use client'

import { useEffect, useRef } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { X, Volume2, VolumeX, StopCircle } from 'lucide-react'
import { messages as msgsApi } from '@/lib/api'
import { useAppStore } from '@/lib/store'
import { useT, useLang } from '@/i18n/config'
import { useVoiceLoop } from '@/hooks/useVoiceLoop'
import { Button }         from '@/components/ui/Button'
import { ScrollArea }     from '@/components/ui/ScrollArea'
import { ChatMessage }    from '@/components/chat/ChatMessage'
import { TypingIndicator } from '@/components/chat/TypingIndicator'
import { VoiceCircle }    from './VoiceCircle'
import type { Message }   from '@/lib/types'

interface Props { readonly onClose: () => void }

const STATUS_LABEL: Record<string, string> = {
  idle:         'Ready',
  recording:    'Listening…',
  transcribing: 'Transcribing…',
  thinking:     'Thinking…',
  speaking:     'Speaking…',
}

export function VoiceMode({ onClose }: Props) {
  const t           = useT()
  const lang        = useLang()
  const ctx         = useAppStore(s => s.activeContext)!
  const msgs        = useAppStore(s => s.messages)
  const appendMsg   = useAppStore(s => s.appendMessage)
  const ttsEnabled  = useAppStore(s => s.ttsEnabled)
  const setTtsEnabled = useAppStore(s => s.setTtsEnabled)
  const qc          = useQueryClient()
  const bottomRef   = useRef<HTMLDivElement>(null)

  const persist = useMutation({
    mutationFn: (msg: Omit<Message, 'timestamp'>) => msgsApi.save(ctx.context_id, msg),
    onSuccess:  () => qc.invalidateQueries({ queryKey: ['messages', ctx.context_id] }),
  })

  const { state, rms, start, stop, interrupt } = useVoiceLoop({
    contextId:  ctx.context_id,
    ttsEnabled,
    lang,
    onMessage:  appendMsg,
    onPersist:  async msg => { await persist.mutateAsync(msg) },
  })

  // Auto-start on mount, stop on unmount
  useEffect(() => {
    start()
    return () => stop()
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // Scroll to latest message
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [msgs.length, state])

  const handleClose = () => { stop(); onClose() }

  const handleTtsToggle = () => {
    const next = !ttsEnabled
    setTtsEnabled(next)
    if (!next) globalThis.speechSynthesis?.cancel()
  }

  return (
    <motion.div
      key="voice-overlay"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 z-50 bg-surface flex flex-col"
    >
      {/* Header */}
      <div className="flex items-center justify-between px-5 pt-5 pb-3 border-b border-border shrink-0">
        <p className="font-semibold text-slate-800 text-sm">🗣️ {t('voiceMode')}</p>
        <div className="flex items-center gap-1">
          <Button size="icon" variant="ghost" onClick={handleTtsToggle}
            title={ttsEnabled ? 'Mute responses' : 'Unmute responses'}>
            {ttsEnabled ? <Volume2 size={16} /> : <VolumeX size={16} className="text-slate-400" />}
          </Button>
          <Button size="icon" variant="ghost" onClick={handleClose} title="Close voice mode">
            <X size={18} />
          </Button>
        </div>
      </div>

      {/* Conversation transcript — shared with ChatView */}
      <ScrollArea className="flex-1">
        <div className="px-4 py-4 space-y-3">
          {msgs.length === 0 ? (
            <p className="text-center text-sm text-slate-400 py-8">
              Voice mode is active — start speaking.
            </p>
          ) : (
            msgs.map(m => <ChatMessage key={`${m.role}-${m.timestamp}`} msg={m} />)
          )}
          {(state === 'transcribing' || state === 'thinking') && <TypingIndicator />}
          <div ref={bottomRef} />
        </div>
      </ScrollArea>

      {/* Voice controls — pinned at bottom */}
      <div className="shrink-0 border-t border-border px-5 py-5 flex flex-col items-center gap-3 bg-surface/95">
        <VoiceCircle state={state} rms={rms} />

        <p className="text-sm font-medium text-slate-600">
          {STATUS_LABEL[state] ?? 'Ready'}
        </p>

        {/* Volume bar — visible while recording */}
        {state === 'recording' && (
          <div className="w-40 h-1 bg-slate-100 rounded-full overflow-hidden">
            <motion.div
              className="h-full bg-red-400 rounded-full"
              animate={{ width: `${rms * 100}%` }}
              transition={{ duration: 0.05 }}
            />
          </div>
        )}

        {/* Interrupt — only while agent is thinking */}
        <AnimatePresence>
          {state === 'thinking' && (
            <motion.div initial={{ opacity: 0, y: 4 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}>
              <Button variant="danger" onClick={interrupt} className="gap-2">
                <StopCircle size={15} /> Interrupt
              </Button>
            </motion.div>
          )}
        </AnimatePresence>

        {/* TTS toggle — labeled */}
        <button
          type="button"
          onClick={handleTtsToggle}
          className="flex items-center gap-2 rounded-full border border-border bg-surface px-4 py-1.5 text-sm font-medium text-slate-600 hover:border-brand hover:text-brand transition-colors"
        >
          {ttsEnabled ? <Volume2 size={15} /> : <VolumeX size={15} className="text-slate-400" />}
          {ttsEnabled ? 'Voice ON' : 'Voice OFF'}
        </button>

        <Button variant="ghost" size="sm" onClick={handleClose}>
          {t('typeInstead')}
        </Button>
      </div>
    </motion.div>
  )
}

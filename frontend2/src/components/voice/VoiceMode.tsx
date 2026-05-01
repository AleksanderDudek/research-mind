'use client'

import { useEffect, useRef } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { X, Volume2, VolumeX, StopCircle } from 'lucide-react'
import { useTranslations, useLocale } from 'next-intl'
import { messages as msgsApi } from '@/lib/api'
import { useAppStore } from '@/lib/store'
import { useVoiceLoop } from '@/hooks/useVoiceLoop'
import { Button }         from '@/components/ui/button'
import { ScrollArea }     from '@/components/ui/scroll-area'
import { ChatMessage }    from '@/components/chat/ChatMessage'
import { TypingIndicator } from '@/components/chat/TypingIndicator'
import { VoiceCircle }    from './VoiceCircle'
import type { Message }   from '@/lib/types'
import type { LoopState } from '@/hooks/useVoiceLoop'

interface Props { readonly onClose: () => void }

export function VoiceMode({ onClose }: Props) {
  const t             = useTranslations()
  const locale        = useLocale()
  const ctx           = useAppStore(s => s.activeContext)!
  const msgs          = useAppStore(s => s.messages)
  const appendMsg     = useAppStore(s => s.appendMessage)
  const ttsEnabled    = useAppStore(s => s.ttsEnabled)
  const setTtsEnabled = useAppStore(s => s.setTtsEnabled)
  const qc            = useQueryClient()
  const bottomRef     = useRef<HTMLDivElement>(null)

  const persist = useMutation({
    mutationFn: (msg: Omit<Message, 'timestamp'>) => msgsApi.save(ctx.context_id, msg),
    onSuccess:  () => qc.invalidateQueries({ queryKey: ['messages', ctx.context_id] }),
  })

  const { state, rms, start, stop, interrupt } = useVoiceLoop({
    contextId:  ctx.context_id,
    ttsEnabled,
    lang:       locale,
    onMessage:  appendMsg,
    onPersist:  async msg => { await persist.mutateAsync(msg) },
  })

  useEffect(() => { start(); return () => stop() }, []) // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [msgs.length, state])

  const handleClose = () => { stop(); onClose() }
  const handleTtsToggle = () => {
    const next = !ttsEnabled
    setTtsEnabled(next)
    if (!next) globalThis.speechSynthesis?.cancel()
  }

  const STATUS_LABEL: Record<LoopState, string> = {
    idle:         t('statusReady'),
    recording:    t('statusListening'),
    transcribing: t('statusTranscribing'),
    thinking:     t('statusThinking'),
    speaking:     t('statusSpeaking'),
  }

  return (
    <motion.div
      key="voice-overlay"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 z-50 bg-background flex flex-col"
    >
      <div className="flex items-center justify-between px-5 pt-5 pb-3 border-b shrink-0">
        <p className="font-semibold text-sm">🗣️ {t('voiceMode')}</p>
        <div className="flex items-center gap-1">
          <Button size="icon" variant="ghost" onClick={handleTtsToggle}
            title={ttsEnabled ? t('muteResponses') : t('unmuteResponses')}>
            {ttsEnabled ? <Volume2 size={16} /> : <VolumeX size={16} className="text-muted-foreground" />}
          </Button>
          <Button size="icon" variant="ghost" onClick={handleClose} title={t('closeVoiceMode')}>
            <X size={18} />
          </Button>
        </div>
      </div>

      <ScrollArea className="flex-1">
        <div className="px-4 py-4 space-y-3">
          {msgs.length === 0
            ? <p className="text-center text-sm text-muted-foreground py-8">{t('voiceActiveHint')}</p>
            : msgs.map(m => <ChatMessage key={`${m.role}-${m.timestamp}`} msg={m} />)}
          {(state === 'transcribing' || state === 'thinking') && <TypingIndicator />}
          <div ref={bottomRef} />
        </div>
      </ScrollArea>

      <div className="shrink-0 border-t px-5 py-5 flex flex-col items-center gap-3 bg-background/95">
        <VoiceCircle state={state} rms={rms} />

        <p className="text-sm font-medium text-muted-foreground">{STATUS_LABEL[state]}</p>

        {state === 'recording' && (
          <div className="w-40 h-1 bg-muted rounded-full overflow-hidden">
            <motion.div
              className="h-full bg-destructive rounded-full"
              animate={{ width: `${rms * 100}%` }}
              transition={{ duration: 0.05 }}
            />
          </div>
        )}

        <AnimatePresence>
          {state === 'thinking' && (
            <motion.div initial={{ opacity: 0, y: 4 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}>
              <Button variant="destructive" onClick={interrupt} className="gap-2">
                <StopCircle size={15} /> {t('interrupt')}
              </Button>
            </motion.div>
          )}
        </AnimatePresence>

        <button
          type="button"
          onClick={handleTtsToggle}
          className="flex items-center gap-2 rounded-full border bg-background px-4 py-1.5 text-sm font-medium text-muted-foreground hover:border-primary hover:text-primary transition-colors"
        >
          {ttsEnabled ? <Volume2 size={15} /> : <VolumeX size={15} className="text-muted-foreground" />}
          {ttsEnabled ? t('voiceOnLabel') : t('voiceOffLabel')}
        </button>

        <Button variant="ghost" size="sm" onClick={handleClose}>{t('typeInstead')}</Button>
      </div>
    </motion.div>
  )
}

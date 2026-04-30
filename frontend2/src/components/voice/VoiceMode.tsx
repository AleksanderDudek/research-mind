'use client'

import { useRef, useEffect, useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { X, Check, Volume2, VolumeX } from 'lucide-react'
import { messages as msgsApi, query as queryApi } from '@/lib/api'
import { useAppStore } from '@/lib/store'
import { useT, useLang } from '@/i18n/config'
import { useVoice, browserTts } from '@/hooks/useVoice'
import { Button } from '@/components/ui/Button'
import { ScrollArea } from '@/components/ui/ScrollArea'
import { ChatMessage } from '@/components/chat/ChatMessage'
import { TypingIndicator } from '@/components/chat/TypingIndicator'
import { VoiceCircle } from './VoiceCircle'
import type { Message } from '@/lib/types'

interface Props { readonly onClose: () => void }

export function VoiceMode({ onClose }: Props) {
  const t          = useT()
  const lang       = useLang()
  const ctx        = useAppStore(s => s.activeContext)!
  const msgs       = useAppStore(s => s.messages)
  const appendMsg  = useAppStore(s => s.appendMessage)
  const qc         = useQueryClient()

  const [agentLoading, setAgentLoading] = useState(false)
  const [confirmation, setConfirmation] = useState<string | null>(null)
  const [ttsEnabled,   setTtsEnabled]   = useState(true)
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [msgs.length, agentLoading])

  const persist = useMutation({
    mutationFn: (msg: Omit<Message, 'timestamp'>) => msgsApi.save(ctx.context_id, msg),
  })

  const sendToAgent = async (text: string) => {
    const userMsg: Message = { role: 'user', content: `🎤 ${text}`, timestamp: new Date().toISOString() }
    appendMsg(userMsg)
    setAgentLoading(true)
    try {
      // Persist user message first (await so the backend has it before we fetch the answer)
      await persist.mutateAsync({ role: 'user', content: text })

      const res  = await queryApi.ask(text, ctx.context_id)
      const asst: Message = {
        role: 'assistant', content: res.answer, timestamp: new Date().toISOString(),
        sources: res.sources, action_taken: res.action_taken, iterations: res.iterations,
      }
      appendMsg(asst)

      // Persist assistant message, then force ChatView to sync from the backend
      await persist.mutateAsync({ role: 'assistant', content: res.answer, sources: res.sources })
      qc.invalidateQueries({ queryKey: ['messages', ctx.context_id] })

      if (ttsEnabled) { browserTts(res.answer, lang) }
    } catch (err) {
      toast.error('Voice response failed — please try again.')
      console.error('[VoiceMode] sendToAgent error:', err)
    } finally {
      setAgentLoading(false)
    }
  }

  const { status, rms, startListening, stopListening } = useVoice({
    onTranscribed:   (text) => { if (!agentLoading) { sendToAgent(text) } },
    onLowConfidence: ({ text }) => setConfirmation(text),
    onError:         () => {},
  })

  const statusText: Record<typeof status, string> = {
    idle:       t('tapToSpeak'),
    recording:  'Listening…',
    processing: t('processing'),
    confirming: t('processing'),
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
          {/* TTS toggle */}
          <Button
            size="icon"
            variant="ghost"
            onClick={() => { setTtsEnabled(v => !v); window.speechSynthesis?.cancel() }}
            title={ttsEnabled ? 'Mute voice responses' : 'Unmute voice responses'}
          >
            {ttsEnabled ? <Volume2 size={16} /> : <VolumeX size={16} className="text-slate-400" />}
          </Button>
          <Button size="icon" variant="ghost" onClick={() => { stopListening(); window.speechSynthesis?.cancel(); onClose() }}>
            <X size={18} />
          </Button>
        </div>
      </div>

      {/* Shared message history — same store as ChatView */}
      <ScrollArea className="flex-1">
        <div className="px-4 py-4 space-y-3">
          {msgs.length === 0 ? (
            <p className="text-center text-sm text-slate-400 py-8">
              Start speaking — your conversation will appear here.
            </p>
          ) : (
            msgs.map(m => <ChatMessage key={`${m.role}-${m.timestamp}`} msg={m} />)
          )}
          {agentLoading && <TypingIndicator />}
          <div ref={bottomRef} />
        </div>
      </ScrollArea>

      {/* Low-confidence confirmation card */}
      <AnimatePresence>
        {confirmation && (
          <motion.div
            initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: 8 }}
            className="mx-4 mb-2 rounded-xl border border-amber-200 bg-amber-50 p-4 space-y-3 shrink-0"
          >
            <p className="text-sm font-medium text-amber-800">
              🤔 {t('didYouSay', { text: confirmation })}
            </p>
            <div className="flex gap-2">
              <Button variant="primary" size="sm" className="flex-1"
                onClick={() => { sendToAgent(confirmation); setConfirmation(null) }}>
                <Check size={14} /> {t('yesCorrect')}
              </Button>
              <Button variant="secondary" size="sm" onClick={() => setConfirmation(null)}>
                {t('discard')}
              </Button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Voice controls (pinned bottom) */}
      <div className="shrink-0 border-t border-border px-5 py-4 flex flex-col items-center gap-3 bg-surface/95">
        <VoiceCircle status={agentLoading ? 'processing' : status} rms={rms} />

        <p className="text-sm font-medium text-slate-600">
          {agentLoading ? t('thinking') : statusText[status]}
        </p>

        {status === 'recording' && (
          <div className="w-40 h-1 bg-slate-100 rounded-full overflow-hidden">
            <motion.div className="h-full bg-red-400 rounded-full"
              animate={{ width: `${rms * 100}%` }} transition={{ duration: 0.05 }} />
          </div>
        )}

        <div className="flex gap-2">
          {status === 'idle' && !agentLoading && (
            <Button variant="primary" onClick={startListening} className="px-8">
              🎤 {t('tapToSpeak')}
            </Button>
          )}
          {status === 'recording' && (
            <Button variant="danger" onClick={stopListening} className="px-8">⏹ Stop</Button>
          )}
          <Button variant="ghost" onClick={() => { stopListening(); window.speechSynthesis?.cancel(); onClose() }}>
            {t('typeInstead')}
          </Button>
        </div>
      </div>
    </motion.div>
  )
}

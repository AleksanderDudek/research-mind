'use client'

import { useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { useMutation } from '@tanstack/react-query'
import { X, Check } from 'lucide-react'
import { messages as msgsApi, query as queryApi } from '@/lib/api'
import { useAppStore } from '@/lib/store'
import { useT, useLang } from '@/i18n/config'
import { useVoice, browserTts } from '@/hooks/useVoice'
import { Button } from '@/components/ui/Button'
import { VoiceCircle } from './VoiceCircle'
import type { Message } from '@/lib/types'

interface Props { readonly onClose: () => void }

export function VoiceMode({ onClose }: Props) {
  const t          = useT()
  const lang       = useLang()
  const ctx        = useAppStore(s => s.activeContext)!
  const appendMsg  = useAppStore(s => s.appendMessage)

  const [agentLoading,  setAgentLoading]  = useState(false)
  const [confirmation,  setConfirmation]  = useState<string | null>(null)

  const persist = useMutation({
    mutationFn: (msg: Omit<Message, 'timestamp'>) => msgsApi.save(ctx.context_id, msg),
  })

  const sendToAgent = async (text: string) => {
    const userMsg: Message = { role: 'user', content: `🎤 ${text}`, timestamp: new Date().toISOString() }
    appendMsg(userMsg)
    persist.mutate({ role: 'user', content: text })
    setAgentLoading(true)
    try {
      const res  = await queryApi.ask(text, ctx.context_id)
      const asst: Message = {
        role: 'assistant', content: res.answer, timestamp: new Date().toISOString(),
        sources: res.sources, action_taken: res.action_taken, iterations: res.iterations,
      }
      appendMsg(asst)
      persist.mutate({ role: 'assistant', content: res.answer, sources: res.sources })
      browserTts(res.answer, lang)
    } catch { /* ignore */ }
    finally { setAgentLoading(false) }
  }

  const { status, rms, startListening, stopListening } = useVoice({
    onTranscribed:    (text) => { if (!agentLoading) { sendToAgent(text) } },
    onLowConfidence:  ({ text }) => setConfirmation(text),
    onError:          () => { /* toast handled by caller */ },
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
      <div className="flex items-center justify-between px-6 pt-safe-top pt-5 pb-4 border-b border-border">
        <p className="font-semibold text-slate-800">🗣️ {t('voiceMode')}</p>
        <Button size="icon" variant="ghost" onClick={() => { stopListening(); onClose() }} title="Close">
          <X size={18} />
        </Button>
      </div>

      {/* Main */}
      <div className="flex-1 flex flex-col items-center justify-center gap-8 px-8">
        {/* Animated circle */}
        <VoiceCircle status={agentLoading ? 'processing' : status} rms={rms} />

        {/* Status text */}
        <p className="text-base font-medium text-slate-600">
          {agentLoading ? t('thinking') : statusText[status]}
        </p>

        {/* Volume bar */}
        {status === 'recording' && (
          <div className="w-48 h-1 bg-slate-100 rounded-full overflow-hidden">
            <motion.div
              className="h-full bg-red-400 rounded-full"
              animate={{ width: `${rms * 100}%` }}
              transition={{ duration: 0.05 }}
            />
          </div>
        )}

        {/* Confirmation card */}
        <AnimatePresence>
          {confirmation && (
            <motion.div
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: 8 }}
              className="w-full max-w-sm rounded-xl border border-amber-200 bg-amber-50 p-4 space-y-3"
            >
              <p className="text-sm font-medium text-amber-800">
                🤔 {t('didYouSay', { text: confirmation })}
              </p>
              <div className="flex gap-2">
                <Button
                  variant="primary" size="sm" className="flex-1"
                  onClick={() => { sendToAgent(confirmation); setConfirmation(null) }}
                >
                  <Check size={14} /> {t('yesCorrect')}
                </Button>
                <Button
                  variant="secondary" size="sm"
                  onClick={() => setConfirmation(null)}
                >
                  {t('discard')}
                </Button>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Controls */}
      <div className="px-8 pb-safe-bottom pb-8 flex justify-center gap-4">
        {status === 'idle' && !agentLoading && (
          <Button variant="primary" size="lg" onClick={startListening} className="px-10">
            🎤 {t('tapToSpeak')}
          </Button>
        )}
        {status === 'recording' && (
          <Button variant="danger" size="lg" onClick={stopListening} className="px-10">
            ⏹ Stop
          </Button>
        )}
        <Button variant="ghost" size="lg" onClick={() => { stopListening(); onClose() }}>
          {t('typeInstead')}
        </Button>
      </div>
    </motion.div>
  )
}

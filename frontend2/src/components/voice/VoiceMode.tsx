'use client'

import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { messages as msgsApi, query as queryApi } from '@/lib/api'
import { useAppStore } from '@/lib/store'
import { useT, useLang } from '@/i18n/config'
import { useVoice, browserTts } from '@/hooks/useVoice'
import { Button } from '@/components/ui/Button'
import { ChatMessage } from '@/components/chat/ChatMessage'
import type { Message } from '@/lib/types'
import { clsx } from 'clsx'

interface Props { onExit: () => void }

export function VoiceMode({ onExit }: Props) {
  const t      = useT()
  const lang   = useLang()
  const ctx    = useAppStore(s => s.activeContext)!
  const msgs   = useAppStore(s => s.messages)
  const appendMsg = useAppStore(s => s.appendMessage)

  const [agentLoading, setAgentLoading] = useState(false)
  const [confirmation, setConfirmation]  = useState<{ text: string } | null>(null)

  const persist = useMutation({
    mutationFn: (msg: Omit<Message, 'timestamp'>) => msgsApi.save(ctx.context_id, msg),
  })

  const sendToAgent = async (text: string) => {
    if (!text.trim()) return
    const userMsg: Message = { role: 'user', content: `🎤 ${text}`, timestamp: new Date().toISOString() }
    appendMsg(userMsg)
    persist.mutate({ role: 'user', content: text })
    setAgentLoading(true)
    try {
      const res  = await queryApi.ask(text, ctx.context_id)
      const asst: Message = {
        role: 'assistant', content: res.answer,
        timestamp: new Date().toISOString(),
        sources: res.sources, action_taken: res.action_taken,
        iterations: res.iterations, critique: res.critique,
      }
      appendMsg(asst)
      persist.mutate({ role: 'assistant', content: res.answer, sources: res.sources })
      browserTts(res.answer, lang)
    } catch { /* ignore */ }
    finally { setAgentLoading(false) }
  }

  const { status, rms, startListening, stopListening } = useVoice({
    onTranscribed:   (text) => { if (!agentLoading) sendToAgent(text) },
    onLowConfidence: ({ text }) => setConfirmation({ text }),
    onError:         (msg) => { /* could show toast */ console.warn(msg) },
  })

  const circleClass = clsx(
    'w-24 h-24 rounded-full mx-auto transition-all duration-300',
    status === 'idle'       && 'bg-slate-200 animate-pulse-slow opacity-70',
    status === 'recording'  && 'bg-red-500 animate-ping-sm shadow-lg shadow-red-200',
    status === 'processing' && 'bg-amber-400 animate-spin-slow',
  )

  return (
    <div className="flex flex-col h-full">
      {/* Exit */}
      <div className="px-4 pt-3 pb-1">
        <Button variant="ghost" size="sm" onClick={() => { stopListening(); onExit() }}>
          {t('typeInstead')}
        </Button>
      </div>

      {/* History */}
      <div className="flex-1 overflow-y-auto px-4 py-2 space-y-3">
        {msgs.map((m, i) => <ChatMessage key={i} msg={m} />)}
      </div>

      {/* Confirmation card */}
      {confirmation && (
        <div className="mx-4 mb-3 p-4 rounded-2xl border border-amber-200 bg-amber-50">
          <p className="text-sm font-medium text-amber-800 mb-2">
            🤔 {t('didYouSay', { text: confirmation.text })}
          </p>
          <div className="flex gap-2">
            <Button variant="primary" size="sm" onClick={() => { sendToAgent(confirmation.text); setConfirmation(null) }}>
              {t('yesCorrect')}
            </Button>
            <Button variant="secondary" size="sm" onClick={() => setConfirmation(null)}>
              {t('discard')}
            </Button>
          </div>
        </div>
      )}

      {/* Circle + volume + controls */}
      <div className="px-4 pb-8 pt-2 flex flex-col items-center gap-4">
        {/* Animated circle */}
        <div className={circleClass} />

        {/* Volume bar */}
        <div className="w-40 h-1.5 bg-slate-100 rounded-full overflow-hidden">
          <div
            className="h-full bg-red-400 rounded-full transition-all duration-75"
            style={{ width: `${rms * 100}%` }}
          />
        </div>

        <p className="text-sm text-slate-500">
          {agentLoading ? t('thinking') :
           status === 'recording' ? '🔴 Listening…' :
           status === 'processing' ? t('processing') :
           t('tapToSpeak')}
        </p>

        {/* Toggle button */}
        {status === 'idle' && !agentLoading ? (
          <Button variant="primary" onClick={startListening} className="px-8">
            🎤 {t('tapToSpeak')}
          </Button>
        ) : status === 'recording' ? (
          <Button variant="danger" onClick={stopListening} className="px-8">
            ⏹ Stop
          </Button>
        ) : null}
      </div>
    </div>
  )
}

'use client'

import { useRef, useEffect, useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { X, Check, Volume2, VolumeX, StopCircle } from 'lucide-react'
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
  const t         = useT()
  const lang      = useLang()
  const ctx          = useAppStore(s => s.activeContext)!
  const msgs         = useAppStore(s => s.messages)
  const appendMsg    = useAppStore(s => s.appendMessage)
  const ttsEnabled   = useAppStore(s => s.ttsEnabled)
  const setTtsEnabled = useAppStore(s => s.setTtsEnabled)
  const qc           = useQueryClient()

  const [agentLoading, setAgentLoading] = useState(false)
  const [ttsSpeaking,  setTtsSpeaking]  = useState(false)
  const [confirmation, setConfirmation] = useState<string | null>(null)
  const bottomRef     = useRef<HTMLDivElement>(null)
  const abortRef      = useRef<AbortController | null>(null)
  // Ref to startListening so onError callback can call it without being
  // listed as a dependency (avoids circular closure issues).
  const startRef      = useRef<() => Promise<void>>(() => Promise.resolve())

  // Auto-scroll
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [msgs.length, agentLoading])

  const persist = useMutation({
    mutationFn: (msg: Omit<Message, 'timestamp'>) => msgsApi.save(ctx.context_id, msg),
  })

  // ── Core send logic ───────────────────────────────────────────────────────
  const sendToAgent = async (text: string) => {
    if (agentLoading) { return }

    const userMsg: Message = {
      role: 'user', content: `🎤 ${text}`, timestamp: new Date().toISOString(),
    }
    appendMsg(userMsg)
    setAgentLoading(true)

    const ctrl = new AbortController()
    abortRef.current = ctrl

    try {
      await persist.mutateAsync({ role: 'user', content: text })

      const res = await queryApi.ask(text, ctx.context_id, ctrl.signal)
      if (ctrl.signal.aborted) { return }

      const asst: Message = {
        role: 'assistant', content: res.answer, timestamp: new Date().toISOString(),
        sources: res.sources, action_taken: res.action_taken, iterations: res.iterations,
      }
      appendMsg(asst)

      await persist.mutateAsync({ role: 'assistant', content: res.answer, sources: res.sources })
      qc.invalidateQueries({ queryKey: ['messages', ctx.context_id] })

      if (ttsEnabled) {
        // Wait for the utterance to finish before opening the mic.
        // synth.cancel() (e.g. TTS toggled off) fires onerror → resolves.
        setTtsSpeaking(true)
        await browserTts(res.answer, lang)
        setTtsSpeaking(false)
      }

      // Mic opens only after TTS is done (or immediately when TTS is off)
      startRef.current()
    } catch (err) {
      if ((err as Error).name === 'AbortError') {
        // User interrupted — silently restart listening
        startRef.current()
        return
      }
      toast.error('Voice response failed — please try again.')
      console.error('[VoiceMode]', err)
      startRef.current() // restart even after errors
    } finally {
      setAgentLoading(false)
      abortRef.current = null
    }
  }

  // ── Interrupt in-flight query ─────────────────────────────────────────────
  const handleInterrupt = () => {
    abortRef.current?.abort()
    globalThis.speechSynthesis?.cancel()
    // sendToAgent's finally will set agentLoading=false and its catch will restart listening
  }

  // ── useVoice hook ─────────────────────────────────────────────────────────
  const { status, rms, startListening, stopListening } = useVoice({
    onTranscribed:   (text) => { sendToAgent(text) },
    onLowConfidence: ({ text }) => setConfirmation(text),
    onError:         () => {
      // LIKELY_NOISE / EMPTY — auto-restart after a short pause
      setTimeout(() => { startRef.current() }, 400)
    },
  })

  // Keep ref in sync with latest startListening (updated every render)
  useEffect(() => { startRef.current = startListening })

  // Auto-start on mount; clean up everything on unmount
  useEffect(() => {
    startListening()
    return () => {
      stopListening()
      abortRef.current?.abort()
      globalThis.speechSynthesis?.cancel()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // ── Status copy ───────────────────────────────────────────────────────────
  let statusLabel: string
  if (agentLoading)                  { statusLabel = t('thinking')   }
  else if (ttsSpeaking)              { statusLabel = 'Speaking…'     }
  else if (status === 'recording')   { statusLabel = 'Listening…'    }
  else if (status === 'processing')  { statusLabel = t('processing') }
  else                               { statusLabel = 'Ready'         }

  type CircleStatus = 'idle' | 'recording' | 'processing' | 'confirming' | 'speaking'
  let circleStatus: CircleStatus
  if (agentLoading)    { circleStatus = 'processing' }
  else if (ttsSpeaking){ circleStatus = 'speaking'   }
  else                 { circleStatus = status        }

  // ── Close ─────────────────────────────────────────────────────────────────
  const handleClose = () => {
    stopListening()
    abortRef.current?.abort()
    globalThis.speechSynthesis?.cancel()
    onClose()
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
          <Button
            size="icon" variant="ghost"
            onClick={() => { setTtsEnabled(!ttsEnabled); globalThis.speechSynthesis?.cancel() }}
            title={ttsEnabled ? 'Mute responses' : 'Unmute responses'}
          >
            {ttsEnabled ? <Volume2 size={16} /> : <VolumeX size={16} className="text-slate-400" />}
          </Button>
          <Button size="icon" variant="ghost" onClick={handleClose} title="Close voice mode">
            <X size={18} />
          </Button>
        </div>
      </div>

      {/* Shared conversation history */}
      <ScrollArea className="flex-1">
        <div className="px-4 py-4 space-y-3">
          {msgs.length === 0 ? (
            <p className="text-center text-sm text-slate-400 py-8">
              Voice mode is active — start speaking.
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
                onClick={() => { setConfirmation(null); sendToAgent(confirmation) }}>
                <Check size={14} /> {t('yesCorrect')}
              </Button>
              <Button variant="secondary" size="sm"
                onClick={() => { setConfirmation(null); startRef.current() }}>
                {t('discard')}
              </Button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Voice controls — always visible at bottom */}
      <div className="shrink-0 border-t border-border px-5 py-4 flex flex-col items-center gap-3 bg-surface/95">
        <VoiceCircle status={circleStatus} rms={rms} />

        <p className="text-sm font-medium text-slate-600">{statusLabel}</p>

        {/* Volume bar — visible while recording */}
        {status === 'recording' && (
          <div className="w-40 h-1 bg-slate-100 rounded-full overflow-hidden">
            <motion.div className="h-full bg-red-400 rounded-full"
              animate={{ width: `${rms * 100}%` }} transition={{ duration: 0.05 }} />
          </div>
        )}

        {/* Interrupt button — only while agent is processing */}
        {agentLoading && (
          <Button variant="danger" onClick={handleInterrupt} className="gap-2">
            <StopCircle size={15} /> Interrupt query
          </Button>
        )}

        {/* TTS toggle — labeled so it's unmissable */}
        <button
          type="button"
          onClick={() => { setTtsEnabled(!ttsEnabled); globalThis.speechSynthesis?.cancel() }}
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

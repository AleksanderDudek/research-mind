'use client'

import { useEffect, useRef, useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { AnimatePresence } from 'framer-motion'
import { messages as msgsApi, query as queryApi } from '@/lib/api'
import { useAppStore } from '@/lib/store'
import { useT } from '@/i18n/config'
import type { Message } from '@/lib/types'
import { ScrollArea }      from '@/components/ui/ScrollArea'
import { ChatMessage }     from './ChatMessage'
import { ChatInput }       from './ChatInput'
import { TypingIndicator } from './TypingIndicator'

interface Props {
  readonly onVoiceOpen: () => void
}

export function ChatView({ onVoiceOpen }: Props) {
  const t            = useT()
  const ctx          = useAppStore(s => s.activeContext)!
  const msgs         = useAppStore(s => s.messages)
  const setMsgs      = useAppStore(s => s.setMessages)
  const appendMsg    = useAppStore(s => s.appendMessage)
  const updateMsg    = useAppStore(s => s.updateMessage)
  const removeMsg    = useAppStore(s => s.removeMessage)
  const bottomRef    = useRef<HTMLDivElement>(null)
  const abortRef     = useRef<AbortController | null>(null)

  const [loading,  setLoading]  = useState(false)
  const [thinking, setThinking] = useState(false)

  const { data: histMsgs = [], isLoading: histLoading } = useQuery({
    queryKey: ['messages', ctx.context_id],
    queryFn:  () => msgsApi.list(ctx.context_id),
    staleTime: Infinity,
  })

  // Sync fetched history to the store once per data change.
  // Must NOT be inside `select` — a new arrow function on every render causes
  // TanStack Query to call setMsgs on every re-render, wiping appendMsg additions.
  useEffect(() => {
    setMsgs(histMsgs)
  }, [histMsgs, setMsgs])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [msgs.length, loading])

  const persist = useMutation({
    mutationFn: (msg: Omit<Message, 'timestamp'>) => msgsApi.save(ctx.context_id, msg),
  })

  // Returns true = placeholder has content (keep it), false = empty (caller removes it).
  // Tries streaming first; falls back to the non-streaming endpoint on any non-abort error.
  const _ask = async (text: string, ts: string, signal: AbortSignal): Promise<boolean> => {
    let hasContent = false
    try {
      for await (const ev of queryApi.streamAsk(text, ctx.context_id, signal)) {
        if (ev.type === 'chunk') {
          if (!hasContent) { hasContent = true; setThinking(false) }
          updateMsg(ts, m => ({ ...m, content: m.content + ev.text }))
        } else if (ev.type === 'done') {
          updateMsg(ts, m => ({ ...m, sources: ev.sources, action_taken: ev.action_taken }))
          persist.mutate({ role: 'assistant', content: ev.answer,
            sources: ev.sources, action_taken: ev.action_taken })
        }
      }
      return true
    } catch (e) {
      if ((e as Error).name === 'AbortError') return hasContent
      // Streaming endpoint not available — fall back to blocking ask
      setThinking(true)
      const res = await queryApi.ask(text, ctx.context_id, signal)
      updateMsg(ts, m => ({ ...m, content: res.answer, sources: res.sources, action_taken: res.action_taken }))
      persist.mutate({ role: 'assistant', content: res.answer,
        sources: res.sources, action_taken: res.action_taken })
      return true
    }
  }

  const handleSubmit = async (text: string) => {
    if (loading) return

    appendMsg({ role: 'user', content: text, timestamp: new Date().toISOString() })
    persist.mutate({ role: 'user', content: text })
    setLoading(true)
    setThinking(true)

    const ctrl = new AbortController()
    abortRef.current = ctrl
    const ts = new Date().toISOString()
    appendMsg({ role: 'assistant', content: '', timestamp: ts })

    let keepPlaceholder = false
    try {
      keepPlaceholder = await _ask(text, ts, ctrl.signal)
    } catch (e) {
      if ((e as Error).name !== 'AbortError') {
        updateMsg(ts, m => ({ ...m, content: `⚠️ ${String(e)}` }))
        keepPlaceholder = true
      }
    } finally {
      if (!keepPlaceholder) removeMsg(ts)
      setLoading(false)
      setThinking(false)
      abortRef.current = null
    }
  }

  const handleStop = () => { abortRef.current?.abort() }

  return (
    <div className="flex flex-col h-full">
      <ScrollArea className="flex-1">
        <div className="px-4 py-6 space-y-4 pb-safe-bottom">
          {histLoading && (
            <div className="space-y-4 animate-pulse">
              {[
                { id: 'sk-a', align: 'ml-auto', width: '70%' },
                { id: 'sk-b', align: '',         width: '50%' },
                { id: 'sk-c', align: 'ml-auto',  width: '80%' },
              ].map(({ id, align, width }) => (
                <div
                  key={id}
                  className={`h-10 rounded-2xl bg-surface-2 ${align}`}
                  style={{ width }}
                />
              ))}
            </div>
          )}

          {!histLoading && msgs.length === 0 && (
            <div className="flex flex-col items-center justify-center h-full py-20 gap-3 text-center">
              <div className="text-4xl">💬</div>
              <p className="text-sm text-slate-400 max-w-xs">{t('chatEmptyHint')}</p>
            </div>
          )}

          {!histLoading && msgs.length > 0 && (
            <AnimatePresence initial={false}>
              {msgs.map(m => <ChatMessage key={`${m.role}-${m.timestamp}`} msg={m} />)}
            </AnimatePresence>
          )}

          {thinking && <TypingIndicator />}
          <div ref={bottomRef} />
        </div>
      </ScrollArea>

      <ChatInput
        onSubmit={handleSubmit}
        loading={loading}
        onStop={handleStop}
        onVoiceOpen={onVoiceOpen}
      />
    </div>
  )
}

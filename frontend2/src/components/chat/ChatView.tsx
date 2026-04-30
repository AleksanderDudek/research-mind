'use client'

import { useEffect, useRef, useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { messages as msgsApi, query as queryApi } from '@/lib/api'
import { useAppStore } from '@/lib/store'
import { useT } from '@/i18n/config'
import type { Message } from '@/lib/types'
import { ChatMessage } from './ChatMessage'
import { ChatInput } from './ChatInput'
import { Spinner } from '@/components/ui/Spinner'

export function ChatView() {
  const t          = useT()
  const ctx        = useAppStore(s => s.activeContext)!
  const msgs       = useAppStore(s => s.messages)
  const setMsgs    = useAppStore(s => s.setMessages)
  const appendMsg  = useAppStore(s => s.appendMessage)
  const bottomRef  = useRef<HTMLDivElement>(null)
  const abortRef   = useRef<AbortController | null>(null)
  const [loading, setLoading] = useState(false)
  const [pendingQ, setPendingQ] = useState<string | null>(null)

  // Load history once per context
  const { isLoading: histLoading } = useQuery({
    queryKey: ['messages', ctx.context_id],
    queryFn:  () => msgsApi.list(ctx.context_id),
    staleTime: Infinity,
    select:    data => { setMsgs(data); return data },
  })

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [msgs.length, loading])

  const persistMutation = useMutation({
    mutationFn: (msg: Omit<Message, 'timestamp'>) =>
      msgsApi.save(ctx.context_id, msg),
  })

  const handleSubmit = async (text: string) => {
    if (loading) return
    const userMsg: Message = { role: 'user', content: text, timestamp: new Date().toISOString() }
    appendMsg(userMsg)
    setPendingQ(text)
    setLoading(true)

    const ctrl = new AbortController()
    abortRef.current = ctrl

    try {
      const res = await queryApi.ask(text, ctx.context_id, ctrl.signal)
      const asst: Message = {
        role:         'assistant',
        content:      res.answer,
        timestamp:    new Date().toISOString(),
        sources:      res.sources,
        action_taken: res.action_taken,
        iterations:   res.iterations,
        critique:     res.critique,
      }
      appendMsg(asst)
      persistMutation.mutate({ role: 'user',      content: text })
      persistMutation.mutate({ role: 'assistant', content: res.answer, sources: res.sources,
        action_taken: res.action_taken, iterations: res.iterations, critique: res.critique })
    } catch (e) {
      if ((e as Error).name !== 'AbortError') {
        appendMsg({ role: 'assistant', content: `⚠️ ${t('errorPrefix', { msg: String(e) })}`, timestamp: new Date().toISOString() })
      }
    } finally {
      setLoading(false)
      setPendingQ(null)
      abortRef.current = null
    }
  }

  const handleStop = () => {
    abortRef.current?.abort()
    setLoading(false)
    setPendingQ(null)
    // Remove the dangling user message if agent never responded
    const last = msgs[msgs.length - 1]
    if (last?.role === 'user') setMsgs(msgs.slice(0, -1))
  }

  return (
    <div className="flex flex-col h-full">
      {/* History */}
      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-3">
        {histLoading ? (
          <div className="flex justify-center py-10"><Spinner className="w-6 h-6" /></div>
        ) : msgs.length === 0 ? (
          <p className="text-center text-slate-400 text-sm py-10">{t('chatPlaceholder')}</p>
        ) : (
          msgs.map((m, i) => <ChatMessage key={i} msg={m} />)
        )}

        {/* Skeleton while loading */}
        {loading && (
          <div className="flex justify-start">
            <div className="max-w-[85%] rounded-2xl px-4 py-3 bg-white border border-slate-200 space-y-2">
              {[80, 65, 75].map((w, i) => (
                <div key={i} className="h-3 bg-slate-100 rounded animate-pulse"
                  style={{ width: `${w}%` }} />
              ))}
              <p className="text-xs text-slate-400 mt-1">{t('thinking')}</p>
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <ChatInput onSubmit={handleSubmit} loading={loading} onStop={handleStop} />
    </div>
  )
}

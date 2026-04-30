'use client'

import { useEffect, useRef, useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { AnimatePresence } from 'framer-motion'
import { messages as msgsApi, query as queryApi } from '@/lib/api'
import { useAppStore } from '@/lib/store'
import type { Message } from '@/lib/types'
import { ScrollArea }      from '@/components/ui/ScrollArea'
import { ChatMessage }     from './ChatMessage'
import { ChatInput }       from './ChatInput'
import { TypingIndicator } from './TypingIndicator'

interface Props {
  readonly onVoiceOpen: () => void
}

export function ChatView({ onVoiceOpen }: Props) {
  const ctx       = useAppStore(s => s.activeContext)!
  const msgs      = useAppStore(s => s.messages)
  const setMsgs   = useAppStore(s => s.setMessages)
  const appendMsg = useAppStore(s => s.appendMessage)
  const bottomRef = useRef<HTMLDivElement>(null)
  const abortRef  = useRef<AbortController | null>(null)
  const [loading, setLoading] = useState(false)

  const { isLoading: histLoading } = useQuery({
    queryKey: ['messages', ctx.context_id],
    queryFn:  () => msgsApi.list(ctx.context_id),
    staleTime: Infinity,
    select:    data => { setMsgs(data); return data },
  })

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [msgs.length, loading])

  const persist = useMutation({
    mutationFn: (msg: Omit<Message, 'timestamp'>) => msgsApi.save(ctx.context_id, msg),
  })

  const handleSubmit = async (text: string) => {
    if (loading) { return }
    const userMsg: Message = { role: 'user', content: text, timestamp: new Date().toISOString() }
    appendMsg(userMsg)
    setLoading(true)
    const ctrl = new AbortController()
    abortRef.current = ctrl

    try {
      const res  = await queryApi.ask(text, ctx.context_id, ctrl.signal)
      const asst: Message = {
        role: 'assistant', content: res.answer, timestamp: new Date().toISOString(),
        sources: res.sources, action_taken: res.action_taken,
        iterations: res.iterations, critique: res.critique,
      }
      appendMsg(asst)
      persist.mutate({ role: 'user',      content: text })
      persist.mutate({ role: 'assistant', content: res.answer, sources: res.sources,
        action_taken: res.action_taken, iterations: res.iterations, critique: res.critique })
    } catch (e) {
      if ((e as Error).name !== 'AbortError') {
        appendMsg({ role: 'assistant', content: `⚠️ ${String(e)}`, timestamp: new Date().toISOString() })
      }
    } finally {
      setLoading(false)
      abortRef.current = null
    }
  }

  const handleStop = () => {
    abortRef.current?.abort()
    setLoading(false)
    const last = msgs[msgs.length - 1]
    if (last?.role === 'user') { setMsgs(msgs.slice(0, -1)) }
  }

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
              <p className="text-sm text-slate-400 max-w-xs">
                Ask anything about the sources in this context — research papers, documents, or notes.
              </p>
            </div>
          )}

          {!histLoading && msgs.length > 0 && (
            <AnimatePresence initial={false}>
              {msgs.map(m => <ChatMessage key={`${m.role}-${m.timestamp}`} msg={m} />)}
            </AnimatePresence>
          )}

          {loading && <TypingIndicator />}
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

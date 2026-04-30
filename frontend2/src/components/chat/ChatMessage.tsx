'use client'

import { useState } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { ChevronDown, ChevronUp, BookOpen } from 'lucide-react'
import type { Message } from '@/lib/types'
import { cn } from '@/lib/utils'

interface Props { readonly msg: Message }

export function ChatMessage({ msg }: Props) {
  const [open, setOpen] = useState(false)
  const isUser = msg.role === 'user'

  return (
    <div className={cn('flex', isUser ? 'justify-end' : 'justify-start')}>
      <div className={cn(
        'max-w-[85%] rounded-2xl px-4 py-3 text-sm leading-relaxed',
        isUser
          ? 'bg-indigo-600 text-white'
          : 'bg-white border border-slate-200 text-slate-800',
      )}>
        {isUser ? (
          <p className="whitespace-pre-wrap">{msg.content}</p>
        ) : (
          <>
            <div className="prose prose-sm max-w-none prose-p:leading-relaxed prose-pre:bg-slate-100 prose-pre:rounded-lg prose-code:text-indigo-700 prose-code:bg-indigo-50 prose-code:rounded prose-code:px-1">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {msg.content}
              </ReactMarkdown>
            </div>

            {msg.sources && msg.sources.length > 0 && (
              <div className="mt-2 pt-2 border-t border-slate-100">
                <button
                  className="flex items-center gap-1 text-xs text-slate-400 hover:text-slate-600 transition-colors"
                  onClick={() => setOpen(v => !v)}
                >
                  <BookOpen size={12} />
                  {msg.sources.length} source{msg.sources.length !== 1 && 's'}
                  {open ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
                </button>
                {open && (
                  <ul className="mt-2 space-y-1.5">
                    {msg.sources.map((hit, i) => (
                      <li key={`${hit.source}-${i}`} className="text-xs text-slate-500">
                        <span className="font-medium">[{i + 1}]</span>{' '}
                        <code className="bg-slate-100 px-1 rounded">{hit.source}</code>
                        {' '}(score: {hit.score?.toFixed(3)})
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            )}

            {(msg.action_taken || msg.iterations) && (
              <details className="mt-2">
                <summary className="text-xs text-slate-400 cursor-pointer">Details</summary>
                <p className="text-xs text-slate-400 mt-1">
                  Action: {msg.action_taken} · Iterations: {msg.iterations}
                  {msg.critique && ` · Critic: ${msg.critique.score}/5`}
                </p>
              </details>
            )}
          </>
        )}
      </div>
    </div>
  )
}

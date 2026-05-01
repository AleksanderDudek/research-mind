'use client'

import { useState } from 'react'
import { motion } from 'framer-motion'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { ChevronDown, ChevronUp, BookOpen, Bot } from 'lucide-react'
import type { Message } from '@/lib/types'
import { cn } from '@/lib/utils'
import { useT } from '@/i18n/config'

interface Props { readonly msg: Message }

export function ChatMessage({ msg }: Props) {
  const t = useT()
  const [showSrc, setShowSrc] = useState(false)
  const isUser = msg.role === 'user'

  return (
    <motion.div
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.2 }}
      className={cn('flex gap-2.5', isUser ? 'justify-end' : 'justify-start')}
    >
      {/* Avatar (assistant only) */}
      {!isUser && (
        <div className="w-7 h-7 rounded-full bg-brand-light flex items-center justify-center text-brand shrink-0 mt-0.5">
          <Bot size={14} />
        </div>
      )}

      <div className={cn(
        'max-w-[82%] rounded-2xl px-4 py-3 text-sm leading-relaxed shadow-sm',
        isUser
          ? 'bg-brand text-white rounded-tr-sm'
          : 'bg-surface border border-border text-slate-800 rounded-tl-sm',
      )}>
        {isUser ? (
          <p className="whitespace-pre-wrap">{msg.content}</p>
        ) : (
          <>
            <div className="rm-prose">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>{msg.content}</ReactMarkdown>
            </div>

            {/* Sources toggle */}
            {msg.sources && msg.sources.length > 0 && (
              <div className="mt-3 pt-3 border-t border-slate-100">
                <button
                  type="button"
                  className="flex items-center gap-1.5 text-xs text-slate-400 hover:text-slate-600 transition-colors"
                  onClick={() => setShowSrc(v => !v)}
                >
                  <BookOpen size={12} />
                  {t('sourcesCount', { n: msg.sources.length })}
                  {showSrc ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
                </button>
                {showSrc && (
                  <ul className="mt-2 space-y-1.5 animate-slide-up">
                    {msg.sources.map((hit, i) => (
                      <li key={`${hit.source}-${i}`} className="text-xs text-slate-500 flex items-start gap-1.5">
                        <span className="font-semibold text-slate-400 shrink-0">[{i + 1}]</span>
                        <code className="bg-slate-100 px-1.5 py-0.5 rounded text-[10px]">{hit.source}</code>
                        <span className="text-slate-400">·</span>
                        <span className="text-slate-400">{hit.score?.toFixed(2)}</span>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            )}

            {/* Agent metadata (collapsed) */}
            {(msg.action_taken || msg.iterations) && (
              <details className="mt-2">
                <summary className="text-[11px] text-slate-400 cursor-pointer select-none hover:text-slate-500">
                  {t('messageDetails')}
                </summary>
                <p className="text-[11px] text-slate-400 mt-1">
                  {msg.action_taken && <>Action: {msg.action_taken}</>}
                  {msg.iterations   && <> · Iterations: {msg.iterations}</>}
                  {msg.critique     && <> · Critic: {msg.critique.score}/5</>}
                </p>
              </details>
            )}
          </>
        )}
      </div>
    </motion.div>
  )
}

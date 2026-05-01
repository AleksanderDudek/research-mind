'use client'

import { useState } from 'react'
import { motion } from 'framer-motion'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { ChevronDown, ChevronUp, BookOpen, Bot } from 'lucide-react'
import { useTranslations } from 'next-intl'
import type { Message } from '@/lib/types'
import { cn } from '@/lib/utils'
import { Badge } from '@/components/ui/badge'

interface Props { readonly msg: Message }

export function ChatMessage({ msg }: Props) {
  const t = useTranslations()
  const [showSrc, setShowSrc] = useState(false)
  const isUser = msg.role === 'user'

  return (
    <motion.div
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.2 }}
      className={cn('flex gap-2.5', isUser ? 'justify-end' : 'justify-start')}
    >
      {!isUser && (
        <div className="w-7 h-7 rounded-full bg-accent flex items-center justify-center text-primary shrink-0 mt-0.5">
          <Bot size={14} />
        </div>
      )}

      <div className={cn(
        'max-w-[82%] rounded-2xl px-4 py-3 text-sm leading-relaxed shadow-sm',
        isUser
          ? 'bg-primary text-primary-foreground rounded-tr-sm'
          : 'bg-card border rounded-tl-sm',
      )}>
        {isUser ? (
          <p className="whitespace-pre-wrap">{msg.content}</p>
        ) : (
          <>
            <div className="rm-prose">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>{msg.content}</ReactMarkdown>
            </div>

            {msg.sources && msg.sources.length > 0 && (
              <div className="mt-3 pt-3 border-t border-border/50">
                <button
                  type="button"
                  className="flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors"
                  onClick={() => setShowSrc(v => !v)}
                >
                  <BookOpen size={12} />
                  {t('sourcesCount', { count: msg.sources.length })}
                  {showSrc ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
                </button>
                {showSrc && (
                  <ul className="mt-2 space-y-1.5 animate-slide-up">
                    {msg.sources.map((hit, i) => (
                      <li key={`${hit.source}-${i}`} className="text-xs text-muted-foreground flex items-start gap-1.5">
                        <span className="font-semibold shrink-0">[{i + 1}]</span>
                        <Badge variant="secondary" className="text-[10px] h-4 px-1">{hit.source}</Badge>
                        <span>· {hit.score?.toFixed(2)}</span>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            )}

            {(msg.action_taken || msg.iterations) && (
              <details className="mt-2">
                <summary className="text-[11px] text-muted-foreground cursor-pointer select-none hover:text-foreground">
                  {t('messageDetails')}
                </summary>
                <p className="text-[11px] text-muted-foreground mt-1">
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

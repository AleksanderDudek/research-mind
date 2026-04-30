'use client'

import { useRef, useState, KeyboardEvent } from 'react'
import { useT } from '@/i18n/config'
import { Button } from '@/components/ui/Button'
import { useRecorder } from '@/hooks/useRecorder'
import { query as queryApi } from '@/lib/api'
import { clsx } from 'clsx'

interface Props {
  onSubmit:  (text: string) => void
  loading:   boolean
  onStop:    () => void
  disabled?: boolean
}

export function ChatInput({ onSubmit, loading, onStop, disabled }: Props) {
  const t    = useT()
  const [text, setText] = useState('')
  const textareaRef     = useRef<HTMLTextAreaElement>(null)
  const rec             = useRecorder()
  const [transcribing, setTranscribing] = useState(false)

  const submit = () => {
    const v = text.trim()
    if (!v || loading) return
    onSubmit(v)
    setText('')
    if (textareaRef.current) textareaRef.current.style.height = 'auto'
  }

  const handleKey = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); submit() }
  }

  const handleResize = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setText(e.target.value)
    const el = e.target
    el.style.height = 'auto'
    el.style.height = `${Math.min(el.scrollHeight, 180)}px`
  }

  const toggleMic = async () => {
    if (rec.recording) {
      setTranscribing(true)
      try {
        const blob = await rec.stop()
        const res  = await queryApi.transcribe(blob)
        if (res.text) setText(prev => prev + (prev ? ' ' : '') + res.text)
      } catch { /* ignore */ }
      finally { setTranscribing(false) }
    } else {
      await rec.start()
    }
  }

  return (
    <div className="border-t border-slate-100 bg-white p-3">
      {/* Volume bar */}
      {rec.recording && (
        <div className="mb-2 h-1 bg-slate-100 rounded-full overflow-hidden">
          <div
            className="h-full bg-red-400 rounded-full transition-all"
            style={{ width: `${rec.rms * 100}%` }}
          />
        </div>
      )}

      <div className="flex items-end gap-2">
        {/* Textarea */}
        <textarea
          ref={textareaRef}
          value={text}
          onChange={handleResize}
          onKeyDown={handleKey}
          placeholder={t('chatPlaceholder')}
          rows={1}
          disabled={disabled || loading}
          className={clsx(
            'flex-1 resize-none rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm',
            'placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500',
            'transition-colors leading-relaxed max-h-44 overflow-auto',
            (disabled || loading) && 'opacity-50 cursor-not-allowed',
          )}
        />

        {/* Mic button */}
        <button
          onClick={toggleMic}
          disabled={loading || transcribing || disabled}
          title={t('voiceInput')}
          className={clsx(
            'w-11 h-11 rounded-full border flex items-center justify-center text-lg shrink-0 transition-all',
            rec.recording
              ? 'bg-red-50 border-red-300 text-red-500 animate-pulse'
              : 'bg-white border-slate-200 text-slate-500 hover:border-indigo-300',
            (loading || transcribing || disabled) && 'opacity-40 cursor-not-allowed',
          )}
        >
          {transcribing ? '⏳' : rec.recording ? '⏹' : '🎙️'}
        </button>

        {/* Send / Stop */}
        {loading ? (
          <Button variant="secondary" size="md" onClick={onStop} className="shrink-0 h-11">
            ⏹ {t('stop')}
          </Button>
        ) : (
          <Button
            variant="primary"
            size="md"
            onClick={submit}
            disabled={!text.trim() || disabled}
            className="shrink-0 h-11 px-5"
          >
            →
          </Button>
        )}
      </div>
    </div>
  )
}

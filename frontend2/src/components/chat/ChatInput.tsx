'use client'

import { useRef, useState, KeyboardEvent } from 'react'
import { SendHorizonal, Square, Mic, MicOff } from 'lucide-react'
import { useT } from '@/i18n/config'
import { useRecorder } from '@/hooks/useRecorder'
import { query as queryApi } from '@/lib/api'
import { cn } from '@/lib/utils'

interface Props {
  readonly onSubmit:      (text: string) => void
  readonly loading:       boolean
  readonly onStop:        () => void
  readonly onVoiceOpen:   () => void
  readonly disabled?:     boolean
}

export function ChatInput({ onSubmit, loading, onStop, onVoiceOpen, disabled }: Props) {
  const t           = useT()
  const [text, setText] = useState('')
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const rec         = useRecorder()
  const [transcribing, setTranscribing] = useState(false)

  const submit = () => {
    const v = text.trim()
    if (!v || loading) { return }
    onSubmit(v)
    setText('')
    if (textareaRef.current) { textareaRef.current.style.height = 'auto' }
  }

  const handleKey = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); submit() }
  }

  const handleResize = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setText(e.target.value)
    const el = e.target
    el.style.height = 'auto'
    el.style.height = `${Math.min(el.scrollHeight, 160)}px`
  }

  const toggleMic = async () => {
    if (rec.recording) {
      setTranscribing(true)
      try {
        const blob = await rec.stop()
        const res  = await queryApi.transcribe(blob)
        if (res.text) { setText(prev => prev + (prev ? ' ' : '') + res.text) }
      } catch { /* ignore */ }
      finally { setTranscribing(false) }
    } else {
      await rec.start()
    }
  }

  const isDisabled = disabled || loading

  return (
    <div className="border-t border-border bg-surface px-3 py-3">
      {/* Volume bar */}
      {rec.recording && (
        <div className="mb-2 h-0.5 bg-slate-100 rounded-full overflow-hidden">
          <div
            className="h-full bg-red-400 rounded-full transition-all duration-75"
            style={{ width: `${rec.rms * 100}%` }}
          />
        </div>
      )}

      <div className="flex items-end gap-2">
        {/* Quick-transcribe mic */}
        <button
          type="button"
          onClick={toggleMic}
          disabled={isDisabled || transcribing}
          title={rec.recording ? 'Stop recording' : 'Transcribe (click to record)'}
          className={cn(
            'h-9 w-9 rounded-full border flex items-center justify-center text-base shrink-0 transition-all',
            rec.recording
              ? 'bg-red-50 border-red-300 text-red-500 animate-pulse'
              : 'bg-surface border-border text-slate-400 hover:border-brand hover:text-brand',
            (isDisabled || transcribing) && 'opacity-40 pointer-events-none',
          )}
        >
          {transcribing && '⌛'}
          {!transcribing && rec.recording && <MicOff size={15} />}
          {!transcribing && !rec.recording && <Mic size={15} />}
        </button>

        {/* Textarea */}
        <textarea
          ref={textareaRef}
          value={text}
          onChange={handleResize}
          onKeyDown={handleKey}
          placeholder={t('chatPlaceholder')}
          rows={1}
          disabled={isDisabled}
          className={cn(
            'flex-1 resize-none rounded-xl border border-border bg-surface-2 px-3.5 py-2.5 text-sm',
            'placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-brand/40 focus:bg-surface',
            'transition-colors max-h-40 overflow-auto leading-relaxed',
            isDisabled && 'opacity-50 cursor-not-allowed',
          )}
        />

        {/* Voice mode FAB */}
        <button
          type="button"
          onClick={onVoiceOpen}
          disabled={isDisabled}
          title="Voice mode"
          className={cn(
            'h-9 w-9 rounded-full border border-border bg-surface text-slate-400',
            'hover:border-brand hover:text-brand flex items-center justify-center transition-all text-base',
            isDisabled && 'opacity-40 pointer-events-none',
          )}
        >
          🗣️
        </button>

        {/* Send / Stop */}
        {loading ? (
          <button
            type="button"
            onClick={onStop}
            className="h-9 w-9 rounded-full bg-red-500 text-white flex items-center justify-center hover:bg-red-600 transition-colors shrink-0"
            title={t('stop')}
          >
            <Square size={14} fill="currentColor" />
          </button>
        ) : (
          <button
            type="button"
            onClick={submit}
            disabled={!text.trim() || isDisabled}
            className={cn(
              'h-9 w-9 rounded-full flex items-center justify-center transition-all shrink-0',
              text.trim() && !isDisabled
                ? 'bg-brand text-white hover:bg-brand-hover shadow-sm'
                : 'bg-surface-2 text-slate-300 cursor-not-allowed',
            )}
            title="Send"
          >
            <SendHorizonal size={15} />
          </button>
        )}
      </div>
    </div>
  )
}

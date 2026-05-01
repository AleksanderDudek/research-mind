'use client'

import { useRef, useState } from 'react'
import type { KeyboardEvent } from 'react'
import { SendHorizonal, Square, Mic, MicOff } from 'lucide-react'
import { useTranslations } from 'next-intl'
import { useRecorder } from '@/hooks/useRecorder'
import { query as queryApi } from '@/lib/api'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'

interface Props {
  readonly onSubmit:    (text: string) => void
  readonly loading:     boolean
  readonly onStop:      () => void
  readonly onVoiceOpen: () => void
  readonly disabled?:   boolean
}

export function ChatInput({ onSubmit, loading, onStop, onVoiceOpen, disabled }: Props) {
  const t           = useTranslations()
  const [text, setText] = useState('')
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const rec         = useRecorder()
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
    el.style.height = `${Math.min(el.scrollHeight, 160)}px`
  }

  const toggleMic = async () => {
    if (rec.recording) {
      setTranscribing(true)
      try {
        const blob = await rec.stop()
        const res  = await queryApi.transcribe(blob)
        if (res.text) setText(prev => prev + (prev ? ' ' : '') + res.text)
      } catch { /* ignore */ } finally {
        setTranscribing(false)
      }
    } else {
      await rec.start()
    }
  }

  const isDisabled = disabled || loading

  return (
    <div className="border-t bg-card px-3 py-3">
      {rec.recording && (
        <div className="mb-2 h-0.5 bg-muted rounded-full overflow-hidden">
          <div className="h-full bg-destructive rounded-full transition-all duration-75" style={{ width: `${rec.rms * 100}%` }} />
        </div>
      )}

      <div className="flex items-end gap-2">
        <Button
          type="button"
          size="icon"
          variant="outline"
          onClick={toggleMic}
          disabled={isDisabled || transcribing}
          title={rec.recording ? 'Stop recording' : 'Transcribe (click to record)'}
          className={cn(
            'h-9 w-9 shrink-0 rounded-full transition-all',
            rec.recording && 'border-destructive text-destructive bg-destructive/10 animate-pulse',
          )}
        >
          {transcribing ? '⌛' : rec.recording ? <MicOff size={15} /> : <Mic size={15} />}
        </Button>

        <Textarea
          ref={textareaRef}
          value={text}
          onChange={handleResize}
          onKeyDown={handleKey}
          placeholder={t('chatPlaceholder')}
          rows={1}
          disabled={isDisabled}
          className="flex-1 resize-none max-h-40 overflow-auto leading-relaxed rounded-xl"
        />

        <Button
          type="button"
          size="icon"
          variant="outline"
          onClick={onVoiceOpen}
          disabled={isDisabled}
          title="Voice mode"
          className="h-9 w-9 shrink-0 rounded-full"
        >
          🗣️
        </Button>

        {loading ? (
          <Button
            type="button"
            size="icon"
            onClick={onStop}
            className="h-9 w-9 shrink-0 rounded-full bg-destructive text-destructive-foreground hover:bg-destructive/90"
            title={t('stop')}
          >
            <Square size={14} fill="currentColor" />
          </Button>
        ) : (
          <Button
            type="button"
            size="icon"
            onClick={submit}
            disabled={!text.trim() || isDisabled}
            className="h-9 w-9 shrink-0 rounded-full"
            title="Send"
          >
            <SendHorizonal size={15} />
          </Button>
        )}
      </div>
    </div>
  )
}

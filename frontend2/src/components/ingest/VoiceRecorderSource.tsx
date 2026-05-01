'use client'

import { useCallback, useEffect, useRef, useState } from 'react'
import { useDropzone } from 'react-dropzone'
import { Mic, MicOff, Play, Trash2, Upload, CheckCircle2 } from 'lucide-react'
import { useTranslations } from 'next-intl'
import { cn } from '@/lib/utils'
import { useRecorder } from '@/hooks/useRecorder'
import { Button } from '@/components/ui/button'

const MAX_RECORD_S = 5 * 60
const MAX_UPLOAD_S = 30 * 60
const WARN_AT_S    = MAX_RECORD_S - 30

type Mode = 'record' | 'upload'

interface Props { readonly onConfirm: (blob: Blob, filename: string) => void }

function formatTime(s: number) {
  return `${Math.floor(s / 60).toString().padStart(2, '0')}:${(s % 60).toString().padStart(2, '0')}`
}

export function VoiceRecorderSource({ onConfirm }: Props) {
  const t = useTranslations()
  const [mode,     setMode]     = useState<Mode>('record')
  const [blob,     setBlob]     = useState<Blob | null>(null)
  const [filename, setFilename] = useState('recording.webm')
  const [elapsed,  setElapsed]  = useState(0)
  const [error,    setError]    = useState<string | null>(null)
  const audioRef    = useRef<HTMLAudioElement>(null)
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const objectUrl   = useRef<string | null>(null)
  const rec = useRecorder()

  useEffect(() => () => {
    if (objectUrl.current) URL.revokeObjectURL(objectUrl.current)
    if (intervalRef.current) clearInterval(intervalRef.current)
  }, [])

  useEffect(() => {
    if (rec.recording) {
      setElapsed(0)
      intervalRef.current = setInterval(() => {
        setElapsed(s => {
          if (s + 1 >= MAX_RECORD_S) { handleStopRecord(); return s }
          return s + 1
        })
      }, 1000)
    } else if (intervalRef.current) {
      clearInterval(intervalRef.current)
      intervalRef.current = null
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [rec.recording])

  useEffect(() => {
    if (!blob || !audioRef.current) return
    if (objectUrl.current) URL.revokeObjectURL(objectUrl.current)
    objectUrl.current = URL.createObjectURL(blob)
    audioRef.current.src = objectUrl.current
  }, [blob])

  const handleStartRecord = async () => { setBlob(null); setError(null); setFilename('recording.webm'); await rec.start() }
  const handleStopRecord  = async () => { setBlob(await rec.stop()) }

  const onDrop = useCallback(async (files: File[]) => {
    const file = files[0]
    if (!file) return
    setError(null)
    const url = URL.createObjectURL(file)
    const audio = new Audio(url)
    await new Promise<void>(resolve => { audio.onloadedmetadata = () => resolve(); audio.onerror = () => resolve() })
    URL.revokeObjectURL(url)
    if (audio.duration && audio.duration > MAX_UPLOAD_S) {
      setError(t('uploadSizeError', { n: Math.ceil(audio.duration / 60), max: MAX_UPLOAD_S / 60 }))
      return
    }
    setFilename(file.name)
    setBlob(new Blob([await file.arrayBuffer()], { type: file.type }))
  }, [t])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop, accept: { 'audio/*': ['.mp3','.wav','.m4a','.ogg','.flac','.webm','.mp4'] }, maxFiles: 1, disabled: rec.recording,
  })

  const handleDiscard = () => { setBlob(null); rec.cancel(); setElapsed(0); setError(null) }

  const isNearLimit  = elapsed >= WARN_AT_S
  const remaining    = MAX_RECORD_S - elapsed
  const activeBorder = isNearLimit ? 'border-destructive' : 'border-primary'
  const recordBorder = rec.recording ? activeBorder : 'border-border'

  return (
    <div className="space-y-4">
      <div className="flex rounded-xl border overflow-hidden">
        {(['record', 'upload'] as const).map(m => (
          <button key={m} type="button" onClick={() => { setMode(m); handleDiscard() }}
            className={cn('flex-1 flex items-center justify-center gap-1.5 py-2 text-sm font-medium transition-colors',
              mode === m ? 'bg-accent text-primary' : 'bg-background text-muted-foreground hover:bg-muted')}>
            {m === 'record' ? <Mic size={14} /> : <Upload size={14} />}
            {m === 'record' ? t('recordLive') : t('uploadFile')}
          </button>
        ))}
      </div>

      {mode === 'record' && !blob && (
        <div className="flex flex-col items-center gap-4 py-6">
          <div className={cn('relative w-24 h-24 rounded-full border-4 flex items-center justify-center transition-colors', recordBorder)}>
            {rec.recording && <div className="absolute inset-1 rounded-full bg-primary/10 transition-all" style={{ opacity: rec.rms }} />}
            <span className={cn('text-lg font-mono font-bold tabular-nums', isNearLimit && 'text-destructive')}>
              {rec.recording ? formatTime(elapsed) : '00:00'}
            </span>
          </div>
          {isNearLimit && rec.recording && <p className="text-xs text-destructive font-medium">{t('timeRemaining', { t: formatTime(remaining) })}</p>}
          {rec.recording ? (
            <Button variant="destructive" onClick={handleStopRecord} className="gap-2">
              <MicOff size={15} /> Stop · {formatTime(elapsed)}
            </Button>
          ) : (
            <Button onClick={handleStartRecord} className="gap-2"><Mic size={15} /> {t('startRecording')}</Button>
          )}
          <p className="text-xs text-muted-foreground">{t('maxDuration', { n: MAX_RECORD_S / 60 })}</p>
        </div>
      )}

      {mode === 'upload' && !blob && (
        <div {...getRootProps()} className={cn(
          'flex flex-col items-center gap-2 rounded-xl border-2 border-dashed p-8 text-sm transition-colors cursor-pointer',
          isDragActive ? 'border-primary bg-accent text-primary' : 'border-border text-muted-foreground hover:border-primary/50')}>
          <input {...getInputProps()} />
          <Upload size={24} className={isDragActive ? 'text-primary' : 'text-muted-foreground'} />
          <span>{t('dropAudio')}</span>
          <span className="text-xs text-muted-foreground">{t('audioFormats')}</span>
        </div>
      )}

      {error && <p className="text-xs text-destructive text-center">{error}</p>}

      {blob && (
        <div className="space-y-3 rounded-xl border bg-muted/30 p-4">
          <div className="flex items-center gap-2">
            <CheckCircle2 size={16} className="text-green-600 shrink-0" />
            <p className="text-sm font-medium truncate flex-1">{filename}</p>
          </div>
          {/* eslint-disable-next-line jsx-a11y/media-has-caption */}
          <audio ref={audioRef} controls className="w-full h-10" />
          <div className="flex items-center gap-2 pt-1">
            <Button className="flex-1 gap-1.5" onClick={() => onConfirm(blob, filename)}>
              <Play size={14} /> {t('transcribeAndAdd')}
            </Button>
            <Button variant="ghost" size="icon" onClick={handleDiscard} title={t('discard')} className="h-9 w-9">
              <Trash2 size={15} className="text-muted-foreground" />
            </Button>
          </div>
        </div>
      )}
    </div>
  )
}

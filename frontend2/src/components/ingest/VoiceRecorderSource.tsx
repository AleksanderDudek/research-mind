'use client'

import { useCallback, useEffect, useRef, useState } from 'react'
import { useDropzone } from 'react-dropzone'
import { Mic, MicOff, Play, Trash2, Upload, CheckCircle2 } from 'lucide-react'
import { cn } from '@/lib/utils'
import { useRecorder } from '@/hooks/useRecorder'
import { Button } from '@/components/ui/Button'

const MAX_RECORD_S = 5 * 60      // 5 minutes
const MAX_UPLOAD_S = 30 * 60     // 30 minutes
const WARN_AT_S    = MAX_RECORD_S - 30  // warn 30 s before limit

type Mode = 'record' | 'upload'

interface Props {
  /** Called with the confirmed audio Blob, ready for transcription. */
  readonly onConfirm: (blob: Blob, filename: string) => void
}

function formatTime(seconds: number): string {
  const m = Math.floor(seconds / 60).toString().padStart(2, '0')
  const s = (seconds % 60).toString().padStart(2, '0')
  return `${m}:${s}`
}

export function VoiceRecorderSource({ onConfirm }: Props) {
  const [mode,      setMode]      = useState<Mode>('record')
  const [blob,      setBlob]      = useState<Blob | null>(null)
  const [filename,  setFilename]  = useState('recording.webm')
  const [elapsed,   setElapsed]   = useState(0)
  const [error,     setError]     = useState<string | null>(null)
  const audioRef   = useRef<HTMLAudioElement>(null)
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const objectUrl  = useRef<string | null>(null)

  const rec = useRecorder()

  // Release object URLs on cleanup
  useEffect(() => () => {
    if (objectUrl.current) { URL.revokeObjectURL(objectUrl.current) }
    if (intervalRef.current) { clearInterval(intervalRef.current) }
  }, [])

  // Tick timer while recording
  useEffect(() => {
    if (rec.recording) {
      setElapsed(0)
      intervalRef.current = setInterval(() => {
        setElapsed(s => {
          if (s + 1 >= MAX_RECORD_S) {
            handleStopRecord()
            return s
          }
          return s + 1
        })
      }, 1000)
    } else {
      if (intervalRef.current) { clearInterval(intervalRef.current); intervalRef.current = null }
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [rec.recording])

  // Attach blob to preview player
  useEffect(() => {
    if (!blob || !audioRef.current) { return }
    if (objectUrl.current) { URL.revokeObjectURL(objectUrl.current) }
    objectUrl.current = URL.createObjectURL(blob)
    audioRef.current.src = objectUrl.current
  }, [blob])

  const handleStartRecord = async () => {
    setBlob(null)
    setError(null)
    setFilename('recording.webm')
    await rec.start()
  }

  const handleStopRecord = async () => {
    const recorded = await rec.stop()
    setBlob(recorded)
  }

  const onDrop = useCallback(async (files: File[]) => {
    const file = files[0]
    if (!file) { return }
    setError(null)

    // Check duration via a temporary Audio element
    const url = URL.createObjectURL(file)
    const audio = new Audio(url)
    await new Promise<void>(resolve => {
      audio.onloadedmetadata = () => resolve()
      audio.onerror = () => { resolve() }
    })
    URL.revokeObjectURL(url)

    if (audio.duration && audio.duration > MAX_UPLOAD_S) {
      setError(`File is ${Math.ceil(audio.duration / 60)} min — max upload is 30 min.`)
      return
    }

    setFilename(file.name)
    const buf = await file.arrayBuffer()
    setBlob(new Blob([buf], { type: file.type }))
  }, [])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { 'audio/*': ['.mp3', '.wav', '.m4a', '.ogg', '.flac', '.webm', '.mp4'] },
    maxFiles: 1,
    disabled: rec.recording,
  })

  const handleDiscard = () => {
    setBlob(null)
    rec.cancel()
    setElapsed(0)
    setError(null)
  }

  const isNearLimit = elapsed >= WARN_AT_S
  const remaining   = MAX_RECORD_S - elapsed

  return (
    <div className="space-y-4">
      {/* Mode toggle */}
      <div className="flex rounded-xl border border-border overflow-hidden">
        {(['record', 'upload'] as const).map(m => (
          <button
            key={m}
            type="button"
            onClick={() => { setMode(m); handleDiscard() }}
            className={cn(
              'flex-1 flex items-center justify-center gap-1.5 py-2 text-sm font-medium transition-colors',
              mode === m ? 'bg-brand-light text-brand' : 'bg-surface text-slate-500 hover:bg-surface-2',
            )}
          >
            {m === 'record' ? <Mic size={14} /> : <Upload size={14} />}
            {m === 'record' ? 'Record live' : 'Upload file'}
          </button>
        ))}
      </div>

      {/* Record tab */}
      {mode === 'record' && !blob && (
        <div className="flex flex-col items-center gap-4 py-6">
          {/* Timer ring */}
          <div className={cn(
            'relative w-24 h-24 rounded-full border-4 flex items-center justify-center transition-colors',
            rec.recording
              ? isNearLimit ? 'border-red-400' : 'border-brand'
              : 'border-border',
          )}>
            {/* Volume fill */}
            {rec.recording && (
              <div
                className="absolute inset-1 rounded-full bg-brand/10 transition-all"
                style={{ opacity: rec.rms }}
              />
            )}
            <span className={cn('text-lg font-mono font-bold tabular-nums', isNearLimit && 'text-red-500')}>
              {rec.recording ? formatTime(elapsed) : '00:00'}
            </span>
          </div>

          {isNearLimit && rec.recording && (
            <p className="text-xs text-red-500 font-medium">
              {formatTime(remaining)} remaining
            </p>
          )}

          {!rec.recording ? (
            <Button variant="primary" onClick={handleStartRecord} className="gap-2">
              <Mic size={15} /> Start recording
            </Button>
          ) : (
            <Button variant="danger" onClick={handleStopRecord} className="gap-2">
              <MicOff size={15} /> Stop · {formatTime(elapsed)}
            </Button>
          )}

          <p className="text-xs text-slate-400">Max {MAX_RECORD_S / 60} minutes</p>
        </div>
      )}

      {/* Upload tab */}
      {mode === 'upload' && !blob && (
        <div
          {...getRootProps()}
          className={cn(
            'flex flex-col items-center gap-2 rounded-xl border-2 border-dashed p-8 text-sm transition-colors cursor-pointer',
            isDragActive ? 'border-brand bg-brand-light text-brand' : 'border-border text-slate-400 hover:border-brand/50',
          )}
        >
          <input {...getInputProps()} />
          <Upload size={24} className={isDragActive ? 'text-brand' : 'text-slate-300'} />
          <span>Drop an audio file or click to browse</span>
          <span className="text-xs text-slate-400">MP3, WAV, M4A, OGG, FLAC, WebM · max 30 min</span>
        </div>
      )}

      {error && <p className="text-xs text-red-500 text-center">{error}</p>}

      {/* Preview + confirm — shown after recording or upload */}
      {blob && (
        <div className="space-y-3 rounded-xl border border-border bg-surface-2 p-4">
          <div className="flex items-center gap-2">
            <CheckCircle2 size={16} className="text-green-600 shrink-0" />
            <p className="text-sm font-medium text-slate-700 truncate flex-1">{filename}</p>
          </div>

          {/* Native audio preview */}
          {/* eslint-disable-next-line jsx-a11y/media-has-caption */}
          <audio ref={audioRef} controls className="w-full h-10" />

          <div className="flex items-center gap-2 pt-1">
            <Button
              variant="primary"
              className="flex-1 gap-1.5"
              onClick={() => onConfirm(blob, filename)}
            >
              <Play size={14} /> Transcribe &amp; add as source
            </Button>
            <Button variant="ghost" size="icon" onClick={handleDiscard} title="Discard">
              <Trash2 size={15} className="text-slate-400" />
            </Button>
          </div>
        </div>
      )}
    </div>
  )
}

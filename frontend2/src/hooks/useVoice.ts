'use client'

import { useCallback, useEffect, useRef, useState } from 'react'
import { query as queryApi } from '@/lib/api'

export type VoiceStatus = 'idle' | 'recording' | 'processing' | 'confirming' | 'speaking'

export interface LowConfidenceResult { text: string; suggestion: string }

interface UseVoiceOptions {
  silenceMs?:       number   // ms of silence before auto-submit (default 2500)
  silenceThresh?:   number   // RMS threshold 0..1 (default 0.012)
  minSpeechMs?:     number   // ms before silence detection starts (default 800)
  onTranscribed?:   (text: string) => void
  onLowConfidence?: (result: LowConfidenceResult) => void
  onError?:         (msg: string) => void
}

export function useVoice({
  silenceMs     = 2500,
  silenceThresh = 0.012,
  minSpeechMs   = 800,
  onTranscribed,
  onLowConfidence,
  onError,
}: UseVoiceOptions = {}) {
  const [status, setStatus] = useState<VoiceStatus>('idle')
  const [rms, setRms]       = useState(0)

  // ── Stable refs for mutable values ────────────────────────────────────────
  // Storing callbacks in refs means _stopRecording and _checkSilence
  // never need to be recreated when the caller's props change.
  // This eliminates the stale-closure bug caused by setRms triggering
  // re-renders that recreate onTranscribed/onError on every frame.
  const onTranscribedRef   = useRef(onTranscribed)
  const onLowConfidenceRef = useRef(onLowConfidence)
  const onErrorRef         = useRef(onError)
  const silenceMsRef       = useRef(silenceMs)
  const silenceThreshRef   = useRef(silenceThresh)
  const minSpeechMsRef     = useRef(minSpeechMs)

  // Keep refs in sync with latest props — no re-render caused
  useEffect(() => {
    onTranscribedRef.current   = onTranscribed
    onLowConfidenceRef.current = onLowConfidence
    onErrorRef.current         = onError
    silenceMsRef.current       = silenceMs
    silenceThreshRef.current   = silenceThresh
    minSpeechMsRef.current     = minSpeechMs
  })

  // ── Hardware refs ──────────────────────────────────────────────────────────
  const recorderRef   = useRef<MediaRecorder | null>(null)
  const chunksRef     = useRef<Blob[]>([])
  const analyserRef   = useRef<AnalyserNode | null>(null)
  const ctxRef        = useRef<AudioContext | null>(null)
  const rafRef        = useRef<number | null>(null)
  const silStartRef   = useRef<number | null>(null)
  const recStartRef   = useRef<number>(0)
  const activeRef     = useRef(false)
  const abortedRef    = useRef(false)

  const _cleanup = () => {
    if (rafRef.current !== null) { cancelAnimationFrame(rafRef.current); rafRef.current = null }
    if (ctxRef.current) ctxRef.current.close().catch(() => {})
    recorderRef.current?.stream.getTracks().forEach(t => t.stop())
    recorderRef.current = null
    analyserRef.current = null
    ctxRef.current      = null
    chunksRef.current   = []
    setRms(0)
  }

  // ── Stop recording + transcribe ────────────────────────────────────────────
  // Stable: only refs used — no deps on caller props
  const _stopRecording = useCallback(() => {
    const recorder = recorderRef.current
    if (!recorder) return

    // Cancel the rAF loop immediately
    if (rafRef.current !== null) { cancelAnimationFrame(rafRef.current); rafRef.current = null }

    setStatus('processing')
    recorder.onstop = async () => {
      if (abortedRef.current) return
      try {
        const blob = new Blob(chunksRef.current, { type: 'audio/webm' })
        if (!blob.size) {
          onErrorRef.current?.("No audio captured.")
          return
        }
        const res  = await queryApi.transcribe(blob)
        const text = res.text?.trim()
        if (text) {
          onTranscribedRef.current?.(text)
        } else {
          onErrorRef.current?.("Didn't catch that.")
        }
      } catch (err) {
        console.warn('[useVoice] transcription error:', err)
        onErrorRef.current?.('Transcription failed.')
      } finally {
        // Allow the next startListening() call to proceed
        activeRef.current = false
        setStatus('idle')
      }
    }

    recorder.stop()
    recorder.stream.getTracks().forEach(t => t.stop())
    recorderRef.current = null
  }, [])  // stable — uses only refs

  // ── Silence detection loop ─────────────────────────────────────────────────
  // Stable: only refs used — immune to re-renders caused by setRms
  const _checkSilence = useCallback(() => {
    if (!activeRef.current) return
    const analyser = analyserRef.current
    if (!analyser) return

    const data = new Uint8Array(analyser.fftSize)
    analyser.getByteTimeDomainData(data)
    const sum = data.reduce((s, v) => s + ((v - 128) / 128) ** 2, 0)
    const r   = Math.sqrt(sum / data.length)
    setRms(Math.min(1, r * 5))

    const elapsed = Date.now() - recStartRef.current
    if (r < silenceThreshRef.current && elapsed > minSpeechMsRef.current) {
      if (!silStartRef.current) silStartRef.current = Date.now()
      if (Date.now() - silStartRef.current >= silenceMsRef.current) {
        _stopRecording()
        return   // do NOT schedule another frame — _stopRecording owns teardown
      }
    } else {
      silStartRef.current = null
    }

    rafRef.current = requestAnimationFrame(_checkSilence)
  }, [_stopRecording])  // _stopRecording is stable, so _checkSilence is stable too

  // ── Public API ─────────────────────────────────────────────────────────────
  const startListening = useCallback(async () => {
    if (activeRef.current) return
    activeRef.current  = true
    abortedRef.current = false

    try {
      const stream   = await navigator.mediaDevices.getUserMedia({ audio: true })
      const ctx      = new AudioContext()
      const analyser = ctx.createAnalyser()
      analyser.fftSize = 512
      ctx.createMediaStreamSource(stream).connect(analyser)
      ctxRef.current      = ctx
      analyserRef.current = analyser

      chunksRef.current   = []
      silStartRef.current = null
      recStartRef.current = Date.now()

      const recorder = new MediaRecorder(stream)
      recorder.ondataavailable = (e) => { if (e.data.size) chunksRef.current.push(e.data) }
      recorder.start(100)
      recorderRef.current = recorder

      setStatus('recording')
      rafRef.current = requestAnimationFrame(_checkSilence)
    } catch (e) {
      console.warn('[useVoice] microphone error:', e)
      activeRef.current = false
      onErrorRef.current?.('Microphone access denied.')
      setStatus('idle')
    }
  }, [_checkSilence])

  const stopListening = useCallback(() => {
    activeRef.current  = false
    abortedRef.current = true
    _cleanup()
    setStatus('idle')
  }, [])

  // Cleanup on unmount
  useEffect(() => () => { activeRef.current = false; _cleanup() }, [])

  return { status, rms, startListening, stopListening }
}

/** Speak *text* via the Web Speech API.
 *  Returns a Promise that resolves when the utterance finishes (onend) OR
 *  is cancelled — e.g. by the user toggling TTS off (onerror/onend).
 *  Callers await this before resuming microphone recording. */
export function browserTts(text: string, lang: string): Promise<void> {
  const synth = globalThis.speechSynthesis
  if (!synth) return Promise.resolve()

  synth.cancel()

  const u   = new SpeechSynthesisUtterance(text.slice(0, 800))
  const tag = lang === 'pl' ? 'pl' : 'en'
  u.lang    = lang === 'pl' ? 'pl-PL' : 'en-US'
  u.rate    = 1

  const voices     = synth.getVoices()
  const localVoice = voices.find(v => v.lang.toLowerCase().startsWith(tag) && v.localService)
  const anyVoice   = voices.find(v => v.lang.toLowerCase().startsWith(tag))
  const chosen     = localVoice ?? anyVoice
  if (chosen) u.voice = chosen

  return new Promise<void>(resolve => {
    u.onend   = () => resolve()
    u.onerror = () => resolve()
    synth.speak(u)
  })
}

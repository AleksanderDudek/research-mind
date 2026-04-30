'use client'

import { useCallback, useEffect, useRef, useState } from 'react'
import { query as queryApi } from '@/lib/api'

export type VoiceStatus = 'idle' | 'recording' | 'processing' | 'confirming'

export interface LowConfidenceResult { text: string; suggestion: string }

interface UseVoiceOptions {
  silenceMs?:     number    // ms of silence before auto-submit (default 2500)
  silenceThresh?: number    // RMS threshold 0..1 (default 0.012)
  minSpeechMs?:   number    // ms of audio before silence detection starts (default 800)
  onTranscribed?: (text: string) => void
  onLowConfidence?: (result: LowConfidenceResult) => void
  onError?: (msg: string) => void
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
    if (rafRef.current) cancelAnimationFrame(rafRef.current)
    if (ctxRef.current) ctxRef.current.close().catch(() => {})
    recorderRef.current?.stream.getTracks().forEach(t => t.stop())
    recorderRef.current = null
    analyserRef.current = null
    ctxRef.current  = null
    rafRef.current  = null
    chunksRef.current = []
    setRms(0)
  }

  const _checkSilence = () => {
    const analyser = analyserRef.current
    if (!analyser || !activeRef.current) return
    const data = new Uint8Array(analyser.fftSize)
    analyser.getByteTimeDomainData(data)
    const sum = data.reduce((s, v) => s + ((v - 128) / 128) ** 2, 0)
    const r   = Math.sqrt(sum / data.length)
    setRms(Math.min(1, r * 5))

    const elapsed = Date.now() - recStartRef.current
    if (r < silenceThresh && elapsed > minSpeechMs) {
      if (!silStartRef.current) silStartRef.current = Date.now()
      if (Date.now() - silStartRef.current >= silenceMs) {
        _stopRecording()
        return
      }
    } else {
      silStartRef.current = null
    }
    rafRef.current = requestAnimationFrame(_checkSilence)
  }

  const _stopRecording = useCallback(() => {
    const recorder = recorderRef.current
    if (!recorder) return
    setStatus('processing')
    recorder.onstop = async () => {
      if (abortedRef.current) return
      try {
        const blob = new Blob(chunksRef.current, { type: 'audio/webm' })
        const res  = await queryApi.transcribe(blob)
        const text = res.text?.trim()
        if (!text) {
          onError?.("Didn't catch that.")
          setStatus(activeRef.current ? 'idle' : 'idle')
        } else {
          onTranscribed?.(text)
        }
      } catch {
        onError?.('Transcription failed.')
      } finally {
        if (activeRef.current) {
          setStatus('idle')
        }
      }
    }
    recorder.stop()
    recorder.stream.getTracks().forEach(t => t.stop())
    recorderRef.current = null
    if (rafRef.current) cancelAnimationFrame(rafRef.current)
  }, [silenceMs, silenceThresh, minSpeechMs, onTranscribed, onError])

  const startListening = useCallback(async () => {
    if (activeRef.current) return
    activeRef.current  = true
    abortedRef.current = false

    try {
      const stream    = await navigator.mediaDevices.getUserMedia({ audio: true })
      const ctx       = new AudioContext()
      const analyser  = ctx.createAnalyser()
      analyser.fftSize = 512
      ctx.createMediaStreamSource(stream).connect(analyser)
      ctxRef.current      = ctx
      analyserRef.current = analyser

      const recorder = new MediaRecorder(stream)
      chunksRef.current  = []
      silStartRef.current = null
      recStartRef.current = Date.now()
      recorder.ondataavailable = (e) => { if (e.data.size) chunksRef.current.push(e.data) }
      recorder.start(100)
      recorderRef.current = recorder
      setStatus('recording')
      rafRef.current = requestAnimationFrame(_checkSilence)
    } catch (e) {
      activeRef.current = false
      onError?.('Microphone access denied.')
      setStatus('idle')
    }
  }, [_checkSilence, onError])

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

/** Speak *text* via the Web Speech API using the first available voice for *lang*.
 *  Always picks the same voice across calls (no random variation). */
export function browserTts(text: string, lang: string) {
  const synth = globalThis.speechSynthesis
  if (!synth) return

  synth.cancel()

  const u    = new SpeechSynthesisUtterance(text.slice(0, 800))
  const tag  = lang === 'pl' ? 'pl' : 'en'
  u.lang     = lang === 'pl' ? 'pl-PL' : 'en-US'
  u.rate     = 1

  // Pick the first available local voice for the language so the voice is
  // consistent across utterances.  Falls back to browser default when the
  // voices list is empty (e.g. before voiceschanged fires on Chrome).
  const voices  = synth.getVoices()
  const localVoice = voices.find(v => v.lang.toLowerCase().startsWith(tag) && v.localService)
  const anyVoice   = voices.find(v => v.lang.toLowerCase().startsWith(tag))
  const chosen     = localVoice ?? anyVoice
  if (chosen) u.voice = chosen

  synth.speak(u)
}

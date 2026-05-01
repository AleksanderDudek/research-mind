'use client'

/**
 * useVoiceLoop — continuous voice conversation loop.
 *
 * State machine (one turn):
 *   recording → (silence) → transcribing → thinking → speaking → recording → …
 *
 * Design principles
 * -----------------
 * • All mutable values live in refs. No callback is ever stale because
 *   nothing is captured in a closure — everything is read from refs at call time.
 * • The loop is a plain async function that tail-calls itself; no timers or
 *   polling. Each phase is a single awaited Promise.
 * • The caller passes onMessage / onPersist; both are kept in refs so
 *   the loop always uses the latest versions without restarting.
 */

import { useCallback, useEffect, useRef, useState } from 'react'
import { query as queryApi } from '@/lib/api'
import { browserTts } from './useVoice'
import type { Message } from '@/lib/types'

export type LoopState = 'idle' | 'recording' | 'transcribing' | 'thinking' | 'speaking'

// Silence-detection constants
const SILENCE_THRESH  = 0.012   // RMS below this = silence
const SILENCE_MS      = 2500    // silence must persist for this long (ms)
const MIN_SPEECH_MS   = 800     // minimum recording before silence detection kicks in

interface Options {
  readonly contextId:  string | null
  readonly ttsEnabled: boolean
  readonly lang:       string
  readonly onMessage:  (msg: Message) => void
  readonly onPersist:  (msg: Omit<Message, 'timestamp'>) => Promise<void>
}

export function useVoiceLoop({ contextId, ttsEnabled, lang, onMessage, onPersist }: Options) {
  const [state, setState] = useState<LoopState>('idle')
  const [rms,   setRms]   = useState(0)

  // ── Lifecycle ────────────────────────────────────────────────────────────
  const activeRef = useRef(false)               // is the loop running?
  const abortRef  = useRef<AbortController | null>(null)  // current agent request

  // ── Audio hardware ────────────────────────────────────────────────────────
  const ctxRef      = useRef<AudioContext | null>(null)
  const analyserRef = useRef<AnalyserNode | null>(null)
  const recRef      = useRef<MediaRecorder | null>(null)
  const rafRef      = useRef<number | null>(null)

  // ── Option mirrors — updated every render, never cause re-renders ─────────
  const ctxIdRef  = useRef(contextId)
  const ttsRef    = useRef(ttsEnabled)
  const langRef   = useRef(lang)
  const msgRef    = useRef(onMessage)
  const persRef   = useRef(onPersist)
  useEffect(() => {
    ctxIdRef.current = contextId
    ttsRef.current   = ttsEnabled
    langRef.current  = lang
    msgRef.current   = onMessage
    persRef.current  = onPersist
  })   // runs after every render — no deps needed

  // ── Hardware teardown ─────────────────────────────────────────────────────
  const _cleanup = useCallback(() => {
    if (rafRef.current !== null) { cancelAnimationFrame(rafRef.current); rafRef.current = null }
    ctxRef.current?.close().catch(() => {})
    recRef.current?.stream.getTracks().forEach(t => t.stop())
    ctxRef.current = analyserRef.current = recRef.current = null
    setRms(0)
  }, [])

  // ── Phase 1: record until silence ─────────────────────────────────────────
  // Resolves with the audio Blob when silence is detected.
  // Rejects (silently) when the loop is stopped or mic access is denied.
  const _record = useCallback((): Promise<Blob> => new Promise(async (resolve, reject) => {
    if (!activeRef.current) { reject(); return }

    let stream: MediaStream
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true })
    } catch {
      reject(new Error('mic-denied'))
      return
    }

    if (!activeRef.current) { stream.getTracks().forEach(t => t.stop()); reject(); return }

    // Set up Web Audio analyser for silence detection + volume meter
    const ctx      = new AudioContext()
    const analyser = ctx.createAnalyser()
    analyser.fftSize = 512
    ctx.createMediaStreamSource(stream).connect(analyser)
    ctxRef.current      = ctx
    analyserRef.current = analyser

    // Set up MediaRecorder
    const chunks: Blob[] = []
    const recorder       = new MediaRecorder(stream)
    recorder.ondataavailable = e => { if (e.data.size) chunks.push(e.data) }
    recorder.start(100)   // fire ondataavailable every 100 ms
    recRef.current = recorder

    let inSilence    = false
    let silenceStart = 0
    const recStart   = Date.now()

    // Called when silence threshold is reached OR loop is stopped
    const finish = () => {
      if (rafRef.current !== null) { cancelAnimationFrame(rafRef.current); rafRef.current = null }
      recorder.onstop = () => {
        stream.getTracks().forEach(t => t.stop())
        ctx.close().catch(() => {})
        ctxRef.current = analyserRef.current = recRef.current = null
        setRms(0)
        // Resolve only if the loop is still active
        if (activeRef.current) {
          resolve(new Blob(chunks, { type: 'audio/webm' }))
        } else {
          reject()
        }
      }
      recorder.stop()
    }

    // rAF loop: measure RMS, detect silence
    const check = () => {
      if (!activeRef.current) { finish(); return }

      const data = new Uint8Array(analyser.fftSize)
      analyser.getByteTimeDomainData(data)
      const r = Math.sqrt(data.reduce((s, v) => s + ((v - 128) / 128) ** 2, 0) / data.length)
      setRms(Math.min(1, r * 5))

      const elapsed = Date.now() - recStart
      if (r < SILENCE_THRESH && elapsed > MIN_SPEECH_MS) {
        if (!inSilence) { inSilence = true; silenceStart = Date.now() }
        if (Date.now() - silenceStart >= SILENCE_MS) { finish(); return }
      } else {
        inSilence = false
      }

      rafRef.current = requestAnimationFrame(check)
    }

    rafRef.current = requestAnimationFrame(check)
  }), [])

  // ── Main loop — one turn, then tail-calls itself ───────────────────────────
  const _loop = useCallback(async () => {
    // ── 1. Record ──────────────────────────────────────────────────────────
    setState('recording')
    let blob: Blob
    try {
      blob = await _record()
    } catch {
      return   // loop stopped or mic denied — exit cleanly
    }
    if (!activeRef.current) return

    // ── 2. Transcribe ──────────────────────────────────────────────────────
    setState('transcribing')
    let text: string
    try {
      const r = await queryApi.transcribe(blob, langRef.current)
      text = r.text?.trim() ?? ''
    } catch {
      // Network error — wait briefly then loop again
      await new Promise(r => setTimeout(r, 1000))
      if (activeRef.current) _loop()
      return
    }
    if (!activeRef.current) return

    // Nothing captured (silence, noise) — loop immediately
    if (!text) { if (activeRef.current) _loop(); return }

    // ── 3. Think (agent) ───────────────────────────────────────────────────
    setState('thinking')

    const userMsg: Message = {
      role: 'user', content: `🎤 ${text}`, timestamp: new Date().toISOString(),
    }
    msgRef.current(userMsg)
    void persRef.current({ role: 'user', content: text })

    const ctrl = new AbortController()
    abortRef.current = ctrl

    let answer: string
    let sources: Message['sources']
    try {
      const r = await queryApi.ask(text, ctxIdRef.current, ctrl.signal)
      answer  = r.answer
      sources = r.sources
    } catch (err) {
      abortRef.current = null
      // AbortError = user interrupted; any other error = retry
      if (activeRef.current) _loop()
      return
    }
    abortRef.current = null
    if (!activeRef.current) return

    const asstMsg: Message = {
      role: 'assistant', content: answer, timestamp: new Date().toISOString(), sources,
    }
    msgRef.current(asstMsg)
    void persRef.current({ role: 'assistant', content: answer, sources })

    // ── 4. Speak (TTS) — awaited so mic reopens only after speech ends ─────
    if (ttsRef.current && activeRef.current) {
      setState('speaking')
      await browserTts(answer, langRef.current)
    }
    if (!activeRef.current) return

    // ── 5. Next turn ───────────────────────────────────────────────────────
    _loop()
  }, [_record])

  // ── Public API ─────────────────────────────────────────────────────────────
  /** Start the continuous loop. No-op if already running. */
  const start = useCallback(() => {
    if (activeRef.current) return
    activeRef.current = true
    _loop()
  }, [_loop])

  /** Stop everything immediately and return to idle. */
  const stop = useCallback(() => {
    activeRef.current = false
    abortRef.current?.abort()
    globalThis.speechSynthesis?.cancel()
    _cleanup()
    setState('idle')
  }, [_cleanup])

  /** Abort the current agent request; loop restarts recording automatically. */
  const interrupt = useCallback(() => {
    abortRef.current?.abort()
  }, [])

  // Full teardown on unmount
  useEffect(() => () => {
    activeRef.current = false
    abortRef.current?.abort()
    globalThis.speechSynthesis?.cancel()
    _cleanup()
  }, [_cleanup])

  return { state, rms, start, stop, interrupt }
}

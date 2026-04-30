'use client'

import { useCallback, useRef, useState } from 'react'

export interface RecorderResult {
  recording:  boolean
  rms:        number          // 0..1 live amplitude for volume meter
  start:      () => Promise<void>
  stop:       () => Promise<Blob>
  cancel:     () => void
}

export function useRecorder(): RecorderResult {
  const [recording, setRecording] = useState(false)
  const [rms, setRms]             = useState(0)

  const recorderRef  = useRef<MediaRecorder | null>(null)
  const chunksRef    = useRef<Blob[]>([])
  const rafRef       = useRef<number | null>(null)
  const analyserRef  = useRef<AnalyserNode | null>(null)
  const ctxRef       = useRef<AudioContext | null>(null)

  const _stopAnalyser = () => {
    if (rafRef.current)    cancelAnimationFrame(rafRef.current)
    if (ctxRef.current)    ctxRef.current.close().catch(() => {})
    rafRef.current    = null
    analyserRef.current = null
    ctxRef.current    = null
    setRms(0)
  }

  const start = useCallback(async () => {
    const stream    = await navigator.mediaDevices.getUserMedia({ audio: true })
    const ctx       = new AudioContext()
    const analyser  = ctx.createAnalyser()
    analyser.fftSize = 256
    ctx.createMediaStreamSource(stream).connect(analyser)
    ctxRef.current    = ctx
    analyserRef.current = analyser

    const recorder = new MediaRecorder(stream)
    chunksRef.current = []
    recorder.ondataavailable = (e) => { if (e.data.size) chunksRef.current.push(e.data) }
    recorder.start(100)
    recorderRef.current = recorder
    setRecording(true)

    const data = new Uint8Array(analyser.fftSize)
    const tick = () => {
      analyser.getByteTimeDomainData(data)
      const sum = data.reduce((s, v) => s + ((v - 128) / 128) ** 2, 0)
      setRms(Math.min(1, Math.sqrt(sum / data.length) * 5))
      rafRef.current = requestAnimationFrame(tick)
    }
    rafRef.current = requestAnimationFrame(tick)
  }, [])

  const stop = useCallback((): Promise<Blob> =>
    new Promise((resolve) => {
      const recorder = recorderRef.current
      if (!recorder) { resolve(new Blob()); return }
      recorder.onstop = () => {
        resolve(new Blob(chunksRef.current, { type: 'audio/webm' }))
        chunksRef.current = []
      }
      recorder.stop()
      recorder.stream.getTracks().forEach(t => t.stop())
      recorderRef.current = null
      _stopAnalyser()
      setRecording(false)
    }),
  [])

  const cancel = useCallback(() => {
    recorderRef.current?.stream.getTracks().forEach(t => t.stop())
    recorderRef.current = null
    chunksRef.current   = []
    _stopAnalyser()
    setRecording(false)
  }, [])

  return { recording, rms, start, stop, cancel }
}

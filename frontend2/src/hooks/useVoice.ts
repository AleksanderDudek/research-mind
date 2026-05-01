'use client'

/**
 * browserTts — speak text via the browser Web Speech API.
 * Returns a Promise that resolves when the utterance ends (onend) or is
 * cancelled externally (onerror, e.g. synth.cancel() when TTS is toggled off).
 */
export function browserTts(text: string, lang: string): Promise<void> {
  const synth = globalThis.speechSynthesis
  if (!synth) return Promise.resolve()

  synth.cancel()

  const u   = new SpeechSynthesisUtterance(text.slice(0, 800))
  const tag = lang === 'pl' ? 'pl' : 'en'
  u.lang    = lang === 'pl' ? 'pl-PL' : 'en-US'
  u.rate    = 1

  // Prefer a local voice for the language so the choice is consistent.
  const voices     = synth.getVoices()
  const localVoice = voices.find(v => v.lang.toLowerCase().startsWith(tag) && v.localService)
  const anyVoice   = voices.find(v => v.lang.toLowerCase().startsWith(tag))
  if (localVoice ?? anyVoice) u.voice = (localVoice ?? anyVoice)!

  return new Promise<void>(resolve => {
    u.onend   = () => resolve()   // normal completion
    u.onerror = () => resolve()   // fired by synth.cancel()
    synth.speak(u)
  })
}

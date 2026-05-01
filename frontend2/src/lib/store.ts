import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { Context, Lang, Message } from './types'

interface AppState {
  lang:          Lang
  activeContext: Context | null
  messages:      Message[]
  // TTS — persisted so the preference survives page reloads
  ttsEnabled:    boolean
  setLang:          (lang: Lang)          => void
  setActiveContext: (ctx: Context | null) => void
  setMessages:      (msgs: Message[])     => void
  appendMessage:    (msg: Message)        => void
  setTtsEnabled:    (on: boolean)         => void
}

export const useAppStore = create<AppState>()(
  persist(
    (set) => ({
      lang:          'en',
      activeContext: null,
      messages:      [],
      ttsEnabled:    true,           // voice ON by default
      setLang:          (lang) => set({ lang }),
      setActiveContext: (ctx)  => set({ activeContext: ctx, messages: [] }),
      appendMessage:    (msg)  => set((s) => ({ messages: [...s.messages, msg] })),
      setMessages:      (msgs) => set({ messages: msgs }),
      setTtsEnabled:    (on)   => set({ ttsEnabled: on }),
    }),
    {
      name:    'researchmind-settings',
      // Only persist user preferences — not session data
      partialize: (s) => ({ ttsEnabled: s.ttsEnabled }),
    },
  ),
)

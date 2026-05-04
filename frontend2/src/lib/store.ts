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
  updateMessage:    (timestamp: string, updater: (msg: Message) => Message) => void
  removeMessage:    (timestamp: string)   => void
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
      appendMessage:    (msg)     => set((s) => ({ messages: [...s.messages, msg] })),
      updateMessage:    (ts, fn)  => set((s) => ({ messages: s.messages.map(m => m.timestamp === ts ? fn(m) : m) })),
      removeMessage:    (ts)      => set((s) => ({ messages: s.messages.filter(m => m.timestamp !== ts) })),
      setMessages:      (msgs)    => set({ messages: msgs }),
      setTtsEnabled:    (on)      => set({ ttsEnabled: on }),
    }),
    {
      name:       'researchmind-settings',
      partialize: (s) => ({ ttsEnabled: s.ttsEnabled }),
      // React 19 concurrent mode reads localStorage synchronously during hydration,
      // which triggers a state update mid-hydration and causes error #185.
      // skipHydration keeps the default values during the initial render so the
      // server-rendered HTML matches; providers.tsx calls rehydrate() after mount.
      skipHydration: true,
    },
  ),
)

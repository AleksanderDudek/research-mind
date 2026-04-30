import { create } from 'zustand'
import type { Context, Lang, Message } from './types'

interface AppState {
  lang:          Lang
  activeContext: Context | null
  messages:      Message[]
  setLang:          (lang: Lang)            => void
  setActiveContext: (ctx: Context | null)   => void
  setMessages:      (msgs: Message[])       => void
  appendMessage:    (msg: Message)          => void
}

export const useAppStore = create<AppState>((set) => ({
  lang:          'en',
  activeContext: null,
  messages:      [],
  setLang:          (lang)    => set({ lang }),
  setActiveContext: (ctx)     => set({ activeContext: ctx, messages: [] }),
  appendMessage:    (msg)     => set((s) => ({ messages: [...s.messages, msg] })),
  setMessages:      (msgs)    => set({ messages: msgs }),
}))

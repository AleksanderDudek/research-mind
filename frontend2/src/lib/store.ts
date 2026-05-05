import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { AppRole } from './supabase'
import type { Context, Lang, Message } from './types'

interface AppState {
  lang:          Lang
  activeContext: Context | null
  messages:      Message[]
  ttsEnabled:    boolean

  // Auth state — populated from Supabase session on mount, not persisted.
  // authReady is false until the initial session + profile check completes
  // (regardless of success or failure). Components should gate rendering on
  // authReady to avoid showing wrong content while auth is still loading.
  authReady: boolean
  userId:   string | null
  orgId:    string | null
  role:     AppRole | null
  fullName: string | null

  setLang:          (lang: Lang)          => void
  setActiveContext: (ctx: Context | null) => void
  setMessages:      (msgs: Message[])     => void
  appendMessage:    (msg: Message)        => void
  updateMessage:    (timestamp: string, updater: (msg: Message) => Message) => void
  removeMessage:    (timestamp: string)   => void
  setTtsEnabled:    (on: boolean)         => void

  setAuthReady: (ready: boolean) => void
  setAuth:  (userId: string, orgId: string, role: AppRole, fullName: string) => void
  clearAuth: () => void
}

export const useAppStore = create<AppState>()(
  persist(
    (set) => ({
      lang:          'en',
      activeContext: null,
      messages:      [],
      ttsEnabled:    true,
      authReady:     false,
      userId:        null,
      orgId:         null,
      role:          null,
      fullName:      null,

      setLang:          (lang) => set({ lang }),
      setActiveContext: (ctx)  => set({ activeContext: ctx, messages: [] }),
      appendMessage:    (msg)     => set((s) => ({ messages: [...s.messages, msg] })),
      updateMessage:    (ts, fn)  => set((s) => ({ messages: s.messages.map(m => m.timestamp === ts ? fn(m) : m) })),
      removeMessage:    (ts)      => set((s) => ({ messages: s.messages.filter(m => m.timestamp !== ts) })),
      setMessages:      (msgs)    => set({ messages: msgs }),
      setTtsEnabled:    (on)      => set({ ttsEnabled: on }),

      setAuthReady: (ready) => set({ authReady: ready }),
      setAuth: (userId, orgId, role, fullName) => set({ userId, orgId, role, fullName }),
      clearAuth: () => set({ authReady: false, userId: null, orgId: null, role: null, fullName: null, activeContext: null, messages: [] }),
    }),
    {
      name:       'researchmind-settings',
      partialize: (s) => ({ ttsEnabled: s.ttsEnabled, lang: s.lang }),
      skipHydration: true,
    },
  ),
)

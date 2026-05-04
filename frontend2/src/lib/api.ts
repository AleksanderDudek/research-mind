import type {
  AgentResult, Context, HistoryEntry, IngestionResult,
  Message, SearchHit, Source, SourceDetail,
} from './types'
import { supabase } from './supabase'

export type StreamEvent =
  | { type: 'chunk'; text: string }
  | { type: 'done'; answer: string; sources: SearchHit[]; action_taken: string }

const base = () =>
  typeof window !== 'undefined'
    ? (process.env.NEXT_PUBLIC_BACKEND_URL ?? 'http://localhost:8001')
    : (process.env.BACKEND_URL ?? 'http://localhost:8001')

async function _getToken(): Promise<string | null> {
  if (globalThis.window === undefined) return null
  const { data } = await supabase.auth.getSession()
  return data.session?.access_token ?? null
}

async function req<T>(
  method: string,
  path: string,
  body?: unknown,
  form?: FormData,
  signal?: AbortSignal,
): Promise<T> {
  const token = await _getToken()
  const init: RequestInit = { method, signal }
  const headers: Record<string, string> = {}
  if (token) headers['Authorization'] = `Bearer ${token}`
  if (form) {
    init.body = form
  } else if (body !== undefined) {
    headers['Content-Type'] = 'application/json'
    init.body = JSON.stringify(body)
  }
  init.headers = headers
  const res = await fetch(`${base()}${path}`, init)
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(String(err?.detail ?? 'Request failed'))
  }
  if (res.status === 204) return undefined as T
  return res.json() as Promise<T>
}

// ── Contexts ──────────────────────────────────────────────────────────────────
export const contexts = {
  list:   ()                      => req<Context[]>('GET',    '/contexts'),
  create: (name?: string)         => req<Context>('POST',   '/contexts', { name }),
  rename: (id: string, name: string) => req<Context>('PATCH', `/contexts/${id}`, { name }),
  delete: (id: string)            => req<void>('DELETE', `/contexts/${id}`),
}

// ── Messages ──────────────────────────────────────────────────────────────────
export const messages = {
  list: (ctxId: string)             => req<Message[]>('GET',  `/contexts/${ctxId}/messages`),
  save: (ctxId: string, msg: Omit<Message, 'timestamp'>) =>
    req<Message>('POST', `/contexts/${ctxId}/messages`, msg),
}

// ── Sources ───────────────────────────────────────────────────────────────────
export const sources = {
  list:   (ctxId: string)                    => req<Source[]>('GET', `/contexts/${ctxId}/sources`),
  detail: (ctxId: string, docId: string)     => req<SourceDetail>('GET', `/contexts/${ctxId}/sources/${docId}/text`),
  delete: (ctxId: string, docId: string)     => req<void>('DELETE', `/contexts/${ctxId}/sources/${docId}`),
  edit:   (ctxId: string, docId: string, text: string, title: string) =>
    req<IngestionResult>('PUT', `/contexts/${ctxId}/sources/${docId}`, { text, title }),
}

// ── History ───────────────────────────────────────────────────────────────────
export const history = {
  list: (ctxId: string) => req<HistoryEntry[]>('GET', `/contexts/${ctxId}/history`),
}

// ── Query ─────────────────────────────────────────────────────────────────────
export const query = {
  ask: (question: string, contextId: string | null, signal?: AbortSignal) =>
    req<AgentResult>('POST', '/query/ask', { question, context_id: contextId }, undefined, signal),

  async *streamAsk(
    question: string,
    contextId: string | null,
    signal?: AbortSignal,
  ): AsyncGenerator<StreamEvent> {
    const token = await _getToken()
    const res = await fetch(`${base()}/query/ask/stream`, {
      method:  'POST',
      headers: {
        'Content-Type':  'application/json',
        ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
      },
      body:    JSON.stringify({ question, context_id: contextId }),
      signal,
    })
    if (!res.ok || !res.body) throw new Error(`HTTP ${res.status}`)

    const reader  = res.body.getReader()
    const decoder = new TextDecoder()
    let buf = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buf += decoder.decode(value, { stream: true })
      const parts = buf.split('\n\n')
      buf = parts.pop() ?? ''
      for (const part of parts) {
        const line = part.trim()
        if (line.startsWith('data: ')) {
          yield JSON.parse(line.slice(6)) as StreamEvent
        }
      }
    }
  },

  transcribe: (audio: Blob, language?: string) => {
    const fd = new FormData()
    fd.append('file', audio, 'voice.webm')
    if (language) fd.append('language', language)
    return req<{ text: string }>('POST', '/query/transcribe', undefined, fd)
  },
}

// ── Ingest ────────────────────────────────────────────────────────────────────
export const ingest = {
  text: (text: string, title: string, contextId: string) =>
    req<IngestionResult>('POST', '/ingest/raw-text', { text, title, context_id: contextId }),

  pdfUrl: (url: string, contextId: string) =>
    req<IngestionResult>('POST', '/ingest/pdf-url', { url, context_id: contextId }),

  webUrl: (url: string, contextId: string) =>
    req<IngestionResult>('POST', '/ingest/web-url', { url, context_id: contextId }),

  pdfUpload: (file: File, contextId: string) => {
    const fd = new FormData()
    fd.append('file', file)
    fd.append('context_id', contextId)
    return req<IngestionResult>('POST', '/ingest/pdf-upload', undefined, fd)
  },

  imageUpload: (file: File, contextId: string, detailLevel = 'standard') => {
    const fd = new FormData()
    fd.append('file', file)
    fd.append('context_id', contextId)
    fd.append('detail_level', detailLevel)
    return req<IngestionResult>('POST', '/ingest/image-upload', undefined, fd)
  },

  audioUpload: (file: File, contextId: string) => {
    const fd = new FormData()
    fd.append('file', file)
    fd.append('context_id', contextId)
    return req<IngestionResult>('POST', '/ingest/audio-upload', undefined, fd)
  },
}

// ── Org management ────────────────────────────────────────────────────────────
export const org = {
  members: () =>
    req<{ id: string; role: string; full_name: string; created_at: string }[]>('GET', '/org/members'),

  invite: (email: string) =>
    req<{ invited: string }>('POST', '/org/invite', { email }),

  removeMember: (userId: string) =>
    req<{ removed: string }>('DELETE', `/org/members/${userId}`),

  allOrgs: () =>
    req<{ id: string; name: string; created_at: string; created_by: string }[]>('GET', '/superadmin/orgs'),

  appoint: (userId: string, role: string) =>
    req<{ user_id: string; role: string }>('POST', '/superadmin/appoint', { user_id: userId, role }),
}

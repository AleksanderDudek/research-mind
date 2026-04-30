import type {
  AgentResult, Context, HistoryEntry, IngestionResult,
  Message, Source, SourceDetail,
} from './types'

const base = () =>
  typeof window !== 'undefined'
    ? (process.env.NEXT_PUBLIC_BACKEND_URL ?? 'http://localhost:8001')
    : (process.env.BACKEND_URL ?? 'http://localhost:8001')

async function req<T>(
  method: string,
  path: string,
  body?: unknown,
  form?: FormData,
  signal?: AbortSignal,
): Promise<T> {
  const init: RequestInit = { method, signal }
  if (form) {
    init.body = form
  } else if (body !== undefined) {
    init.headers = { 'Content-Type': 'application/json' }
    init.body = JSON.stringify(body)
  }
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

  transcribe: (audio: Blob) => {
    const fd = new FormData()
    fd.append('file', audio, 'voice.webm')
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

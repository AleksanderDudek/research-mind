export interface Context {
  context_id: string
  name: string
  created_at: string
  updated_at: string
}

/** A retrieved chunk returned by the agent alongside its answer. */
export interface SearchHit {
  source:      string
  score:       number
  text:        string
  source_type: string
  image_data?: string
}

export interface Message {
  role:         'user' | 'assistant'
  content:      string
  timestamp:    string
  sources?:     SearchHit[]
  action_taken?: string
  iterations?:  number
  critique?:    { score: number }
}

export interface Source {
  document_id: string
  title: string
  source_type: string
  chunk_count: number
  ingested_at: string
  url?: string
}

export interface SourceDetail extends Source {
  raw_text: string
  image_data?: string
  image_mime_type?: string
}

export interface HistoryEntry {
  action: string
  detail: string
  timestamp: string
}

export interface AgentResult {
  answer:       string
  sources:      SearchHit[]
  action_taken: string
  iterations:   number
  critique?:    { score: number }
}

export interface IngestionResult {
  document_id: string
  chunks_ingested: number
  source_type: string
  context_id: string
}

export type Lang = 'en' | 'pl'

export interface OrgMember {
  id:         string
  role:       string
  full_name:  string | null
  created_at: string
}

export interface Organization {
  id:         string
  name:       string
  created_at: string
  created_by: string
}

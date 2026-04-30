'use client'

import { useCallback, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useDropzone } from 'react-dropzone'
import { toast } from 'sonner'
import { Trash2, FileText, Globe, Upload, Type, Image, Mic2, HelpCircle, Mic } from 'lucide-react'
import { ingest as ingestApi, sources as srcApi } from '@/lib/api'
import { useT } from '@/i18n/config'
import { useAppStore } from '@/lib/store'
import type { Source } from '@/lib/types'
import { Button } from '@/components/ui/Button'
import { Input  } from '@/components/ui/Input'
import { Badge  } from '@/components/ui/Badge'
import { ScrollArea } from '@/components/ui/ScrollArea'
import { VoiceRecorderSource } from './VoiceRecorderSource'
import { cn } from '@/lib/utils'

type SourceType = 'pdfUrl' | 'webUrl' | 'upload' | 'text' | 'image' | 'audio' | 'record'

interface TabDef {
  readonly key:      SourceType
  readonly Icon:     typeof FileText
  readonly labelKey: string
  readonly helpKey:  string
}

const TABS: TabDef[] = [
  { key: 'pdfUrl', Icon: FileText, labelKey: 'tabPdfUrl', helpKey: 'Fetch a PDF from a URL and index its content.' },
  { key: 'webUrl', Icon: Globe,    labelKey: 'tabWeb',    helpKey: 'Fetch a web page and index its main content.' },
  { key: 'upload', Icon: Upload,   labelKey: 'tabUpload', helpKey: 'Upload a PDF file from your device.' },
  { key: 'text',   Icon: Type,     labelKey: 'tabText',   helpKey: 'Paste any text — notes, excerpts, summaries.' },
  { key: 'image',  Icon: Image,    labelKey: 'tabImage',  helpKey: 'Upload an image. A vision model will describe it and index the description.' },
  { key: 'audio',  Icon: Mic2,     labelKey: 'tabAudio',  helpKey: 'Upload an audio file. Whisper will transcribe it.' },
  { key: 'record', Icon: Mic,      labelKey: 'tabRecord', helpKey: 'Record audio live (max 5 min) or upload a file (max 30 min). Preview before transcription.' },
]

function DropZone({
  accept, label, onFile,
}: {
  readonly accept: Record<string, string[]>
  readonly label:  string
  readonly onFile: (f: File) => void
}) {
  const onDrop = useCallback((files: File[]) => { if (files[0]) { onFile(files[0]) } }, [onFile])
  const { getRootProps, getInputProps, isDragActive, acceptedFiles } = useDropzone({ onDrop, accept, maxFiles: 1 })
  return (
    <div
      {...getRootProps()}
      className={cn(
        'flex flex-col items-center gap-2 rounded-xl border-2 border-dashed p-6 text-sm transition-colors cursor-pointer',
        isDragActive ? 'border-brand bg-brand-light text-brand' : 'border-border text-slate-400 hover:border-brand/50',
      )}
    >
      <input {...getInputProps()} />
      <Upload size={22} className={isDragActive ? 'text-brand' : 'text-slate-300'} />
      {acceptedFiles[0]
        ? <span className="font-medium text-slate-700 text-center break-all">{acceptedFiles[0].name}</span>
        : <span className="text-center">{label}</span>}
    </div>
  )
}

export function IngestPanel() {
  const t   = useT()
  const ctx = useAppStore(s => s.activeContext)!
  const qc  = useQueryClient()

  const [tab,      setTab]      = useState<SourceType>('pdfUrl')
  const [url,      setUrl]      = useState('')
  const [title,    setTitle]    = useState('')
  const [textBody, setTextBody] = useState('')
  const [file,     setFile]     = useState<File | null>(null)
  const [detail,   setDetail]   = useState<'quick' | 'standard' | 'detailed'>('standard')

  const invalidate = () => qc.invalidateQueries({ queryKey: ['sources', ctx.context_id] })

  const mut = useMutation({
    mutationFn: (fn: () => Promise<{ chunks_ingested: number }>) => fn(),
    onSuccess: (res) => {
      toast.success(`Indexed ${res.chunks_ingested} chunk${res.chunks_ingested !== 1 ? 's' : ''}`)
      setUrl(''); setTitle(''); setTextBody(''); setFile(null)
      invalidate()
    },
    onError: (e) => toast.error(String(e)),
  })

  const handleSubmit = () => {
    switch (tab) {
      case 'pdfUrl': mut.mutate(() => ingestApi.pdfUrl(url, ctx.context_id)); break
      case 'webUrl': mut.mutate(() => ingestApi.webUrl(url, ctx.context_id)); break
      case 'text':   mut.mutate(() => ingestApi.text(textBody, title || 'Paste', ctx.context_id)); break
      case 'upload': if (file) { mut.mutate(() => ingestApi.pdfUpload(file, ctx.context_id)) } break
      case 'image':  if (file) { mut.mutate(() => ingestApi.imageUpload(file, ctx.context_id, detail)) } break
      case 'audio':  if (file) { mut.mutate(() => ingestApi.audioUpload(file, ctx.context_id)) } break
    }
  }

  const delSrc = useMutation({
    mutationFn: (docId: string) => srcApi.delete(ctx.context_id, docId),
    onSuccess:  () => { toast.success('Source removed'); invalidate() },
    onError:    (e) => toast.error(String(e)),
  })

  const { data: sourceList = [], isLoading } = useQuery({
    queryKey: ['sources', ctx.context_id],
    queryFn:  () => srcApi.list(ctx.context_id),
  })

  let isFieldEmpty: boolean
  if (tab === 'pdfUrl' || tab === 'webUrl') {
    isFieldEmpty = url.trim().length === 0
  } else if (tab === 'text') {
    isFieldEmpty = textBody.trim().length < 50
  } else {
    isFieldEmpty = file === null
  }

  const currentTab = TABS.find(t => t.key === tab)!

  return (
    <ScrollArea className="h-full">
      <div className="px-5 py-5 space-y-6">
        {/* Source type selector */}
        <div>
          <p className="text-xs font-semibold text-slate-400 uppercase tracking-widest mb-3">Source type</p>
          <div className="grid grid-cols-3 gap-1.5">
            {TABS.map(({ key, Icon, labelKey }) => (
              <button
                key={key}
                type="button"
                onClick={() => setTab(key)}
                className={cn(
                  'flex flex-col items-center gap-1.5 rounded-xl py-3 px-2 text-xs font-medium transition-colors border',
                  tab === key
                    ? 'bg-brand-light text-brand border-brand/30'
                    : 'bg-surface text-slate-500 border-border hover:border-brand/30 hover:bg-brand-light/30',
                )}
              >
                <Icon size={16} />
                {t(labelKey as never)}
              </button>
            ))}
          </div>

          {/* Contextual help */}
          <p className="flex items-start gap-1.5 text-xs text-slate-400 mt-2.5">
            <HelpCircle size={12} className="shrink-0 mt-0.5" />
            {currentTab.helpKey}
          </p>
        </div>

        {/* Form */}
        <div className="space-y-3">
          {(tab === 'pdfUrl' || tab === 'webUrl') && (
            <Input
              value={url}
              onChange={e => setUrl(e.target.value)}
              placeholder={tab === 'pdfUrl' ? 'https://arxiv.org/pdf/…' : 'https://…'}
            />
          )}

          {tab === 'text' && (
            <>
              <Input value={title} onChange={e => setTitle(e.target.value)} placeholder={t('textTitle')} />
              <textarea
                value={textBody}
                onChange={e => setTextBody(e.target.value)}
                rows={6}
                placeholder={t('textContent')}
                className="w-full rounded-xl border border-border bg-surface-2 px-3.5 py-2.5 text-sm resize-y focus:outline-none focus:ring-2 focus:ring-brand/40 focus:bg-surface transition-colors"
              />
              {textBody.length > 0 && textBody.trim().length < 50 && (
                <p className="text-xs text-amber-600">{t('tooShort')}</p>
              )}
            </>
          )}

          {tab === 'upload' && (
            <DropZone accept={{ 'application/pdf': ['.pdf'] }} label="Drop a PDF or click to browse" onFile={setFile} />
          )}

          {tab === 'image' && (
            <>
              <DropZone accept={{ 'image/*': ['.png','.jpg','.jpeg','.webp'] }} label="Drop an image or click to browse" onFile={setFile} />
              <div className="flex gap-2">
                {(['quick', 'standard', 'detailed'] as const).map(d => (
                  <button
                    key={d}
                    type="button"
                    onClick={() => setDetail(d)}
                    className={cn(
                      'flex-1 rounded-lg py-1.5 text-xs font-medium border transition-colors',
                      detail === d ? 'bg-brand-light text-brand border-brand/30' : 'bg-surface border-border text-slate-500 hover:border-brand/30',
                    )}
                  >
                    {t(`detail${d.charAt(0).toUpperCase()}${d.slice(1)}` as never)}
                  </button>
                ))}
              </div>
            </>
          )}

          {tab === 'audio' && (
            <>
              <DropZone accept={{ 'audio/*': ['.mp3','.wav','.m4a','.ogg','.flac','.webm'] }} label="Drop an audio file or click to browse" onFile={setFile} />
              <p className="text-xs text-slate-400">{t('audioHint')}</p>
            </>
          )}

          {/* Voice recorder — has its own confirm flow, rendered outside the shared submit button */}
          {tab === 'record' && (
            <VoiceRecorderSource
              onConfirm={(blob, filename) => {
                const audioFile = new File([blob], filename, { type: blob.type })
                mut.mutate(() => ingestApi.audioUpload(audioFile, ctx.context_id))
              }}
            />
          )}

          {tab !== 'record' && (
            <Button variant="primary" className="w-full" onClick={handleSubmit}
              disabled={isFieldEmpty} loading={mut.isPending}>
              {t(`ingest${tab.charAt(0).toUpperCase()}${tab.slice(1)}` as never)}
            </Button>
          )}
        </div>

        {/* Indexed sources */}
        <div>
          <p className="text-xs font-semibold text-slate-400 uppercase tracking-widest mb-3 flex items-center gap-2">
            Indexed sources
            {sourceList.length > 0 && <Badge size="sm">{sourceList.length}</Badge>}
          </p>

          {isLoading && <div className="space-y-2">{[1,2].map(i => <div key={i} className="h-14 rounded-xl bg-surface-2 animate-pulse" />)}</div>}

          {!isLoading && sourceList.length === 0 && (
            <p className="text-sm text-slate-400 text-center py-6">No sources yet. Add one above.</p>
          )}

          {!isLoading && sourceList.length > 0 && (
            <ul className="space-y-2">
              {sourceList.map((s: Source) => (
                <li key={s.document_id} className="flex items-center gap-3 rounded-xl border border-border bg-surface px-3 py-2.5 shadow-sm">
                  <FileText size={15} className="text-slate-300 shrink-0" />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-slate-800 truncate">{s.title || s.document_id.slice(0, 8)}</p>
                    <p className="text-xs text-slate-400 flex items-center gap-1.5">
                      <Badge size="sm">{s.source_type}</Badge>
                      {s.chunk_count} chunks
                    </p>
                  </div>
                  <Button size="icon-sm" variant="ghost" onClick={() => delSrc.mutate(s.document_id)}
                    disabled={delSrc.isPending} title={t('deleteSource')}>
                    <Trash2 size={13} />
                  </Button>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </ScrollArea>
  )
}

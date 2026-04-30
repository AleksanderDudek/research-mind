'use client'

import { useCallback, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useDropzone } from 'react-dropzone'
import { toast } from 'sonner'
import { Trash2, FileText, Globe, Upload, Type, Image, Mic2 } from 'lucide-react'
import { ingest as ingestApi, sources as srcApi } from '@/lib/api'
import { useT } from '@/i18n/config'
import { useAppStore } from '@/lib/store'
import type { Source } from '@/lib/types'
import { Button } from '@/components/ui/Button'
import { Input }  from '@/components/ui/Input'
import { Spinner } from '@/components/ui/Spinner'
import { cn } from '@/lib/utils'

type SourceType = 'pdfUrl' | 'webUrl' | 'upload' | 'text' | 'image' | 'audio'

const TABS: { key: SourceType; Icon: typeof FileText; labelKey: string }[] = [
  { key: 'pdfUrl', Icon: FileText, labelKey: 'tabPdfUrl' },
  { key: 'webUrl', Icon: Globe,    labelKey: 'tabWeb'    },
  { key: 'upload', Icon: Upload,   labelKey: 'tabUpload' },
  { key: 'text',   Icon: Type,     labelKey: 'tabText'   },
  { key: 'image',  Icon: Image,    labelKey: 'tabImage'  },
  { key: 'audio',  Icon: Mic2,     labelKey: 'tabAudio'  },
]

function DropZone({
  accept,
  label,
  onFile,
}: {
  readonly accept: Record<string, string[]>
  readonly label:  string
  readonly onFile: (f: File) => void
}) {
  const onDrop = useCallback((files: File[]) => { if (files[0]) onFile(files[0]) }, [onFile])
  const { getRootProps, getInputProps, isDragActive, acceptedFiles } = useDropzone({ onDrop, accept, maxFiles: 1 })

  return (
    <div
      {...getRootProps()}
      className={cn(
        'flex flex-col items-center justify-center gap-2 rounded-xl border-2 border-dashed p-6 cursor-pointer transition-colors text-sm',
        isDragActive
          ? 'border-indigo-400 bg-indigo-50 text-indigo-700'
          : 'border-slate-200 text-slate-500 hover:border-indigo-300 hover:bg-slate-50',
      )}
    >
      <input {...getInputProps()} />
      <Upload size={20} />
      {acceptedFiles[0]
        ? <span className="font-medium text-slate-700">{acceptedFiles[0].name}</span>
        : <span>{label}</span>}
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
    onSuccess: (res: { chunks_ingested: number }) => {
      toast.success(t('ingestOk', { n: res.chunks_ingested }))
      setUrl(''); setTitle(''); setTextBody(''); setFile(null)
      invalidate()
    },
    onError: (e) => toast.error(t('errorPrefix', { msg: String(e) })),
  })

  const handleSubmit = () => {
    switch (tab) {
      case 'pdfUrl': return mut.mutate(ingestApi.pdfUrl(url, ctx.context_id) as never)
      case 'webUrl': return mut.mutate(ingestApi.webUrl(url, ctx.context_id) as never)
      case 'text':   return mut.mutate(ingestApi.text(textBody, title || 'Paste', ctx.context_id) as never)
      case 'upload': if (file) mut.mutate(ingestApi.pdfUpload(file, ctx.context_id) as never); break
      case 'image':  if (file) mut.mutate(ingestApi.imageUpload(file, ctx.context_id, detail) as never); break
      case 'audio':  if (file) mut.mutate(ingestApi.audioUpload(file, ctx.context_id) as never); break
    }
  }

  const delSrc = useMutation({
    mutationFn: (docId: string) => srcApi.delete(ctx.context_id, docId),
    onSuccess:  () => { toast.success('Source deleted'); invalidate() },
    onError:    (e) => toast.error(String(e)),
  })

  const { data: sourceList = [], isLoading } = useQuery({
    queryKey: ['sources', ctx.context_id],
    queryFn:  () => srcApi.list(ctx.context_id),
  })

  let isFieldEmpty: boolean
  if (tab === 'pdfUrl' || tab === 'webUrl') {
    isFieldEmpty = !url.trim()
  } else if (tab === 'text') {
    isFieldEmpty = textBody.trim().length < 50
  } else {
    isFieldEmpty = !file
  }
  const isSubmitDisabled = mut.isPending || isFieldEmpty

  return (
    <div className="px-4 py-4 space-y-5">
      {/* Source type pill selector */}
      <div className="flex flex-wrap gap-1.5">
        {TABS.map(({ key, Icon, labelKey }) => (
          <button
            key={key}
            onClick={() => setTab(key)}
            className={cn(
              'flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium transition-colors',
              tab === key
                ? 'bg-indigo-600 text-white'
                : 'bg-slate-100 text-slate-600 hover:bg-slate-200',
            )}
          >
            <Icon size={12} /> {t(labelKey as never)}
          </button>
        ))}
      </div>

      {/* Form fields */}
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
            <Input value={title} onChange={e => setTitle(e.target.value)}
              placeholder={t('textTitle')} />
            <textarea
              value={textBody}
              onChange={e => setTextBody(e.target.value)}
              rows={5}
              placeholder={t('textContent')}
              className="w-full rounded-xl border border-slate-200 bg-slate-50 px-3.5 py-2 text-sm resize-y focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
            {textBody.length > 0 && textBody.trim().length < 50 && (
              <p className="text-xs text-amber-600">{t('tooShort')}</p>
            )}
          </>
        )}

        {tab === 'upload' && (
          <DropZone
            accept={{ 'application/pdf': ['.pdf'] }}
            label="Drop a PDF here or click to browse"
            onFile={setFile}
          />
        )}

        {tab === 'image' && (
          <>
            <DropZone
              accept={{ 'image/*': ['.png', '.jpg', '.jpeg', '.webp'] }}
              label="Drop an image here or click to browse"
              onFile={setFile}
            />
            <select
              value={detail}
              onChange={e => setDetail(e.target.value as typeof detail)}
              className="w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm"
            >
              {(['quick', 'standard', 'detailed'] as const).map(d => (
                <option key={d} value={d}>
                  {t(`detail${d.charAt(0).toUpperCase()}${d.slice(1)}` as never)}
                </option>
              ))}
            </select>
          </>
        )}

        {tab === 'audio' && (
          <>
            <DropZone
              accept={{ 'audio/*': ['.mp3', '.wav', '.m4a', '.ogg', '.flac', '.webm'] }}
              label="Drop an audio file here or click to browse"
              onFile={setFile}
            />
            <p className="text-xs text-slate-400">{t('audioHint')}</p>
          </>
        )}

        <Button
          variant="primary"
          className="w-full"
          onClick={handleSubmit}
          disabled={isSubmitDisabled}
        >
          {mut.isPending ? <Spinner /> : t(`ingest${tab.charAt(0).toUpperCase()}${tab.slice(1)}` as never)}
        </Button>
      </div>

      {/* Source list */}
      <div>
        <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2">
          📄 {t('sources')} ({sourceList.length})
        </p>
        {isLoading && <Spinner />}
        {!isLoading && sourceList.length === 0 && (
          <p className="text-sm text-slate-400">{t('noSources')}</p>
        )}
        {!isLoading && sourceList.length > 0 && (
          <ul className="space-y-2">
            {sourceList.map((s: Source) => (
              <li key={s.document_id}
                className="flex items-center justify-between gap-2 rounded-xl border border-slate-100 px-3 py-2 text-sm">
                <div className="min-w-0">
                  <p className="font-medium text-slate-800 truncate">{s.title || s.document_id.slice(0, 8)}</p>
                  <p className="text-xs text-slate-400">{s.source_type} · {s.chunk_count} chunks</p>
                </div>
                <Button
                  variant="ghost" size="sm"
                  onClick={() => delSrc.mutate(s.document_id)}
                  disabled={delSrc.isPending}
                  title={t('deleteSource')}
                >
                  <Trash2 size={14} />
                </Button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  )
}

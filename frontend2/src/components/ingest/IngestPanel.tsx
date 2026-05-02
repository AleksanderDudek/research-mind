'use client'

import { useCallback, useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useDropzone } from 'react-dropzone'
import { toast } from 'sonner'
import { Trash2, FileText, Globe, Upload, Type, Image, Mic2, HelpCircle, Mic } from 'lucide-react'
import { useTranslations } from 'next-intl'
import { ingest as ingestApi, sources as srcApi } from '@/lib/api'
import { useAppStore } from '@/lib/store'
import type { Source } from '@/lib/types'
import { Button }    from '@/components/ui/button'
import { Input }     from '@/components/ui/input'
import { Textarea }  from '@/components/ui/textarea'
import { Badge }     from '@/components/ui/badge'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Form, FormControl, FormField, FormItem, FormMessage } from '@/components/ui/form'
import { VoiceRecorderSource } from './VoiceRecorderSource'
import { cn } from '@/lib/utils'

type SourceType = 'pdfUrl' | 'webUrl' | 'upload' | 'text' | 'image' | 'audio' | 'record'

// ── Zod schemas per source type ───────────────────────────────────────────────
const urlSchema    = z.object({ url: z.url('Enter a valid URL') })
const textSchema   = z.object({ title: z.string().optional(), content: z.string().min(50, 'Minimum 50 characters') })
const detailSchema = z.object({ detail: z.enum(['quick', 'standard', 'detailed']) })

type UrlInput    = z.infer<typeof urlSchema>
type TextInput   = z.infer<typeof textSchema>
type DetailInput = z.infer<typeof detailSchema>

const TABS: { key: SourceType; Icon: typeof FileText; labelKey: string; helpKey: string }[] = [
  { key: 'pdfUrl', Icon: FileText, labelKey: 'tabPdfUrl', helpKey: 'helpPdfUrl' },
  { key: 'webUrl', Icon: Globe,    labelKey: 'tabWeb',    helpKey: 'helpWebUrl' },
  { key: 'upload', Icon: Upload,   labelKey: 'tabUpload', helpKey: 'helpUpload' },
  { key: 'text',   Icon: Type,     labelKey: 'tabText',   helpKey: 'helpText'   },
  { key: 'image',  Icon: Image,    labelKey: 'tabImage',  helpKey: 'helpImage'  },
  { key: 'audio',  Icon: Mic2,     labelKey: 'tabAudio',  helpKey: 'helpAudio'  },
  { key: 'record', Icon: Mic,      labelKey: 'tabRecord', helpKey: 'helpRecord' },
]

function DropZone({ accept, label, onFile }: { accept: Record<string, string[]>; label: string; onFile: (f: File) => void }) {
  const onDrop = useCallback((files: File[]) => { if (files[0]) onFile(files[0]) }, [onFile])
  const { getRootProps, getInputProps, isDragActive, acceptedFiles } = useDropzone({ onDrop, accept, maxFiles: 1 })
  return (
    <div {...getRootProps()} className={cn(
      'flex flex-col items-center gap-2 rounded-xl border-2 border-dashed p-6 text-sm transition-colors cursor-pointer',
      isDragActive ? 'border-primary bg-accent text-primary' : 'border-border text-muted-foreground hover:border-primary/50',
    )}>
      <input {...getInputProps()} />
      <Upload size={22} className={isDragActive ? 'text-primary' : 'text-muted-foreground'} />
      {acceptedFiles[0]
        ? <span className="font-medium text-foreground text-center break-all">{acceptedFiles[0].name}</span>
        : <span className="text-center">{label}</span>}
    </div>
  )
}

export function IngestPanel() {
  const t   = useTranslations()
  const ctx = useAppStore(s => s.activeContext)!
  const qc  = useQueryClient()
  const [tab,    setTab]    = useState<SourceType>('pdfUrl')
  const [file,   setFile]   = useState<File | null>(null)

  const invalidate = () => qc.invalidateQueries({ queryKey: ['sources', ctx.context_id] })

  const mut = useMutation({
    mutationFn: (fn: () => Promise<{ chunks_ingested: number }>) => fn(),
    onSuccess: (res) => {
      toast.success(t('ingestOk', { n: res.chunks_ingested }))
      urlForm.reset()
      textForm.reset()
      setFile(null)
      invalidate()
    },
    onError: (e: Error) => toast.error(e.message),
  })

  const delSrc = useMutation({
    mutationFn: (docId: string) => srcApi.delete(ctx.context_id, docId),
    onSuccess:  () => { toast.success(t('sourceRemoved')); invalidate() },
    onError:    (e: Error) => toast.error(e.message),
  })

  const { data: sourceList = [], isLoading } = useQuery({
    queryKey: ['sources', ctx.context_id],
    queryFn:  () => srcApi.list(ctx.context_id),
  })

  // ── Forms ─────────────────────────────────────────────────────────────────
  const urlForm  = useForm<UrlInput>({ resolver: zodResolver(urlSchema), defaultValues: { url: '' } })
  const textForm = useForm<TextInput>({ resolver: zodResolver(textSchema), defaultValues: { title: '', content: '' } })
  const detailForm = useForm<DetailInput>({ defaultValues: { detail: 'standard' } })

  const onUrlSubmit  = (data: UrlInput)  => {
    const fn = tab === 'pdfUrl'
      ? () => ingestApi.pdfUrl(data.url, ctx.context_id)
      : () => ingestApi.webUrl(data.url, ctx.context_id)
    mut.mutate(fn)
  }
  const onTextSubmit = (data: TextInput) =>
    mut.mutate(() => ingestApi.text(data.content, data.title || 'Paste', ctx.context_id))
  const onFileSubmit = () => {
    if (!file) return
    const detail = detailForm.getValues('detail')
    if (tab === 'upload') mut.mutate(() => ingestApi.pdfUpload(file, ctx.context_id))
    else if (tab === 'image') mut.mutate(() => ingestApi.imageUpload(file, ctx.context_id, detail))
    else if (tab === 'audio') mut.mutate(() => ingestApi.audioUpload(file, ctx.context_id))
  }

  const currentTab = TABS.find(tb => tb.key === tab)!

  return (
    <ScrollArea className="h-full">
      <div className="px-5 py-5 space-y-6">
        {/* Tab grid */}
        <div>
          <p className="text-xs font-semibold text-muted-foreground uppercase tracking-widest mb-3">{t('sourceTypeSection')}</p>
          <div className="grid grid-cols-3 gap-1.5">
            {TABS.map(({ key, Icon, labelKey }) => (
              <button
                key={key}
                type="button"
                onClick={() => setTab(key)}
                className={cn(
                  'flex flex-col items-center gap-1.5 rounded-xl py-3 px-2 text-xs font-medium transition-colors border',
                  tab === key
                    ? 'bg-accent text-primary border-primary/30'
                    : 'bg-background text-muted-foreground border-border hover:border-primary/30 hover:bg-accent/30',
                )}
              >
                <Icon size={16} />
                {t(labelKey)}
              </button>
            ))}
          </div>
          <p className="flex items-start gap-1.5 text-xs text-muted-foreground mt-2.5">
            <HelpCircle size={12} className="shrink-0 mt-0.5" />
            {t(currentTab.helpKey)}
          </p>
        </div>

        {/* Forms */}
        <div className="space-y-3">
          {(tab === 'pdfUrl' || tab === 'webUrl') && (
            <Form {...urlForm}>
              <form onSubmit={urlForm.handleSubmit(onUrlSubmit)} className="space-y-3">
                <FormField control={urlForm.control} name="url" render={({ field }) => (
                  <FormItem>
                    <FormControl>
                      <Input placeholder={tab === 'pdfUrl' ? 'https://arxiv.org/pdf/…' : 'https://…'} {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )} />
                <Button type="submit" className="w-full" disabled={mut.isPending}>
                  {t(tab === 'pdfUrl' ? 'ingestPdfUrl' : 'ingestWebUrl')}
                </Button>
              </form>
            </Form>
          )}

          {tab === 'text' && (
            <Form {...textForm}>
              <form onSubmit={textForm.handleSubmit(onTextSubmit)} className="space-y-3">
                <FormField control={textForm.control} name="title" render={({ field }) => (
                  <FormItem><FormControl><Input placeholder={t('textTitle')} {...field} /></FormControl></FormItem>
                )} />
                <FormField control={textForm.control} name="content" render={({ field }) => (
                  <FormItem>
                    <FormControl>
                      <Textarea placeholder={t('textContent')} rows={6} className="resize-y" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )} />
                <Button type="submit" className="w-full" disabled={mut.isPending}>{t('ingestText')}</Button>
              </form>
            </Form>
          )}

          {tab === 'upload' && (
            <>
              <DropZone accept={{ 'application/pdf': ['.pdf'] }} label={t('dropPdf')} onFile={setFile} />
              <Button className="w-full" disabled={!file || mut.isPending} onClick={onFileSubmit}>{t('ingestUpload')}</Button>
            </>
          )}

          {tab === 'image' && (
            <>
              <DropZone accept={{ 'image/*': ['.png','.jpg','.jpeg','.webp'] }} label={t('dropImage')} onFile={setFile} />
              <div className="flex gap-2">
                {(['quick', 'standard', 'detailed'] as const).map(d => (
                  <button
                    key={d}
                    type="button"
                    onClick={() => detailForm.setValue('detail', d)}
                    className={cn(
                      'flex-1 rounded-lg py-1.5 text-xs font-medium border transition-colors',
                      detailForm.watch('detail') === d
                        ? 'bg-accent text-primary border-primary/30'
                        : 'bg-background border-border text-muted-foreground hover:border-primary/30',
                    )}
                  >
                    {t(`detail${d.charAt(0).toUpperCase()}${d.slice(1)}` as Parameters<typeof t>[0])}
                  </button>
                ))}
              </div>
              <Button className="w-full" disabled={!file || mut.isPending} onClick={onFileSubmit}>{t('ingestImage')}</Button>
            </>
          )}

          {tab === 'audio' && (
            <>
              <DropZone accept={{ 'audio/*': ['.mp3','.wav','.m4a','.ogg','.flac','.webm'] }} label={t('dropAudio')} onFile={setFile} />
              <p className="text-xs text-muted-foreground">{t('audioHint')}</p>
              <Button className="w-full" disabled={!file || mut.isPending} onClick={onFileSubmit}>{t('ingestAudio')}</Button>
            </>
          )}

          {tab === 'record' && (
            <VoiceRecorderSource
              onConfirm={(blob, filename) => {
                const f = new File([blob], filename, { type: blob.type })
                mut.mutate(() => ingestApi.audioUpload(f, ctx.context_id))
              }}
            />
          )}
        </div>

        {/* Source list */}
        <div>
          <div className="text-xs font-semibold text-muted-foreground uppercase tracking-widest mb-3 flex items-center gap-2">
            {t('indexedSources')}
            {sourceList.length > 0 && <Badge variant="secondary">{sourceList.length}</Badge>}
          </div>

          {isLoading && <div className="space-y-2">{[1,2].map(i => <div key={i} className="h-14 rounded-xl bg-muted animate-pulse" />)}</div>}

          {!isLoading && sourceList.length === 0 && (
            <p className="text-sm text-muted-foreground text-center py-6">{t('noSourcesYet')}</p>
          )}

          {!isLoading && sourceList.length > 0 && (
            <ul className="space-y-2">
              {sourceList.map((s: Source) => (
                <li key={s.document_id} className="flex items-center gap-3 rounded-xl border bg-card px-3 py-2.5 shadow-sm">
                  <FileText size={15} className="text-muted-foreground shrink-0" />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium truncate">{s.title || s.document_id.slice(0, 8)}</p>
                    <div className="text-xs text-muted-foreground flex items-center gap-1.5">
                      <Badge variant="outline" className="text-[10px] h-4 px-1">{s.source_type}</Badge>
                      {t('chunksCount', { count: s.chunk_count })}
                    </div>
                  </div>
                  <Button size="icon" variant="ghost" onClick={() => delSrc.mutate(s.document_id)} disabled={delSrc.isPending} title={t('deleteSource')} className="h-7 w-7">
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

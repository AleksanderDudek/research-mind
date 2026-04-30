'use client'

import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import { toast } from 'sonner'
import { FolderOpen, MoreHorizontal, Pencil, Trash2, Check, X } from 'lucide-react'
import { contexts as api, sources } from '@/lib/api'
import type { Context } from '@/lib/types'
import { useT } from '@/i18n/config'
import { Button } from '@/components/ui/Button'
import { Input  } from '@/components/ui/Input'
import { Badge  } from '@/components/ui/Badge'
import { Popover, PopoverTrigger, PopoverContent, PopoverItem, PopoverClose } from '@/components/ui/Popover'

interface Props {
  readonly ctx:    Context
  readonly onOpen: (ctx: Context) => void
}

export function ContextCard({ ctx, onOpen }: Props) {
  const t  = useT()
  const qc = useQueryClient()

  const [renaming, setRenaming] = useState(false)
  const [newName,  setNewName]  = useState(ctx.name)

  const { data: srcs = [] } = useQuery({
    queryKey: ['sources', ctx.context_id],
    queryFn:  () => sources.list(ctx.context_id),
    staleTime: 60_000,
  })

  const del = useMutation({
    mutationFn: () => api.delete(ctx.context_id),
    onSuccess:  () => { qc.invalidateQueries({ queryKey: ['contexts'] }); toast.success('Context deleted') },
    onError:    (e) => toast.error(String(e)),
  })

  const rename = useMutation({
    mutationFn: () => api.rename(ctx.context_id, newName.trim()),
    onSuccess:  () => { qc.invalidateQueries({ queryKey: ['contexts'] }); setRenaming(false); toast.success('Renamed') },
    onError:    (e) => toast.error(String(e)),
  })

  const date = new Date(ctx.created_at).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, scale: 0.98 }}
      className="group bg-surface rounded-xl border border-border shadow-sm hover:shadow-md hover:border-brand-light transition-all duration-200"
    >
      {renaming ? (
        <div className="flex items-center gap-2 p-3">
          <Input
            autoFocus
            value={newName}
            onChange={e => setNewName(e.target.value)}
            onKeyDown={e => { if (e.key === 'Enter') { rename.mutate() } else if (e.key === 'Escape') { setRenaming(false) } }}
            className="flex-1"
          />
          <Button size="icon-sm" variant="primary"    onClick={() => rename.mutate()} loading={rename.isPending}><Check size={14} /></Button>
          <Button size="icon-sm" variant="ghost"      onClick={() => setRenaming(false)}><X size={14} /></Button>
        </div>
      ) : (
        <div className="flex items-center gap-3 p-4">
          {/* Icon */}
          <div className="w-10 h-10 rounded-lg bg-brand-light flex items-center justify-center text-brand shrink-0">
            <FolderOpen size={18} />
          </div>

          {/* Content — native button for full keyboard + device accessibility */}
          <button
            type="button"
            className="flex-1 min-w-0 text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand/60 rounded-md"
            onClick={() => onOpen(ctx)}
          >
            <p className="font-semibold text-slate-800 truncate leading-tight">{ctx.name}</p>
            <div className="flex items-center gap-2 mt-0.5">
              <span className="text-xs text-slate-400">{date}</span>
              <Badge size="sm">{srcs.length} {srcs.length === 1 ? 'source' : 'sources'}</Badge>
            </div>
          </button>

          {/* Actions */}
          <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
            <Button size="icon-sm" variant="ghost" onClick={() => onOpen(ctx)} title={t('openContext')}>
              <FolderOpen size={15} />
            </Button>

            <Popover>
              <PopoverTrigger asChild>
                <Button size="icon-sm" variant="ghost" title="More options">
                  <MoreHorizontal size={15} />
                </Button>
              </PopoverTrigger>
              <PopoverContent align="end">
                <PopoverItem onClick={() => { setNewName(ctx.name); setRenaming(true) }}>
                  <Pencil size={14} /> {t('renameContext')}
                </PopoverItem>
                <PopoverClose asChild>
                  <PopoverItem destructive onClick={() => del.mutate()}>
                    <Trash2 size={14} /> {t('deleteContext')}
                  </PopoverItem>
                </PopoverClose>
              </PopoverContent>
            </Popover>
          </div>
        </div>
      )}
    </motion.div>
  )
}

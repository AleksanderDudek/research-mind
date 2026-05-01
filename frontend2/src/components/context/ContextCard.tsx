'use client'

import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { motion } from 'framer-motion'
import { toast } from 'sonner'
import { FolderOpen, MoreHorizontal, Pencil, Trash2, Check, X } from 'lucide-react'
import { useTranslations } from 'next-intl'
import { contexts as api, sources } from '@/lib/api'
import type { Context } from '@/lib/types'
import { Button }  from '@/components/ui/button'
import { Input }   from '@/components/ui/input'
import { Badge }   from '@/components/ui/badge'
import {
  DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'

interface Props {
  readonly ctx:    Context
  readonly onOpen: (ctx: Context) => void
}

export function ContextCard({ ctx, onOpen }: Props) {
  const t  = useTranslations()
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
    onSuccess:  () => { qc.invalidateQueries({ queryKey: ['contexts'] }); toast.success(t('contextDeleted')) },
    onError:    (e: Error) => toast.error(e.message),
  })

  const rename = useMutation({
    mutationFn: () => api.rename(ctx.context_id, newName.trim()),
    onSuccess:  () => { qc.invalidateQueries({ queryKey: ['contexts'] }); setRenaming(false); toast.success(t('renamedOk')) },
    onError:    (e: Error) => toast.error(e.message),
  })

  const date = new Date(ctx.created_at).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, scale: 0.98 }}
      className="group bg-card rounded-xl border shadow-sm hover:shadow-md hover:border-primary/30 transition-all duration-200"
    >
      {renaming ? (
        <div className="flex items-center gap-2 p-3">
          <Input
            autoFocus
            value={newName}
            onChange={e => setNewName(e.target.value)}
            onKeyDown={e => {
              if (e.key === 'Enter') rename.mutate()
              else if (e.key === 'Escape') setRenaming(false)
            }}
            className="flex-1"
          />
          <Button size="icon" onClick={() => rename.mutate()} disabled={rename.isPending}><Check size={14} /></Button>
          <Button size="icon" variant="ghost" onClick={() => setRenaming(false)}><X size={14} /></Button>
        </div>
      ) : (
        <div className="flex items-center gap-3 p-4">
          <div className="w-10 h-10 rounded-lg bg-accent flex items-center justify-center text-primary shrink-0">
            <FolderOpen size={18} />
          </div>

          <button
            type="button"
            className="flex-1 min-w-0 text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring rounded-md"
            onClick={() => onOpen(ctx)}
          >
            <p className="font-semibold text-foreground truncate leading-tight">{ctx.name}</p>
            <div className="flex items-center gap-2 mt-0.5">
              <span className="text-xs text-muted-foreground">{date}</span>
              <Badge variant="secondary" className="text-[10px] h-4 px-1.5">
                {t('sourcesCount', { count: srcs.length })}
              </Badge>
            </div>
          </button>

          <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
            <Button size="icon" variant="ghost" onClick={() => onOpen(ctx)} title={t('openContext')}>
              <FolderOpen size={15} />
            </Button>
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button size="icon" variant="ghost" title={t('moreOptions')}>
                  <MoreHorizontal size={15} />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DropdownMenuItem onClick={() => { setNewName(ctx.name); setRenaming(true) }}>
                  <Pencil size={14} className="mr-2" /> {t('renameContext')}
                </DropdownMenuItem>
                <DropdownMenuItem
                  className="text-destructive focus:text-destructive"
                  onClick={() => del.mutate()}
                >
                  <Trash2 size={14} className="mr-2" /> {t('deleteContext')}
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </div>
      )}
    </motion.div>
  )
}

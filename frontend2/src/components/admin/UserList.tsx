'use client'

import { useQuery, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { Trash2, ShieldCheck } from 'lucide-react'
import { useTranslations } from 'next-intl'
import { org as orgApi } from '@/lib/api'
import { useAppStore } from '@/lib/store'
import { Button } from '@/components/ui/button'
import { Badge  } from '@/components/ui/badge'

const ROLE_VARIANT: Record<string, 'default' | 'secondary' | 'outline'> = {
  superadmin: 'default',
  admin:      'secondary',
  user:       'outline',
}

export function UserList() {
  const t         = useTranslations()
  const qc        = useQueryClient()
  const currentId = useAppStore(s => s.userId)

  const { data: members = [], isLoading } = useQuery({
    queryKey: ['org', 'members'],
    queryFn:  orgApi.members,
  })

  const handleRemove = async (memberId: string) => {
    try {
      await orgApi.removeMember(memberId)
      toast.success(t('adminMemberRemoved'))
      qc.invalidateQueries({ queryKey: ['org', 'members'] })
    } catch (err) {
      toast.error(String(err))
    }
  }

  if (isLoading) {
    return (
      <div className="space-y-2">
        {[1, 2].map(i => <div key={i} className="h-14 rounded-xl bg-muted animate-pulse" />)}
      </div>
    )
  }

  return (
    <ul className="space-y-2">
      {members.map(m => (
        <li key={m.id} className="flex items-center gap-3 rounded-xl border bg-card px-3 py-2.5">
          <ShieldCheck size={15} className="text-muted-foreground shrink-0" />
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium truncate">{m.full_name || '—'}</p>
            <p className="text-xs text-muted-foreground">{m.id.slice(0, 8)}</p>
          </div>
          <Badge variant={ROLE_VARIANT[m.role] ?? 'outline'}>{m.role}</Badge>
          {m.id !== currentId && (
            <Button
              size="icon"
              variant="ghost"
              className="h-7 w-7 text-destructive hover:text-destructive"
              onClick={() => handleRemove(m.id)}
              title={t('adminRemoveMember')}
            >
              <Trash2 size={13} />
            </Button>
          )}
        </li>
      ))}
    </ul>
  )
}

'use client'

import { MessageSquare, FileText, History, Settings } from 'lucide-react'
import { useTranslations } from 'next-intl'
import { cn } from '@/lib/utils'
import { useAppStore } from '@/lib/store'
import type { SidebarTab } from './Sidebar'

interface Props {
  readonly tab:   SidebarTab
  readonly onTab: (t: SidebarTab) => void
}

const TABS: { id: SidebarTab; Icon: typeof MessageSquare; labelKey: string }[] = [
  { id: 'chat',     Icon: MessageSquare, labelKey: 'chat'    },
  { id: 'sources',  Icon: FileText,      labelKey: 'sources' },
  { id: 'history',  Icon: History,       labelKey: 'history' },
  { id: 'settings', Icon: Settings,      labelKey: 'settings'},
]

export function BottomTabs({ tab, onTab }: Props) {
  const t    = useTranslations()
  const role = useAppStore(s => s.role)
  // Only admins/superadmins see Sources and Settings.
  // null role (auth still loading) is treated the same as 'user' — fail closed.
  const visibleTabs = (role === 'admin' || role === 'superadmin')
    ? TABS
    : TABS.filter(tb => tb.id === 'chat' || tb.id === 'history')

  return (
    <nav className="md:hidden fixed bottom-0 inset-x-0 z-20 border-t bg-card/95 backdrop-blur-sm">
      <div className="flex">
        {visibleTabs.map(({ id, Icon, labelKey }) => (
          <button
            key={id}
            type="button"
            onClick={() => onTab(id)}
            className={cn(
              'flex-1 flex flex-col items-center gap-1 py-2.5 text-[10px] font-medium transition-colors',
              tab === id ? 'text-primary' : 'text-muted-foreground hover:text-foreground',
            )}
          >
            <Icon size={18} strokeWidth={tab === id ? 2.5 : 1.75} />
            {t(labelKey)}
          </button>
        ))}
      </div>
      <div className="h-safe-bottom" />
    </nav>
  )
}

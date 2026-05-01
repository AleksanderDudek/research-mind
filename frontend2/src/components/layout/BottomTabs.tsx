'use client'

import { MessageSquare, FileText, History, Settings } from 'lucide-react'
import { cn } from '@/lib/utils'
import { useT } from '@/i18n/config'
import type { TranslationKey } from '@/i18n/config'
import type { SidebarTab } from './Sidebar'

interface Props {
  readonly tab:   SidebarTab
  readonly onTab: (t: SidebarTab) => void
}

const TABS: { id: SidebarTab; Icon: typeof MessageSquare; labelKey: TranslationKey }[] = [
  { id: 'chat',     Icon: MessageSquare, labelKey: 'chat'    },
  { id: 'sources',  Icon: FileText,      labelKey: 'sources' },
  { id: 'history',  Icon: History,       labelKey: 'history' },
  { id: 'settings', Icon: Settings,      labelKey: 'settings'},
]

export function BottomTabs({ tab, onTab }: Props) {
  const t = useT()

  return (
    <nav className="md:hidden fixed bottom-0 inset-x-0 z-20 border-t border-border bg-surface/95 backdrop-blur-sm">
      <div className="flex">
        {TABS.map(({ id, Icon, labelKey }) => (
          <button
            key={id}
            type="button"
            onClick={() => onTab(id)}
            className={cn(
              'flex-1 flex flex-col items-center gap-1 py-2.5 text-[10px] font-medium transition-colors',
              tab === id ? 'text-brand' : 'text-slate-400 hover:text-slate-600',
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
